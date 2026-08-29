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
"""

from __future__ import annotations

from PIL import Image, ImageOps

from ..errors import SpecError

KEYS = {"normalize", "cutoff", "equalize", "gamma", "invert"}


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
    if spec.get("invert", False):
        gray = ImageOps.invert(gray)

    out = gray.convert("RGBA")
    out.putalpha(alpha)
    return out


def _cutoff(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value < 50:
        raise SpecError(f"tones.cutoff debe estar entre 0 y 50, llegó {value!r}")
    return float(value)


def _gamma_lut(value) -> list[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise SpecError(f"tones.gamma debe ser un número positivo, llegó {value!r}")
    return [round(255 * (i / 255) ** (1 / value)) for i in range(256)]