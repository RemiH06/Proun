"""Selección ponderada de una imagen entre varias candidatas.

Un `pool` es una capa que no fija un único archivo: da una lista o un glob de
candidatas y deja que Proun elija una por wallpaper. La elección no es "la que
mejor calza", que sería determinista y mataría la variedad entre semillas del
mismo lote: es un sorteo ponderado hacia las que retienen más área al
recortarlas contra el hueco de destino, considerando también su mejor
orientación (girada 90° o no), igual que `crop.auto_rotate`.

Si la capa no declara `crop.aspect`, no hay hueco que calzar: el sorteo es
uniforme, como cualquier lista.

Con `dark_bias` (0 por defecto, apagado), se suma un segundo criterio: qué
tan oscuro saldría el recorte después de `tones`. Es necesario porque la
misma foto puede dar un recorte bien iluminado en un hueco y un recorte de
puro piso o sombra en otro — el problema no es el archivo, es qué región de
ese archivo terminó ahí, y eso solo se sabe recortando y midiendo de verdad.
Por eso, a diferencia del peso por proporción (que solo lee las dimensiones
de cada candidata), este sí abre y procesa cada una en miniatura.

La medición se hace sobre la salida de `tones`, antes de `recolor`, así que
no depende de qué color tenga el lote: un pixel oscuro en escala de grises
va a mapear a sombra sin importar a qué color se traduzca después.
"""

from __future__ import annotations

import random
from pathlib import Path

from . import loading
from .errors import SpecError
from .geometry import fit_box
from .ops import crop as crop_op
from .ops import tones as tones_op

MINIATURA = 150  # suficiente para medir oscuridad, barato de procesar


def choose(paths: tuple[Path, ...], aspect: float | None, bias: float,
          rng: random.Random, *, crop_spec=None, tones_spec=None,
          dark_bias: float = 0.0) -> Path:
    """Sortea un candidato de `paths`, ponderado por `aspect` y, si se pide,
    por qué tan oscuro saldría el recorte."""
    if not paths:
        raise SpecError("el pool de una capa está vacío")
    if aspect is None and dark_bias <= 0:
        return rng.choice(paths)
    pesos = []
    for p in paths:
        peso = _weight(p, aspect, bias) if aspect is not None else 1.0
        if dark_bias > 0:
            peso *= _brightness_weight(p, crop_spec, tones_spec, dark_bias)
        pesos.append(peso)
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


def _brightness_weight(path: Path, crop_spec, tones_spec, dark_bias: float) -> float:
    """1.0 si el recorte sale todo claro, se acerca a 0 cuanto más oscuro.

    Reproduce en miniatura lo que le pasaría de verdad a esta capa (crop y
    tones), para que la medición sea sobre la región que realmente se usaría,
    no sobre la imagen completa.
    """
    im = loading.load(path)
    im.thumbnail((MINIATURA, MINIATURA))
    im = crop_op.apply(im, crop_spec)
    im = tones_op.apply(im, tones_spec if tones_spec is not None else True)
    gris = im.convert("L")
    oscuros = sum(gris.histogram()[:64])
    fraccion_oscura = oscuros / (gris.width * gris.height)
    return max(1.0 - fraccion_oscura, 1e-6) ** dark_bias