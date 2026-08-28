"""Colores: parseo, mezclas y espectros.

Un color puede escribirse como "#ff0088", "ff0088", "f08" o [255, 0, 136].
"""

from __future__ import annotations

import colorsys

from .errors import SpecError

RGB = tuple[int, int, int]

_HEX = set("0123456789abcdef")


def _byte(value) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise SpecError(f"componente de color inválido: {value!r}") from None
    if not 0 <= n <= 255:
        raise SpecError(f"componente de color fuera de rango 0..255: {n}")
    return n


def parse(value) -> RGB:
    """Normaliza cualquier representación aceptada a una tupla RGB."""
    if isinstance(value, (list, tuple)):
        if len(value) != 3:
            raise SpecError(f"se esperaban 3 componentes RGB, llegaron {len(value)}")
        return (_byte(value[0]), _byte(value[1]), _byte(value[2]))
    text = str(value).strip().lstrip("#").lower()
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6 or not set(text) <= _HEX:
        raise SpecError(f"color hexadecimal inválido: {value!r}")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def to_hex(rgb: RGB) -> str:
    """Devuelve el color en hexadecimal sin '#', tal como va en el nombre del archivo."""
    return "%02x%02x%02x" % parse(rgb)


def mix(a: RGB, b: RGB, t: float) -> RGB:
    """Interpola linealmente entre dos colores. t=0 devuelve a, t=1 devuelve b."""
    t = min(max(float(t), 0.0), 1.0)
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def shade(rgb: RGB, factor: float) -> RGB:
    """Oscurece (factor < 1) o aclara (factor > 1) un color.

    factor=0 da negro, factor=1 deja el color intacto y factor=2 da blanco.
    """
    if factor < 0:
        raise SpecError(f"factor de sombra negativo: {factor}")
    if factor <= 1:
        return mix((0, 0, 0), rgb, factor)
    return mix(rgb, (255, 255, 255), min(factor - 1.0, 1.0))


def hue_of(rgb: RGB) -> float:
    r, g, b = (c / 255.0 for c in parse(rgb))
    return colorsys.rgb_to_hsv(r, g, b)[0]


def spectrum(
    count: int,
    saturation: float = 0.62,
    value: float = 0.9,
    start: float = 0.0,
    span: float = 1.0,
) -> list[RGB]:
    """Genera `count` colores repartidos sobre un arco del círculo cromático.

    start y span van en vueltas (0..1): span=1 recorre todo el círculo,
    span=0.25 se queda en un cuarto a partir de start.
    """
    if count < 1:
        raise SpecError(f"un espectro necesita al menos un color, se pidieron {count}")
    for name, v in (("saturation", saturation), ("value", value)):
        if not 0.0 <= v <= 1.0:
            raise SpecError(f"{name} debe estar entre 0 y 1, llegó {v}")
    step = span / count if count > 1 else 0.0
    out = []
    for i in range(count):
        h = (start + step * i) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, saturation, value)
        out.append((round(r * 255), round(g * 255), round(b * 255)))
    return out