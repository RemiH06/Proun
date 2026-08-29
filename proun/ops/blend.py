"""Pegado de una capa sobre el lienzo, con opacidad y modo de fusión.

Se permite que la capa salga del lienzo: se recorta la parte visible y se pega
solo eso, así que las posiciones negativas o desbordadas son válidas.
"""

from __future__ import annotations

from PIL import Image, ImageChops

from ..errors import SpecError

MODES = {
    "normal": None,
    "multiply": ImageChops.multiply,
    "screen": ImageChops.screen,
    "overlay": ImageChops.overlay,
    "soft_light": ImageChops.soft_light,
    "hard_light": ImageChops.hard_light,
    "add": ImageChops.add,
    "subtract": ImageChops.subtract,
    "difference": ImageChops.difference,
    "lighter": ImageChops.lighter,
    "darker": ImageChops.darker,
}


def _position(value) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"la posición debe ser [x, y], llegó {value!r}")
    out = []
    for coord in value:
        if isinstance(coord, bool) or not isinstance(coord, (int, float)):
            raise SpecError(f"la posición debe llevar números, llegó {coord!r}")
        out.append(round(coord))
    return (out[0], out[1])


def composite(
    canvas: Image.Image,
    layer: Image.Image,
    position: tuple[int, int],
    mode: str = "normal",
    opacity: float = 1.0,
) -> Image.Image:
    """Pega `layer` sobre `canvas` en su lugar. Devuelve el mismo lienzo."""
    mode = str(mode).lower()
    if mode not in MODES:
        raise SpecError(f"blend debe ser uno de {sorted(MODES)}, llegó {mode!r}")
    if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not 0 <= opacity <= 1:
        raise SpecError(f"opacity debe estar entre 0 y 1, llegó {opacity!r}")
    if opacity == 0:
        return canvas

    x, y = _position(position)
    left, top = max(x, 0), max(y, 0)
    right, bottom = min(x + layer.width, canvas.width), min(y + layer.height, canvas.height)
    if right <= left or bottom <= top:
        return canvas
    if (left, top, right, bottom) != (x, y, x + layer.width, y + layer.height):
        layer = layer.crop((left - x, top - y, right - x, bottom - y))

    if opacity < 1.0:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: round(v * opacity)))

    if mode != "normal":
        base = canvas.crop((left, top, right, bottom)).convert("RGB")
        fused = MODES[mode](base, layer.convert("RGB")).convert("RGBA")
        fused.putalpha(layer.getchannel("A"))
        layer = fused

    canvas.alpha_composite(layer, (left, top))
    return canvas