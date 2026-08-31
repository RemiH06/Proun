"""Fondo del wallpaper.

Formas aceptadas en `background`:
    "auto"                          degradado suave derivado del color principal
    "#101018" / [16, 16, 24]        color sólido
    {"solid": "auto"}               sólido derivado del color principal
    {"gradient": ["auto", "#000"]}  degradado explícito
    {"gradient": [...], "direction": "vertical"|"horizontal"|"diagonal"|"radial"}
    {"solid": "#f2efe8", "stain": {"amount": 0.3, "color": "#ddd6c6"}}

`stain` mancha el papel mismo: usa el mismo ruido de nubes que `ops/stain.py`,
pero en vez de comer transparencia mezcla entre el fondo y un segundo color. Es
lo que da la sensación de papel viejo debajo de las piezas.
"auto" dentro de un color significa "una sombra del color principal".
"""

from __future__ import annotations

from PIL import Image

from .. import colors
from . import stain as stain_op
from ..errors import SpecError

DIRECTIONS = ("vertical", "horizontal", "diagonal", "radial")

STAIN_KEYS = {"amount", "scale", "octaves", "threshold", "color", "invert"}


def build(size: tuple[int, int], main, spec="auto", rng=None) -> Image.Image:
    if spec is None:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    if isinstance(spec, (str, list, tuple)):
        spec = {"gradient": ["auto", "auto_dark"]} if spec == "auto" else {"solid": spec}
    if not isinstance(spec, dict):
        raise SpecError(f"background inválido: {spec!r}")

    unknown = set(spec) - {"solid", "gradient", "direction", "stain"}
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
        base = Image.new("RGBA", size, _color(spec["solid"], main, 0.18) + (255,))
        return _stain(base, spec.get("stain"), main, rng)

    stops = spec.get("gradient")
    if not isinstance(stops, (list, tuple)) or len(stops) != 2:
        raise SpecError(f"background.gradient debe ser [color1, color2], llegó {stops!r}")
    start = _color(stops[0], main, 0.28)
    end = _color(stops[1], main, 0.08)

    direction = str(spec.get("direction", "vertical")).lower()
    if direction not in DIRECTIONS:
        raise SpecError(f"background.direction debe ser uno de {DIRECTIONS}")

    ramp = _ramp(start, end)
    manchar = lambda im: _stain(im, spec.get("stain"), main, rng)  # noqa: E731
    if direction == "radial":
        mask = Image.radial_gradient("L").resize(size, Image.Resampling.BILINEAR)
        base = Image.new("RGB", size, start)
        return manchar(Image.composite(Image.new("RGB", size, end), base, mask).convert("RGBA"))
    if direction == "horizontal":
        return manchar(ramp.resize(size, Image.Resampling.BILINEAR).convert("RGBA"))
    if direction == "vertical":
        # ROTATE_270 y no rotate(90): este deja el primer color arriba, igual
        # que horizontal lo deja a la izquierda. rotate(90) los invertía.
        vertical = ramp.transpose(Image.Transpose.ROTATE_270)
        return manchar(vertical.resize(size, Image.Resampling.BILINEAR).convert("RGBA"))
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
    return manchar(inner.resize(size, Image.Resampling.BILINEAR).convert("RGBA"))


def _stain(base: Image.Image, spec, main, rng) -> Image.Image:
    """Mancha el fondo mezclando hacia otro color con ruido de nubes."""
    if not spec:
        return base
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        spec = {"amount": spec}
    if not isinstance(spec, dict):
        raise SpecError(f"background.stain debe ser un número o un objeto, llegó {spec!r}")
    unknown = set(spec) - STAIN_KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en background.stain: {sorted(unknown)}")
    amount = spec.get("amount", 0.3)
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not 0 <= amount <= 1:
        raise SpecError(f"background.stain.amount debe estar entre 0 y 1, llegó {amount!r}")
    if amount == 0:
        return base
    if rng is None:
        raise SpecError(
            "background.stain necesita un generador aleatorio para ser reproducible"
        )

    nubes = stain_op.clouds(base.size, spec, rng)
    tinte = spec.get("color", "auto")
    color = colors.shade(main, 0.55) if tinte == "auto" else colors.parse(tinte)
    mascara = nubes.point([round(i * amount) for i in range(256)])
    return Image.composite(
        Image.new("RGBA", base.size, color + (255,)), base, mascara
    )


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