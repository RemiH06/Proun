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

MODES = ("scatter", "free", "grid", "row", "column", "stack")


def positions(count: int, rng: random.Random, spec=None) -> list[tuple[float, float]]:
    """Centros normalizados para `count` capas."""
    if count < 0:
        raise SpecError(f"conteo de capas negativo: {count}")
    if count == 0:
        return []
    if spec is not None and not isinstance(spec, dict):
        raise SpecError(f"layout debe ser un objeto, llegó {spec!r}")
    spec = dict(spec or {})
    unknown = set(spec) - {"mode", "bleed", "jitter", "shuffle", "size"}
    if unknown:
        raise SpecError(f"claves desconocidas en layout: {sorted(unknown)}")

    mode = str(spec.get("mode", "scatter")).lower()
    if mode not in MODES:
        raise SpecError(f"layout.mode debe ser uno de {MODES}, llegó {mode!r}")
    bleed = _unit(spec.get("bleed", 0.12), "layout.bleed", high=1.0)
    jitter = _unit(spec.get("jitter", 0.12), "layout.jitter", high=1.0)

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


def _unit(value, name, high=1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= high:
        raise SpecError(f"{name} debe estar entre 0 y {high}, llegó {value!r}")
    return float(value)