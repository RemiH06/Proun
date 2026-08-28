"""Rotación de una capa, con preferencia por múltiplos de 90 grados.

Los múltiplos de 90 se hacen con `transpose`, que no interpola ni un pixel.
Cualquier otro ángulo pasa por `rotate` con expansión y suavizado.

Formas aceptadas en `rotate`:
    90                      ángulo fijo
    "random" / "quarter"    elige entre 0, 90, 180 y 270
    [0, 90, 270]            elige uno de esos ángulos
    {"angles": [0, 180]}    lo mismo
    {"range": [-8, 8], "step": 2}   ángulo libre dentro del rango
    {"flip": "random"}      espejado horizontal, vertical, ambos o ninguno
"""

from __future__ import annotations

import random

from PIL import Image

from ..errors import SpecError

QUARTERS = (0, 90, 180, 270)

_TRANSPOSE = {
    90: Image.Transpose.ROTATE_90,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_270,
}

_FLIPS = {
    "none": (),
    "horizontal": (Image.Transpose.FLIP_LEFT_RIGHT,),
    "vertical": (Image.Transpose.FLIP_TOP_BOTTOM,),
    "both": (Image.Transpose.FLIP_LEFT_RIGHT, Image.Transpose.FLIP_TOP_BOTTOM),
}


def decide(spec, rng: random.Random) -> tuple[float, str]:
    """Resuelve el ángulo y el espejado antes de tocar pixeles.

    Va aparte de `apply` para que el sorteo ocurra una sola vez por wallpaper y
    la misma semilla dé la misma composición en todas las resoluciones.
    """
    if spec is None or spec is False:
        return (0.0, "none")
    if isinstance(spec, str) or isinstance(spec, (int, float)) and not isinstance(spec, bool):
        spec = {"angles": spec}
    elif isinstance(spec, (list, tuple)):
        spec = {"angles": list(spec)}
    if not isinstance(spec, dict):
        raise SpecError(f"rotate debe ser un ángulo, una lista o un objeto, llegó {spec!r}")

    unknown = set(spec) - {"angles", "range", "step", "flip"}
    if unknown:
        raise SpecError(f"claves desconocidas en rotate: {sorted(unknown)}")

    if "angles" in spec and "range" in spec:
        raise SpecError("rotate admite angles o range, no los dos")
    if "step" in spec and "range" not in spec:
        raise SpecError("rotate.step solo tiene sentido junto a rotate.range")

    angle = 0.0
    if "angles" in spec:
        angle = _from_angles(spec["angles"], rng)
    elif "range" in spec:
        angle = _from_range(spec["range"], spec.get("step"), rng)

    flip = spec.get("flip", "none")
    flip = str(flip).lower() if flip is not None else "none"
    if flip == "random":
        flip = rng.choice(list(_FLIPS))
    if flip not in _FLIPS:
        raise SpecError(f"rotate.flip debe ser uno de {sorted(_FLIPS)} o 'random'")
    return (angle, flip)


def apply(im: Image.Image, angle: float, flip: str = "none") -> Image.Image:
    for op in _FLIPS[flip]:
        im = im.transpose(op)
    angle = float(angle) % 360
    if angle == 0:
        return im
    if angle in _TRANSPOSE:
        return im.transpose(_TRANSPOSE[angle])
    return im.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)


def _from_angles(value, rng):
    if isinstance(value, str):
        key = value.strip().lower()
        if key in ("random", "quarter", "quarters", "random90", "90"):
            return float(rng.choice(QUARTERS))
        if key == "none":
            return 0.0
        raise SpecError(f"rotate desconocido: {value!r}. Usa un número, una lista o 'random'")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, (list, tuple)):
        if not value:
            raise SpecError("rotate.angles está vacío")
        # Se valida la lista entera y no solo el elegido: si no, una lista con
        # basura pasaría o fallaría según la semilla que tocara.
        for item in value:
            if not isinstance(item, (int, float)) or isinstance(item, bool):
                raise SpecError(f"rotate.angles solo admite números, llegó {item!r}")
        return float(rng.choice(list(value)))
    raise SpecError(f"rotate.angles inválido: {value!r}")


def _from_range(value, step, rng):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"rotate.range debe ser [mínimo, máximo], llegó {value!r}")
    low, high = float(value[0]), float(value[1])
    if low > high:
        low, high = high, low
    if step in (None, 0):
        return rng.uniform(low, high)
    if not isinstance(step, (int, float)) or isinstance(step, bool) or step < 0:
        raise SpecError(f"rotate.step debe ser un número no negativo, llegó {step!r}")
    pasos = int((high - low) / step)
    return low + step * rng.randint(0, pasos)