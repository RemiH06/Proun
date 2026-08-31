"""Normalización tonal: lleva cada capa a una escala de luces comparable.

Este es el paso que hace que un collage se vea de una sola paleta. Sin él, una
foto lavada y una de alto contraste aportan escalas de luz distintas y el
resultado parece de siete paletas aunque todo esté teñido del mismo color.

Va antes de `recolor` y es independiente: se puede normalizar sin recolorear
(queda una capa en grises) o recolorear sin normalizar (`tones: false`), y en
ese caso el recoloreado trabaja sobre los tonos originales de la imagen.

Formas aceptadas en `tones`:
    false / null                 no toca la capa, conserva su color
    true / {}                    normalización por defecto
    {"normalize": false}         pasa a grises sin igualar el rango
    {"cutoff": 3}                ignora ese porcentaje de extremos al normalizar
    {"equalize": true}           ecualiza el histograma, mucho más agresivo
    {"gamma": 1.4}               aclara medios tonos (menor que 1 los oscurece)
    {"invert": true}             negativo, útil para tinta sobre fondo claro
    {"dominant": "light"}        lleva el tono más frecuente al blanco puro

`dominant` es la clave que decide si una capa se lee o no. El tono dominante de
una foto casi siempre es su fondo: la pared, el cielo, el papel. Llevarlo al
blanco hace que `transparent` se lo lleve limpio y quede solo el sujeto, igual
que pasa con una radiografía. Con "dark" hace lo contrario, y con "auto" elige
el extremo más cercano, que en la práctica significa invertir las fotos oscuras
para que se lean como masa sólida en vez de como neblina.
"""

from __future__ import annotations

from PIL import Image, ImageOps

from ..errors import SpecError

KEYS = {"normalize", "cutoff", "equalize", "gamma", "invert", "dominant"}

DOMINANTES = ("light", "dark", "auto")


def apply(im: Image.Image, spec=None) -> Image.Image:
    """Devuelve la capa en grises normalizados, conservando el canal alfa."""
    if spec is None or spec is False:
        return im
    if spec is True:
        spec = {}
    if not isinstance(spec, dict):
        raise SpecError(f"tones debe ser un booleano o un objeto, llegó {spec!r}")
    unknown = set(spec) - KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en tones: {sorted(unknown)}")

    alpha = im.getchannel("A")
    gray = ImageOps.grayscale(im.convert("RGB"))

    if spec.get("normalize", True):
        gray = ImageOps.autocontrast(gray, cutoff=_cutoff(spec.get("cutoff", 1)))
    if spec.get("equalize", False):
        gray = ImageOps.equalize(gray)
    if "gamma" in spec:
        gray = gray.point(_gamma_lut(spec["gamma"]))
    if "dominant" in spec:
        gray = _dominant(gray, spec["dominant"])
    if spec.get("invert", False):
        gray = ImageOps.invert(gray)

    out = gray.convert("RGBA")
    out.putalpha(alpha)
    return out


def _dominant(gray: Image.Image, target) -> Image.Image:
    """Lleva el tono más frecuente de la capa al extremo que se pida."""
    objetivo = str(target).lower()
    if objetivo not in DOMINANTES:
        raise SpecError(f"tones.dominant debe ser uno de {DOMINANTES}, llegó {target!r}")

    histograma = gray.histogram()
    # Se ignoran los extremos puros, porque si la imagen ya trae un borde
    # saturado el modo se ancla ahí y el ajuste no hace nada. Pero si fuera de
    # los extremos casi no hay píxeles (una imagen ya bilevel, por ejemplo una
    # radiografía keyeada), esa exclusión daría un modo arbitrario, así que en
    # ese caso se mira el rango completo.
    modo = max(range(4, 252), key=lambda i: histograma[i])
    if histograma[modo] < 0.01 * sum(histograma):
        modo = max(range(256), key=lambda i: histograma[i])
    if objetivo == "auto":
        objetivo = "light" if modo >= 128 else "dark"

    # Si el dominante está del lado contrario al objetivo, se invierte primero:
    # es lo que hace que una foto oscura salga como masa sólida y no como velo.
    if (objetivo == "light") != (modo >= 128):
        gray = ImageOps.invert(gray)
        modo = 255 - modo

    if objetivo == "light":
        if modo >= 254:
            return gray
        return gray.point([min(255, round(i * 255 / modo)) for i in range(256)])
    if modo <= 1:
        return gray
    return gray.point([max(0, round((i - modo) * 255 / (255 - modo))) for i in range(256)])


def _cutoff(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value < 50:
        raise SpecError(f"tones.cutoff debe estar entre 0 y 50, llegó {value!r}")
    return float(value)


def _gamma_lut(value) -> list[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise SpecError(f"tones.gamma debe ser un número positivo, llegó {value!r}")
    return [round(255 * (i / 255) ** (1 / value)) for i in range(256)]