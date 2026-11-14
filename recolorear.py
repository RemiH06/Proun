"""Vuelve a colorear un wallpaper ya exportado, sin reconstruirlo desde sus
capas originales: con un colormap de varios colores (inferno y similares,
modo "colormap" por defecto) o como negativo fotográfico (--invert, modo
"invert"). Usa proun.ops.recolor tal cual. Corre desde la raíz del
proyecto:

    python recolorear.py wallpapers/1920x1080/wp_0001_3ba7ff_123456.png
    python recolorear.py wallpapers/1920x1080/wp_0001_3ba7ff_123456.png --name inferno
    python recolorear.py foto.png --stops "#000814" "#ffd60a" --out foto_sol.png
    python recolorear.py foto.png --invert
    python recolorear.py foto.png --kmeans 6 --smooth 5
    python recolorear.py foto.png --kmeans 6 --name viridis
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from proun.errors import SpecError
from proun.ops import recolor

# Sin color principal de verdad: el modo "colormap" lo ignora, pero
# recolor.apply lo pide igual (lo usan los demás modos).
_SIN_USAR = "#000000"


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="recolorear",
        description='Repinta un wallpaper ya exportado con un colormap (recolor.py, modo "colormap").',
    )
    p.add_argument("imagen", help="ruta al PNG/JPG ya exportado")
    # Sin default a propósito: en colormap el motor ya usa inferno si no
    # llega ninguno, y en --kmeans la ausencia significa "colores medios".
    p.add_argument("--name",
                    help='colormap con nombre (ver proun.ops.recolor.COLORMAPS), por defecto "inferno"')
    p.add_argument("--stops", nargs="+", metavar="HEX",
                    help="en vez de --name, una lista propia de colores para el degradado")
    p.add_argument("--invert", action="store_true",
                    help="negativo fotográfico en vez de colormap: ignora --name y --stops")
    p.add_argument("--kmeans", type=int, metavar="CLASES",
                    help="clasifica en CLASES colores con k-means; con --name o --stops "
                         "pinta las clases con ese degradado, sin ellos conserva sus colores medios")
    p.add_argument("--smooth", type=int, metavar="N",
                    help="con --kmeans, filtro de mayoría de NxN (impar) para quitar píxeles sueltos")
    p.add_argument("--out", metavar="RUTA",
                    help="archivo de salida (por defecto, el mismo nombre con el colormap como sufijo)")
    return p.parse_args(argv)


def recolorear(imagen: Image.Image, *, mode: str = "colormap", name: str | None = "inferno",
               stops=None, colors: int | None = None, smooth: int | None = None,
               channels: dict | None = None) -> Image.Image:
    """`name`/`stops` son el degradado en "colormap" (inferno si no llega
    ninguno) y, en "kmeans", el degradado opcional para pintar las clases
    (sin ellos cada clase conserva su color medio). `colors`/`smooth` solo
    aplican a "kmeans" y `channels` a "channels"."""
    spec: dict = {"mode": mode}
    if mode in ("colormap", "kmeans"):
        if stops:
            spec["stops"] = list(stops)
        elif name:
            spec["name"] = name
    if mode == "kmeans":
        spec.update({k: v for k, v in (("colors", colors), ("smooth", smooth)) if v is not None})
    if mode == "channels":
        spec["channels"] = channels
    return recolor.apply(imagen.convert("RGBA"), _SIN_USAR, spec)


def sufijo(mode: str, name: str | None = None, stops=None, colors: int | None = None) -> str:
    """El sufijo del archivo exportado, compartido con api/routes_recolor.py."""
    if mode == "invert":
        return "invertido"
    if mode == "invert_value":
        return "tonos_invertidos"
    if mode == "none":
        return "redimensionado"
    if mode == "channels":
        return "canales"
    degradado = "personalizado" if stops else name
    if mode == "kmeans":
        return "_".join(filter(None, (f"kmeans{colors or 6}", degradado)))
    return degradado or "inferno"


def main(argv=None) -> int:
    args = parse_args(argv)
    origen = Path(args.imagen)
    if args.invert:
        modo = "invert"
    elif args.kmeans is not None:
        modo = "kmeans"
    else:
        modo = "colormap"
    try:
        with Image.open(origen) as im:
            salida = recolorear(im, mode=modo, name=args.name, stops=args.stops,
                                colors=args.kmeans, smooth=args.smooth)
    except FileNotFoundError:
        print(f"error: no existe {origen}", file=sys.stderr)
        return 2
    except SpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    final = sufijo(modo, args.name, args.stops, args.kmeans)
    destino = Path(args.out) if args.out else origen.with_stem(f"{origen.stem}_{final}")
    salida.convert("RGB").save(destino)
    print(f"guardado {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
