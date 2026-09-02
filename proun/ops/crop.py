"""Recorte de una capa.

Formas aceptadas en `crop`:
    [x, y, ancho, alto]              recorte explícito
    {"box": [x, y, ancho, alto]}     lo mismo
    {"aspect": "16:9"}               el recorte más grande con esa proporción
    {"aspect": "16:9", "auto_rotate": true}   igual, pero si girar la imagen
                                      90° deja un recorte más grande (pierde
                                      menos), gira antes de recortar
    {"margin": 0.1}                  quita margen por los cuatro lados
    {"margin": [x, y]}               margen horizontal y vertical
    {"margin": [i, s, d, inf]}       izquierda, superior, derecha, inferior
Todas admiten "anchor" (center por defecto, o "random" con semilla).
Enteros son píxeles, flotantes son fracciones del tamaño de la imagen.
"""

from __future__ import annotations

from PIL import Image

from ..errors import SpecError
from ..geometry import anchor_factors, fit_box, measure, parse_aspect, place_box


def apply(im: Image.Image, spec, rng=None) -> Image.Image:
    if not spec:
        return im
    if isinstance(spec, (list, tuple)):
        spec = {"box": list(spec)}
    if not isinstance(spec, dict):
        raise SpecError(f"crop debe ser una lista o un objeto, llegó {spec!r}")

    size = im.size
    unknown = set(spec) - {"box", "aspect", "margin", "anchor", "auto_rotate"}
    if unknown:
        raise SpecError(f"claves desconocidas en crop: {sorted(unknown)}")

    modes = {"box", "aspect", "margin"} & set(spec)
    if not modes:
        raise SpecError("crop necesita box, aspect o margin")
    if len(modes) > 1:
        raise SpecError(f"crop admite solo uno de box, aspect o margin: llegaron {sorted(modes)}")
    if "auto_rotate" in spec and "aspect" not in spec:
        raise SpecError("crop.auto_rotate solo tiene sentido junto a crop.aspect")

    if "box" in spec:
        raw = spec["box"]
        if not isinstance(raw, (list, tuple)) or len(raw) != 4:
            raise SpecError(f"crop.box debe ser [x, y, ancho, alto], llegó {raw!r}")
        x = measure(raw[0], size[0], name="crop.box[x]", minimum=0)
        y = measure(raw[1], size[1], name="crop.box[y]", minimum=0)
        w = measure(raw[2], size[0], name="crop.box[ancho]")
        h = measure(raw[3], size[1], name="crop.box[alto]")
        box = (x, y, x + w, y + h)
    elif "margin" in spec:
        left, top, right, bottom = _margins(spec["margin"], size)
        box = (left, top, size[0] - right, size[1] - bottom)
        if box[2] - box[0] < 1 or box[3] - box[1] < 1:
            raise SpecError(f"los márgenes {spec['margin']!r} no dejan imagen")
    elif "aspect" in spec:
        aspect = parse_aspect(spec["aspect"])
        if spec.get("auto_rotate", False):
            im, size = _best_orientation(im, size, aspect)
        inner = fit_box(size, aspect)
        x, y = place_box(inner, size, anchor_factors(spec.get("anchor", "center"), rng))
        box = (x, y, x + inner[0], y + inner[1])

    clipped = (
        max(0, box[0]),
        max(0, box[1]),
        min(size[0], box[2]),
        min(size[1], box[3]),
    )
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        raise SpecError(f"el recorte {box} queda fuera de la imagen de {size[0]}x{size[1]}")
    return im.crop(clipped)


def _best_orientation(im: Image.Image, size, aspect):
    """Compara recortar tal cual contra girar 90° primero, y se queda con lo
    que retiene más área. Un giro múltiplo de 90 no pierde nitidez, así que
    no cuesta nada probarlo."""
    directo = fit_box(size, aspect)
    girado_size = (size[1], size[0])
    girado = fit_box(girado_size, aspect)
    if girado[0] * girado[1] > directo[0] * directo[1]:
        return im.transpose(Image.Transpose.ROTATE_90), girado_size
    return im, size


def _margins(value, size) -> tuple[int, int, int, int]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = [value] * 4
    if not isinstance(value, (list, tuple)) or len(value) not in (2, 4):
        raise SpecError(f"crop.margin debe ser un número, un par o cuatro valores: {value!r}")
    if len(value) == 2:
        value = [value[0], value[1], value[0], value[1]]
    refs = (size[0], size[1], size[0], size[1])
    names = ("izquierdo", "superior", "derecho", "inferior")
    return tuple(  # type: ignore[return-value]
        measure(v, r, name=f"crop.margin {n}", minimum=0)
        for v, r, n in zip(value, refs, names)
    )