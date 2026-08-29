"""Recoloreado: mapea los tonos de una capa hacia el color del wallpaper.

Trabaja sobre lo que le llegue. Si antes pasó por `tones`, recibe grises ya
normalizados y el resultado es una paleta limpia; si no, recibe la imagen tal
cual y conserva su carácter original.

Modos:
    duotone   (por defecto) sombras y luces derivadas del color principal
    tint      multiplica los canales por el color, conserva la textura
    screen    aclara hacia el color, útil sobre fondos oscuros
    hue       impone el matiz, conserva saturación y luminosidad
    channels  ganancia y desplazamiento explícitos por canal r, g, b
    none      deja la capa tal cual

`strength` mezcla el resultado con una referencia, y `mix_with` dice cuál:
    tones   (por defecto) lo que le llegó a este módulo, o sea los grises
            normalizados. Bajar la fuerza da un duotono más pálido sin que
            reaparezca el color original.
    source  la imagen antes de `tones`. Bajar la fuerza deja asomar la foto.
            Solo funciona si quien llama pasa esa imagen en `source`.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageEnhance, ImageOps

from .. import colors
from ..errors import SpecError

MODES = ("duotone", "tint", "screen", "hue", "channels", "none")

MIX_SOURCES = ("tones", "source")

KEYS = {
    "mode", "strength", "mix_with", "color", "shadow", "highlight",
    "midpoint", "levels", "saturation", "channels",
}


def apply(im: Image.Image, main, spec=None, source: Image.Image | None = None) -> Image.Image:
    """Devuelve la capa recoloreada hacia `main` según `spec`."""
    spec = dict(spec or {})
    unknown = set(spec) - KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en recolor: {sorted(unknown)}")

    mode = str(spec.get("mode", "duotone")).lower()
    if mode not in MODES:
        raise SpecError(f"recolor.mode debe ser uno de {MODES}, llegó {mode!r}")
    strength = _unit(spec.get("strength", 1.0), "recolor.strength")
    if mode == "none" or strength == 0:
        return im

    main = colors.parse(spec.get("color", main))
    alpha = im.getchannel("A")
    base = im.convert("RGB")

    if mode == "duotone":
        out = _duotone(ImageOps.grayscale(base), main, spec)
    elif mode == "tint":
        out = ImageChops.multiply(base, Image.new("RGB", base.size, main))
    elif mode == "screen":
        out = ImageChops.screen(base, Image.new("RGB", base.size, main))
    elif mode == "hue":
        out = _hue(base, main, spec)
    else:
        out = _channels(base, spec)

    saturation = spec.get("saturation")
    if saturation is not None and mode != "hue":
        out = ImageEnhance.Color(out).enhance(_saturation(saturation))

    if strength < 1.0:
        out = Image.blend(_reference(base, spec, source), out, strength)

    out = out.convert("RGBA")
    out.putalpha(alpha)
    return out


def _reference(base: Image.Image, spec, source) -> Image.Image:
    """La imagen contra la que mezcla `strength`."""
    mix_with = str(spec.get("mix_with", "tones")).lower()
    if mix_with not in MIX_SOURCES:
        raise SpecError(f"recolor.mix_with debe ser uno de {MIX_SOURCES}, llegó {mix_with!r}")
    if mix_with == "tones":
        return base
    if source is None:
        raise SpecError(
            'recolor.mix_with = "source" necesita la imagen previa a tones y no llegó ninguna'
        )
    if source.size != base.size:
        raise SpecError(
            f"la imagen de referencia mide {source.size} y la capa {base.size}: "
            "tienen que coincidir para poder mezclarlas"
        )
    return source.convert("RGB")


def _duotone(gray: Image.Image, main, spec) -> Image.Image:
    shadow = colors.parse(spec["shadow"]) if "shadow" in spec else colors.shade(main, 0.22)
    highlight = colors.parse(spec["highlight"]) if "highlight" in spec else colors.shade(main, 1.7)
    black, white = _levels(spec.get("levels"))
    mid = spec.get("midpoint", 128)
    if isinstance(mid, bool) or not isinstance(mid, int) or not black < mid < white:
        raise SpecError(f"recolor.midpoint debe quedar entre {black} y {white}, llegó {mid!r}")
    return ImageOps.colorize(
        gray, black=shadow, white=highlight, mid=main,
        blackpoint=black, whitepoint=white, midpoint=mid,
    )


def _hue(base: Image.Image, main, spec) -> Image.Image:
    h, s, v = base.convert("HSV").split()
    flat = Image.new("L", base.size, round(colors.hue_of(main) * 255))
    saturation = spec.get("saturation")
    if saturation is not None:
        factor = _saturation(saturation)
        s = s.point([min(255, round(i * factor)) for i in range(256)])
    return Image.merge("HSV", (flat, s, v)).convert("RGB")


def _channels(base: Image.Image, spec) -> Image.Image:
    raw = spec.get("channels")
    if not isinstance(raw, dict) or not raw:
        raise SpecError('el modo "channels" necesita recolor.channels, por ejemplo {"r": [1.2, 10]}')
    unknown = set(raw) - {"r", "g", "b"}
    if unknown:
        raise SpecError(f"canales desconocidos: {sorted(unknown)}. Solo r, g y b")
    bands = dict(zip("rgb", base.split()))
    for name, setting in raw.items():
        if isinstance(setting, (int, float)) and not isinstance(setting, bool):
            gain, offset = float(setting), 0.0
        elif isinstance(setting, (list, tuple)) and len(setting) == 2:
            gain, offset = float(setting[0]), float(setting[1])
        else:
            raise SpecError(f"channels.{name} debe ser ganancia o [ganancia, desplazamiento]")
        bands[name] = bands[name].point(
            [min(255, max(0, round(i * gain + offset))) for i in range(256)]
        )
    return Image.merge("RGB", (bands["r"], bands["g"], bands["b"]))


def _levels(value) -> tuple[int, int]:
    if value is None:
        return (0, 255)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"recolor.levels debe ser [negro, blanco], llegó {value!r}")
    try:
        black, white = int(value[0]), int(value[1])
    except (TypeError, ValueError):
        raise SpecError(f"recolor.levels debe llevar dos enteros, llegó {value!r}") from None
    if not 0 <= black < white <= 255:
        raise SpecError(f"recolor.levels fuera de rango: {value!r}")
    return (black, white)


def _unit(value, name) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise SpecError(f"{name} debe estar entre 0 y 1, llegó {value!r}")
    return float(value)


def _saturation(value) -> float:
    """0 desatura del todo, 1 deja igual, más de 1 exagera. El cero es válido."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 10:
        raise SpecError(f"recolor.saturation debe estar entre 0 y 10, llegó {value!r}")
    return float(value)