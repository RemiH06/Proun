"""Fondo del wallpaper.

Formas aceptadas en `background`:
    "auto"                          degradado suave derivado del color principal
    "#101018" / [16, 16, 24]        color sólido
    {"solid": "auto"}               sólido derivado del color principal
    {"gradient": ["auto", "#000"]}  degradado explícito
    {"gradient": [...], "direction": "vertical"|"horizontal"|"diagonal"|"radial"}
"auto" dentro de un color significa "una sombra del color principal".
"""

from __future__ import annotations

from PIL import Image

from .. import colors
from ..errors import SpecError

DIRECTIONS = ("vertical", "horizontal", "diagonal", "radial")


def build(size: tuple[int, int], main, spec="auto") -> Image.Image:
    if spec is None:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    if isinstance(spec, (str, list, tuple)):
        spec = {"gradient": ["auto", "auto_dark"]} if spec == "auto" else {"solid": spec}
    if not isinstance(spec, dict):
        raise SpecError(f"background inválido: {spec!r}")

    unknown = set(spec) - {"solid", "gradient", "direction"}
    if unknown:
        raise SpecError(f"claves desconocidas en background: {sorted(unknown)}")

    modes = {"solid", "gradient"} & set(spec)
    if not modes:
        raise SpecError("background necesita solid o gradient")
    if len(modes) > 1:
        raise SpecError("background admite solid o gradient, no los dos")

    if "solid" in spec:
        if "direction" in spec:
            raise SpecError("background.direction solo tiene sentido con gradient")
        return Image.new("RGBA", size, _color(spec["solid"], main, 0.18) + (255,))

    stops = spec.get("gradient")
    if not isinstance(stops, (list, tuple)) or len(stops) != 2:
        raise SpecError(f"background.gradient debe ser [color1, color2], llegó {stops!r}")
    start = _color(stops[0], main, 0.28)
    end = _color(stops[1], main, 0.08)

    direction = str(spec.get("direction", "vertical")).lower()
    if direction not in DIRECTIONS:
        raise SpecError(f"background.direction debe ser uno de {DIRECTIONS}")

    ramp = _ramp(start, end)
    if direction == "radial":
        mask = Image.radial_gradient("L").resize(size, Image.Resampling.BILINEAR)
        base = Image.new("RGB", size, start)
        return Image.composite(Image.new("RGB", size, end), base, mask).convert("RGBA")
    if direction == "horizontal":
        return ramp.resize(size, Image.Resampling.BILINEAR).convert("RGBA")
    if direction == "vertical":
        # ROTATE_270 y no rotate(90): este deja el primer color arriba, igual
        # que horizontal lo deja a la izquierda. rotate(90) los invertía.
        vertical = ramp.transpose(Image.Transpose.ROTATE_270)
        return vertical.resize(size, Image.Resampling.BILINEAR).convert("RGBA")
    # Un degradado no tiene detalle fino: se arma chico, se gira y se escala.
    # Así el diagonal no cuesta memoria aunque el wallpaper sea 8K.
    side = 512
    turned = ramp.resize((side, side), Image.Resampling.BILINEAR).rotate(
        45, resample=Image.Resampling.BILINEAR, expand=True
    )
    radius = side * 0.7071  # media diagonal del cuadrado girado
    half_h = radius / (1 + size[0] / size[1])
    half_w = half_h * size[0] / size[1]
    cx, cy = turned.width / 2, turned.height / 2
    inner = turned.crop((
        round(cx - half_w), round(cy - half_h), round(cx + half_w), round(cy + half_h),
    ))
    return inner.resize(size, Image.Resampling.BILINEAR).convert("RGBA")


def _ramp(start, end, steps: int = 256) -> Image.Image:
    ramp = Image.new("RGB", (steps, 1))
    ramp.putdata([colors.mix(start, end, i / (steps - 1)) for i in range(steps)])
    return ramp


def _color(value, main, default_factor: float):
    if isinstance(value, str):
        key = value.strip().lower()
        if key == "auto":
            return colors.shade(main, default_factor)
        if key == "auto_dark":
            return colors.shade(main, default_factor * 0.4)
        if key == "auto_light":
            return colors.shade(main, 1.0 + default_factor)
    return colors.parse(value)