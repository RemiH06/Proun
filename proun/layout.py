"""Dónde cae cada capa.

Las posiciones se calculan en coordenadas normalizadas (0..1 sobre el lienzo,
tomando el centro de la capa como referencia). Al ser relativas, la misma
semilla produce la misma composición en 1920x1080 y en 3840x2160.

Modos:
    scatter  (por defecto) al azar pero repartido: cada capa cae en su propia
             celda de una cuadrícula suelta, así el azar no deja media pantalla
             vacía. El solapamiento sigue siendo libre
    free     azar puro y duro, sin repartir
    grid     una celda por capa, en cuadrícula automática, con temblor opcional
    row      repartidas en horizontal
    column   repartidas en vertical
    stack    todas al centro, apiladas
"""

from __future__ import annotations

import math
import random

from .errors import SpecError
from .geometry import anchor_factors, measure

MODES = ("scatter", "free", "grid", "row", "column", "stack", "align")


def positions(count: int, rng: random.Random, spec=None) -> list[tuple[float, float]]:
    """Centros normalizados para `count` capas."""
    if count < 0:
        raise SpecError(f"conteo de capas negativo: {count}")
    if count == 0:
        return []
    if spec is not None and not isinstance(spec, dict):
        raise SpecError(f"layout debe ser un objeto, llegó {spec!r}")
    spec = dict(spec or {})
    unknown = set(spec) - {"mode", "bleed", "jitter", "shuffle", "size"} - PACK_KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en layout: {sorted(unknown)}")

    mode = str(spec.get("mode", "scatter")).lower()
    if mode not in MODES:
        raise SpecError(f"layout.mode debe ser uno de {MODES}, llegó {mode!r}")
    bleed = _unit(spec.get("bleed", 0.12), "layout.bleed", high=1.0)
    jitter = _unit(spec.get("jitter", 0.12), "layout.jitter", high=1.0)

    if mode == "align":
        # La posición real se calcula después, en compose.prepare, porque
        # depende del tamaño en píxeles de cada capa y eso todavía no se
        # conoce aquí. No consume el generador: no hay nada que sortear.
        return [(0.5, 0.5)] * count
    if mode == "free":
        return [
            (rng.uniform(-bleed, 1 + bleed), rng.uniform(-bleed, 1 + bleed))
            for _ in range(count)
        ]
    if mode == "scatter":
        return _scatter(count, rng, bleed)
    if mode == "stack":
        return [
            (0.5 + rng.uniform(-jitter, jitter), 0.5 + rng.uniform(-jitter, jitter))
            for _ in range(count)
        ]
    if mode == "row":
        cols, rows = count, 1
    elif mode == "column":
        cols, rows = 1, count
    else:
        cols = max(1, round(math.sqrt(count)))
        rows = math.ceil(count / cols)

    cells = [(c, r) for r in range(rows) for c in range(cols)][:count]
    if spec.get("shuffle", True):
        rng.shuffle(cells)
    out = []
    for col, row in cells:
        cx = (col + 0.5) / cols + rng.uniform(-jitter, jitter) / cols
        cy = (row + 0.5) / rows + rng.uniform(-jitter, jitter) / rows
        out.append((cx, cy))
    return out


DEFAULT_SIZE = (0.38, 0.82)


def sizes(count: int, rng: random.Random, spec=None) -> list[float]:
    """Fracción del lienzo que ocupa cada capa cuando no trae `resize` propio.

    Sin esto un collage de fotos chicas sobre un 4K se vería como estampitas
    perdidas en la esquina. Se sortea aquí, con la semilla, para que el tamaño
    también sea reproducible.
    """
    if spec is not None and not isinstance(spec, dict):
        raise SpecError(f"layout debe ser un objeto, llegó {spec!r}")
    value = (spec or {}).get("size", DEFAULT_SIZE)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = (value, value)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"layout.size debe ser un número o [mínimo, máximo], llegó {value!r}")
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise SpecError(f"layout.size debe llevar números, llegó {v!r}")
    low, high = float(value[0]), float(value[1])
    if not 0 < low <= high <= 8:
        raise SpecError(f"layout.size fuera de rango (0, 8]: {value!r}")
    return [rng.uniform(low, high) for _ in range(count)]


def _scatter(count, rng, bleed):
    """Azar estratificado: una celda por capa, posición libre dentro de la celda."""
    cols = max(1, round(math.sqrt(count)))
    rows = math.ceil(count / cols)
    cells = [(c, r) for r in range(rows) for c in range(cols)]
    rng.shuffle(cells)
    span = 1 + 2 * bleed
    out = []
    for col, row in cells[:count]:
        cx = rng.uniform(col / cols, (col + 1) / cols)
        cy = rng.uniform(row / rows, (row + 1) / rows)
        out.append((-bleed + cx * span, -bleed + cy * span))
    return out


def to_pixels(center, size: tuple[int, int], canvas: tuple[int, int]) -> tuple[int, int]:
    """Pasa de centro normalizado a esquina superior izquierda en píxeles."""
    return (
        round(center[0] * canvas[0] - size[0] / 2),
        round(center[1] * canvas[1] - size[1] / 2),
    )


def explicit(value, size, canvas, anchor="center", rng=None) -> tuple[int, int]:
    """Resuelve una posición declarada a mano en la capa.

    Enteros son píxeles y flotantes son fracciones del lienzo, igual que en el
    resto de la herramienta. El ancla dice qué punto de la capa se coloca ahí.
    """
    if isinstance(value, str):
        fx, fy = anchor_factors(value, rng)
        return (round((canvas[0] - size[0]) * fx), round((canvas[1] - size[1]) * fy))
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"position debe ser [x, y] o un ancla nombrada, llegó {value!r}")
    px = [
        measure(v, canvas[i], name=f"position[{eje}]", minimum=None)
        for i, (v, eje) in enumerate(zip(value, "xy"))
    ]
    ax, ay = anchor_factors(anchor, rng)
    return (round(px[0] - size[0] * ax), round(px[1] - size[1] * ay))


def clamp(position, size, canvas, bleed) -> tuple[int, int]:
    """Limita cuánto se sale una capa del lienzo.

    `bleed` es fracción del tamaño de la propia capa: 0 la deja completamente
    dentro y 1 le permite salirse entera. Se aplica al colocar, no al sortear,
    porque hasta ese momento no se sabe cuánto mide la capa.
    """
    salida = []
    for eje in (0, 1):
        margen = round(size[eje] * bleed[eje])
        minimo = -margen
        maximo = canvas[eje] - size[eje] + margen
        if minimo > maximo:
            # La capa es más grande que el lienzo más el margen: se centra.
            salida.append(round((canvas[eje] - size[eje]) / 2))
        else:
            salida.append(min(max(position[eje], minimo), maximo))
    return (salida[0], salida[1])


PACK_KEYS = {"width", "gap", "anchor"}
PACK_ANCHORS = ("top", "center", "bottom")


def pack(sizes, width: int, gap: int = 0):
    """Coloca rectángulos sin solaparse con skyline bottom-left.

    Cada pieza cae en el hueco más alto disponible dentro de `width`, tocando a
    sus vecinas por los lados y por abajo, como una estantería. `sizes` va en
    el orden en que deben colocarse; normalmente ya viene revuelto por la
    semilla, y ese orden es lo único de lo que depende el resultado, así que es
    determinista sin tocar el generador aleatorio.

    Una pieza más ancha que `width` no se recorta: se le da su propio ancho de
    contenedor, así que el bloque final puede terminar más ancho de lo pedido.

    Devuelve las esquinas superiores izquierdas en el mismo orden que `sizes`,
    y el tamaño del bloque que las contiene a todas.
    """
    if not sizes:
        return [], (0, 0)
    ancho = max(width, max(w for w, _ in sizes)) + gap
    skyline = [[0, ancho, 0]]  # segmentos contiguos [x, ancho, y]

    posiciones = []
    for w, h in sizes:
        # Se reserva w+gap y h+gap, pero la pieza se dibuja en el mismo punto:
        # así el hueco queda a la derecha y abajo de cada pieza, no alrededor.
        x, y, idx = _best_fit(skyline, w + gap, ancho)
        posiciones.append((x, y))
        _place(skyline, x, w + gap, y + h + gap)

    block_w = max(x + w for (x, _), (w, _h) in zip(posiciones, sizes))
    block_h = max(y + h for (_, y), (_w, h) in zip(posiciones, sizes))
    return posiciones, (block_w, block_h)


def _best_fit(skyline, w: int, ancho: int):
    """El punto más alto (menor y) donde cabe un ancho w; a igualdad, el más a la izquierda."""
    mejor_y = None
    mejor_x = None
    mejor_indice = None
    for i in range(len(skyline)):
        x0 = skyline[i][0]
        if x0 + w > ancho:
            continue
        y = 0
        cubierto = 0
        j = i
        while cubierto < w and j < len(skyline):
            y = max(y, skyline[j][2])
            cubierto += skyline[j][1]
            j += 1
        if cubierto < w:
            continue
        if mejor_y is None or y < mejor_y or (y == mejor_y and x0 < mejor_x):
            mejor_y, mejor_x, mejor_indice = y, x0, i
    if mejor_x is None:
        # No debería pasar: `ancho` se calculó para que la pieza más ancha quepa.
        raise SpecError(f"no se encontró lugar para una pieza de {w}px en un bloque de {ancho}px")
    return mejor_x, mejor_y, mejor_indice


def _place(skyline, x: int, w: int, y: int) -> None:
    """Inserta un segmento nuevo en [x, x+w) a altura y, recortando lo que tapa."""
    nuevo = []
    for seg_x, seg_w, seg_y in skyline:
        seg_end, x_end = seg_x + seg_w, x + w
        if seg_end <= x or seg_x >= x_end:
            nuevo.append([seg_x, seg_w, seg_y])
            continue
        if seg_x < x:
            nuevo.append([seg_x, x - seg_x, seg_y])
        if seg_end > x_end:
            nuevo.append([x_end, seg_end - x_end, seg_y])
    nuevo.append([x, w, y])
    nuevo.sort(key=lambda s: s[0])
    # Fusiona segmentos vecinos con la misma altura, para que la lista no crezca sin fin.
    fusionado = [nuevo[0]]
    for seg in nuevo[1:]:
        anterior = fusionado[-1]
        if anterior[2] == seg[2] and anterior[0] + anterior[1] == seg[0]:
            anterior[1] += seg[1]
        else:
            fusionado.append(seg)
    skyline[:] = fusionado


def center_block(block_size, canvas, anchor="center") -> tuple[int, int]:
    """Esquina donde colocar un bloque ya empaquetado para centrarlo en el lienzo.

    Horizontal siempre al centro. Vertical según `anchor`: top, center o bottom,
    que es lo que deja la banda de papel vacío arriba y abajo o la empuja hacia
    un lado.
    """
    if anchor not in PACK_ANCHORS:
        raise SpecError(f"layout.anchor debe ser uno de {PACK_ANCHORS}, llegó {anchor!r}")
    x = round((canvas[0] - block_size[0]) / 2)
    if anchor == "top":
        y = 0
    elif anchor == "bottom":
        y = canvas[1] - block_size[1]
    else:
        y = round((canvas[1] - block_size[1]) / 2)
    return (x, y)


def pack_options(spec: dict) -> tuple[float, int, str]:
    """Lee width, gap y anchor del layout, con sus valores por defecto."""
    width = spec.get("width", 0.94)
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not 0 < width <= 1:
        raise SpecError(f"layout.width debe estar entre 0 y 1, llegó {width!r}")
    gap = spec.get("gap", 0)
    if isinstance(gap, bool) or not isinstance(gap, int) or gap < 0:
        raise SpecError(f"layout.gap debe ser un entero no negativo, llegó {gap!r}")
    anchor = str(spec.get("anchor", "center")).lower()
    return (float(width), gap, anchor)


def _unit(value, name, high=1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= high:
        raise SpecError(f"{name} debe estar entre 0 y {high}, llegó {value!r}")
    return float(value)