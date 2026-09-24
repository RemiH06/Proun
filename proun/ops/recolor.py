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
    colormap  degradado de varios colores (`name`, ver COLORMAPS, o una
              lista propia en `stops`), no depende del color principal
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

MODES = ("duotone", "tint", "screen", "hue", "channels", "colormap", "none")

MIX_SOURCES = ("tones", "source")

KEYS = {
    "mode", "strength", "mix_with", "color", "shadow", "highlight",
    "midpoint", "levels", "saturation", "channels", "name", "stops",
}

# Degradados con nombre para el modo "colormap". Puntos de control de la
# familia perceptualmente uniforme de matplotlib (la misma que trae ArcGIS
# Pro de fábrica para datos continuos), aproximados a mano: no son los 256
# valores oficiales, pero alcanzan para que se reconozcan a simple vista.
COLORMAPS = {
    "inferno": (
        (0, 0, 4), (31, 12, 72), (85, 15, 109), (136, 34, 106),
        (186, 54, 85), (227, 89, 51), (249, 140, 10), (249, 201, 50),
        (252, 255, 164),
    ),
    "viridis": (
        (68, 1, 84), (72, 40, 120), (62, 74, 137), (49, 104, 142),
        (38, 130, 142), (31, 158, 137), (53, 183, 121), (109, 205, 89),
        (180, 222, 44), (253, 231, 37),
    ),
    "plasma": (
        (13, 8, 135), (75, 3, 161), (125, 3, 168), (168, 34, 150),
        (203, 70, 121), (229, 107, 93), (248, 148, 65), (253, 195, 40),
        (240, 249, 33),
    ),
    "magma": (
        (0, 0, 4), (28, 16, 68), (79, 18, 123), (129, 37, 129),
        (181, 54, 122), (229, 80, 100), (251, 135, 97), (254, 194, 135),
        (252, 253, 191),
    ),
    "cividis": (
        (0, 32, 76), (0, 42, 102), (48, 63, 111), (89, 84, 116),
        (127, 106, 120), (165, 128, 116), (206, 152, 100), (255, 178, 60),
        (255, 234, 70),
    ),
    "turbo": (
        (48, 18, 59), (65, 69, 171), (52, 130, 222), (30, 184, 210),
        (65, 219, 150), (146, 235, 88), (220, 216, 59), (253, 165, 49),
        (227, 89, 38), (159, 34, 27), (122, 4, 3),
    ),
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
    elif mode == "colormap":
        out = _colormap(ImageOps.grayscale(base), spec)
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


def _colormap(gray: Image.Image, spec) -> Image.Image:
    """Mapea el tono (0 negro, 255 blanco) a un degradado de varios colores,
    en vez de a los dos extremos de un duotono. `stops` gana si viene junto
    con `name`."""
    raw = spec.get("stops")
    if raw is not None:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            raise SpecError("recolor.stops necesita una lista de al menos dos colores")
        puntos = tuple(colors.parse(c) for c in raw)
    else:
        name = str(spec.get("name", "inferno")).lower()
        if name not in COLORMAPS:
            raise SpecError(f"recolor.name debe ser uno de {sorted(COLORMAPS)}, llegó {name!r}")
        puntos = COLORMAPS[name]
    lut_r, lut_g, lut_b = _gradient_luts(puntos)
    r, g, b = (gray.point(lut) for lut in (lut_r, lut_g, lut_b))
    return Image.merge("RGB", (r, g, b))


def _gradient_luts(puntos: tuple[tuple[int, int, int], ...]):
    """Tres tablas de 256 entradas (una por canal), interpolando en línea
    recta entre los colores de control repartidos parejo en 0..255."""
    tramos = len(puntos) - 1
    salida = ([], [], [])
    for i in range(256):
        avance = i / 255 * tramos
        tramo = min(int(avance), tramos - 1)
        resto = avance - tramo
        inicio, fin = puntos[tramo], puntos[tramo + 1]
        for canal in range(3):
            salida[canal].append(round(inicio[canal] + (fin[canal] - inicio[canal]) * resto))
    return salida


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