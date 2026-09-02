"""Selección ponderada de una imagen entre varias candidatas.

Un `pool` es una capa que no fija un único archivo: da una lista o un glob de
candidatas y deja que Proun elija una por wallpaper. La elección no es "la que
mejor calza", que sería determinista y mataría la variedad entre semillas del
mismo lote: es un sorteo ponderado hacia las que retienen más área al
recortarlas contra el hueco de destino, considerando también su mejor
orientación (girada 90° o no), igual que `crop.auto_rotate`.

Si la capa no declara `crop.aspect`, no hay hueco que calzar: el sorteo es
uniforme, como cualquier lista.
"""

from __future__ import annotations

import random
from pathlib import Path

from . import loading
from .errors import SpecError
from .geometry import fit_box


def choose(paths: tuple[Path, ...], aspect: float | None, bias: float,
          rng: random.Random) -> Path:
    """Sortea un candidato de `paths`, ponderado por `aspect` si se conoce."""
    if not paths:
        raise SpecError("el pool de una capa está vacío")
    if aspect is None:
        return rng.choice(paths)
    pesos = [_weight(p, aspect, bias) for p in paths]
    return rng.choices(paths, weights=pesos, k=1)[0]


def _weight(path: Path, aspect: float, bias: float) -> float:
    """Qué tan bien calza `path` contra `aspect`, elevado a `bias`.

    1.0 es un calce perfecto (no se pierde nada al recortar); valores más
    chicos son peores calces. `bias` decide qué tan fuerte castiga un mal
    calce: en 1 el sorteo es proporcional al área retenida, más alto lo hace
    casi determinista hacia las mejores, más bajo lo acerca a un sorteo parejo.
    """
    w, h = loading.peek_size(path)
    directo = fit_box((w, h), aspect)
    girado = fit_box((h, w), aspect)
    mejor = max(directo[0] * directo[1], girado[0] * girado[1])
    retencion = mejor / (w * h)
    return max(retencion, 1e-6) ** bias