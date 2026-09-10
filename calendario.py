#!/usr/bin/env python3
"""Calendario de pared para imprimir: doce imágenes, una por mes, cada una
con la grilla de días de ese mes debajo, todo en un solo PDF de varias
páginas. Corre desde la raíz del proyecto:

    python calendario.py --sources fuentes/ --year 2027 --out calendario.pdf

Las imágenes salen de `fuentes/` o de wallpapers ya generados, lo mismo que
acepta `--images` en `proun/cli.py` (archivos, carpetas o globs). Si hay más
de doce, se toman las primeras doce en orden; con `--seed` se sortean en vez
de tomar siempre las mismas.

Con `--filters` se les puede aplicar a las doce fotos el mismo recoloreado
que al resto de Proun, por ejemplo para que compartan la paleta de un lote de
wallpapers ya generado. El archivo es un JSON con las mismas claves que
`ops/tones.py`, `ops/recolor.py` y `ops/finish.py` ya documentan:

    {"color": "#3ba7ff", "tones": true, "recolor": {"mode": "duotone"}}
"""

from __future__ import annotations

import argparse
import calendar
import json
import random
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from proun import loading
from proun.errors import SourceError, SpecError
from proun.ops import finish as finish_op
from proun.ops import recolor as recolor_op
from proun.ops import resize as resize_op
from proun.ops import text as text_op
from proun.ops import tones as tones_op

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["L", "M", "X", "J", "V", "S", "D"]

PAPERS_MM = {
    "a4": (210.0, 297.0),
    "letter": (215.9, 279.4),
}

INK = (26, 24, 22)
LINEA_CELDA = (200, 197, 192)
PHOTO_FRACTION = 0.5  # el resto es para la grilla: bastante celda libre para anotar
MAX_SEMANAS = 6  # un mes puede pintar 4, 5 o 6 filas; se fija la más grande para
                 # que las doce páginas compartan el mismo alto de grilla

FILTER_KEYS = {"color", "tones", "recolor", "finish"}
DEFAULT_COLOR = "#3ba7ff"

_numeral_cache: dict[tuple[str, str], Image.Image] = {}


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="calendario",
        description="Genera un calendario de pared: doce imágenes con la grilla de su mes.",
    )
    p.add_argument("--sources", nargs="+", required=True, metavar="RUTA",
                   help="archivos, carpetas o globs con las doce imágenes")
    p.add_argument("--year", type=int, default=date.today().year, metavar="AAAA",
                   help="año del calendario (por defecto, el actual)")
    p.add_argument("--out", default="calendario.pdf", metavar="ARCHIVO",
                   help="PDF de salida, las doce páginas juntas")
    p.add_argument("--paper", choices=sorted(PAPERS_MM), default="a4", help="tamaño de papel")
    p.add_argument("--orientation", choices=("portrait", "landscape"), default="portrait")
    p.add_argument("--dpi", type=int, default=300, help="resolución de impresión")
    p.add_argument("--margin", type=float, default=12.0, metavar="MM",
                   help="margen de impresión en milímetros")
    p.add_argument("--seed", type=int, default=None,
                   help="sortea qué doce imágenes entran y en qué mes cae cada una")
    p.add_argument("--filters", metavar="JSON",
                   help="archivo con tones/recolor/finish para aplicar a las doce fotos")
    return p.parse_args(argv)


def mm_to_px(mm: float, dpi: int) -> int:
    return round(mm / 25.4 * dpi)


def page_size(paper: str, orientation: str, dpi: int) -> tuple[int, int]:
    ancho_mm, alto_mm = PAPERS_MM[paper]
    if orientation == "landscape":
        ancho_mm, alto_mm = alto_mm, ancho_mm
    return mm_to_px(ancho_mm, dpi), mm_to_px(alto_mm, dpi)


def pick_twelve(sources, seed: int | None) -> list[Path]:
    paths = loading.expand(sources)
    if len(paths) < 12:
        raise SpecError(f"hacen falta al menos 12 imágenes, {sources!r} dio {len(paths)}")
    if seed is not None:
        paths = list(paths)
        random.Random(seed).shuffle(paths)
    return paths[:12]


def load_filters(path: str | None) -> dict:
    """Lee el JSON de `--filters`. Sin `--filters`, no se aplica nada."""
    if path is None:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"JSON inválido en {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError(f"{path} debe ser un objeto JSON")
    # Igual que en los specs de json/: una clave que empieza con "_" es un
    # comentario (JSON no los tiene) y se ignora.
    data = {k: v for k, v in data.items() if not str(k).startswith("_")}
    unknown = set(data) - FILTER_KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en {path}: {sorted(unknown)}")
    return data


def apply_filters(im: Image.Image, filtros: dict, rng: random.Random) -> Image.Image:
    """Le pasa la foto por `tones`, `recolor` y `finish`, igual que a
    cualquier capa del generador principal, con el mismo `main` para las
    doce: así comparten paleta entre sí."""
    if not filtros:
        return im
    main = filtros.get("color", DEFAULT_COLOR)
    if "tones" in filtros:
        im = tones_op.apply(im, filtros["tones"])
    if "recolor" in filtros:
        im = recolor_op.apply(im, main, filtros["recolor"])
    if "finish" in filtros:
        im = finish_op.apply(im, main, filtros["finish"], rng)
    return im


def numeral(text: str, weight: str = "bold") -> Image.Image:
    """Rasteriza `text` con `ops/text.py` una sola vez por valor: los mismos
    números y encabezados se repiten entre los doce meses."""
    clave = (text, weight)
    if clave not in _numeral_cache:
        _numeral_cache[clave] = text_op.build({"text": text, "weight": weight})
    return _numeral_cache[clave]


def paste_text(page: Image.Image, text: str, center: tuple[int, int], line_height: int,
              weight: str = "bold") -> None:
    """Pega `text` centrado en `center`, escalado a `line_height` de alto."""
    glifo = numeral(text, weight)
    factor = line_height / glifo.height
    tamano = (max(1, round(glifo.width * factor)), max(1, line_height))
    glifo = glifo.resize(tamano, Image.Resampling.LANCZOS)
    tinta = Image.new("RGBA", glifo.size, INK + (255,))
    tinta.putalpha(glifo.getchannel("A"))
    x = round(center[0] - tamano[0] / 2)
    y = round(center[1] - tamano[1] / 2)
    page.paste(tinta, (x, y), tinta)


def render_month(path: Path, year: int, month: int, size: tuple[int, int],
                 margin_px: int, gap_px: int, filtros: dict | None = None,
                 rng: random.Random | None = None) -> Image.Image:
    page = Image.new("RGB", size, "white")
    ancho_util = size[0] - 2 * margin_px
    alto_util = size[1] - 2 * margin_px

    alto_foto = round(alto_util * PHOTO_FRACTION)
    foto = loading.load(path)
    foto = resize_op.apply(foto, {"size": [ancho_util, alto_foto], "mode": "fill"}, foto.size)
    foto = apply_filters(foto, filtros or {}, rng or random.Random(0))
    page.paste(foto.convert("RGB"), (margin_px, margin_px))

    grid_top = margin_px + alto_foto + gap_px
    grid_alto = size[1] - margin_px - grid_top
    header_alto = round(grid_alto * 0.16)
    fila_alto = (grid_alto - header_alto) // (MAX_SEMANAS + 1)  # +1: fila de L M X J V S D
    col_ancho = ancho_util / 7

    # Un mes de 4 semanas y uno de 6 comparten el mismo fila_alto (para que
    # las doce páginas se vean iguales), así que el bloque completo se centra
    # en el espacio sobrante en vez de quedar pegado arriba con un vacío abajo.
    semanas = calendar.monthcalendar(year, month)
    bloque_alto = header_alto + fila_alto * (len(semanas) + 1)
    inicio = grid_top + max(0, (grid_alto - bloque_alto) // 2)

    paste_text(page, f"{MESES[month - 1]} {year}",
              (size[0] // 2, inicio + header_alto // 2), round(header_alto * 0.7))

    fila_dias_y = inicio + header_alto + fila_alto // 2
    for c, nombre in enumerate(DIAS):
        cx = round(margin_px + col_ancho * (c + 0.5))
        paste_text(page, nombre, (cx, fila_dias_y), round(fila_alto * 0.4), weight="regular")

    # El número va arriba de su celda, no centrado: el resto de la celda
    # queda como casillero en blanco para anotar algo si se imprime.
    draw = ImageDraw.Draw(page)
    borde = max(1, round(fila_alto * 0.012))
    numero_alto = round(fila_alto * 0.26)
    padding = round(fila_alto * 0.08)
    for f, semana in enumerate(semanas):
        fila_top = inicio + header_alto + fila_alto * (f + 1)
        for c, dia in enumerate(semana):
            if dia == 0:
                continue
            x0 = round(margin_px + col_ancho * c)
            x1 = round(margin_px + col_ancho * (c + 1))
            draw.rectangle((x0, fila_top, x1, fila_top + fila_alto), outline=LINEA_CELDA,
                           width=borde)
            cx = round((x0 + x1) / 2)
            cy = fila_top + padding + numero_alto // 2
            paste_text(page, str(dia), (cx, cy), numero_alto, weight="regular")

    return page


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        imagenes = pick_twelve(args.sources, args.seed)
        filtros = load_filters(args.filters)
        size = page_size(args.paper, args.orientation, args.dpi)
        margin_px = mm_to_px(args.margin, args.dpi)
        gap_px = mm_to_px(6, args.dpi)

        paginas = []
        for mes, imagen in enumerate(imagenes, start=1):
            rng = random.Random((args.seed or 0) * 1009 + mes)
            paginas.append(
                render_month(imagen, args.year, mes, size, margin_px, gap_px, filtros, rng)
            )

        salida = Path(args.out)
        salida.parent.mkdir(parents=True, exist_ok=True)
        paginas[0].save(salida, save_all=True, append_images=paginas[1:], resolution=args.dpi)
    except (SpecError, SourceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{len(paginas)} páginas en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
