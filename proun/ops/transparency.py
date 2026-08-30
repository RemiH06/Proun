"""Transparencia por color: hace que un color de la capa desaparezca.

Cualquier color puede ser el que se vuelve transparente, y con eso se elige la
polaridad de la capa. Si desaparece el extremo claro, lo oscuro se acumula como
tinta sobre papel; si desaparece el oscuro, al revés.

La transparencia no es un corte: cuanto más se parece un pixel al color
elegido, más transparente queda. Con `tolerance` en 0 y `softness` en 1 el
resultado es un degradado limpio (la clásica matriz de tinta), y con tolerancia
alta y suavidad baja es un recorte duro tipo croma.

Formas aceptadas en `transparent`:
    "#ffffff"                        blanco fuera, con los valores por defecto
    "light" / "dark"                 atajos de blanco y negro
    {"color": "light", "tolerance": 0, "softness": 1}    matriz de tinta
    {"color": "#00ff00", "tolerance": 0.6, "softness": 0.05}   croma duro
    {"color": "light", "invert": true}    conserva solo lo que se parece al color

Va después de `tones`, así que si la capa está normalizada, "light" y "dark" se
refieren a los extremos de esa capa y no a lo que traía la foto original.
"""

from __future__ import annotations

from PIL import Image, ImageChops

from .. import colors
from ..errors import SpecError

KEYS = {"color", "tolerance", "softness", "invert"}

ALIASES = {"light": "#ffffff", "dark": "#000000", "white": "#ffffff", "black": "#000000"}


def apply(im: Image.Image, spec) -> Image.Image:
    if spec is None or spec is False:
        return im
    if isinstance(spec, (str, list, tuple)):
        spec = {"color": spec}
    if not isinstance(spec, dict):
        raise SpecError(f"transparent debe ser un color o un objeto, llegó {spec!r}")
    unknown = set(spec) - KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en transparent: {sorted(unknown)}")
    if "color" not in spec:
        raise SpecError("transparent necesita el color que debe desaparecer")

    fuera = colors.parse(ALIASES.get(str(spec["color"]).strip().lower(), spec["color"]))
    tolerance = _unit(spec.get("tolerance", 0.1), "transparent.tolerance")
    softness = _unit(spec.get("softness", 0.3), "transparent.softness")

    distancia = _distance(im, fuera)
    mascara = distancia.point(_ramp(tolerance, softness))
    if spec.get("invert", False):
        mascara = ImageChops.invert(mascara)

    out = im.copy()
    out.putalpha(ImageChops.multiply(im.getchannel("A"), mascara))
    return out


def _distance(im: Image.Image, color) -> Image.Image:
    """Qué tan lejos está cada pixel del color, canal por canal y quedándose
    con el mayor. Es la distancia de croma de toda la vida y sale de dos
    operaciones de Pillow, sin recorrer píxeles en Python."""
    diferencia = ImageChops.difference(
        im.convert("RGB"), Image.new("RGB", im.size, tuple(color))
    )
    r, g, b = diferencia.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b)


def _ramp(tolerance: float, softness: float) -> list[int]:
    """0 donde el pixel se parece al color, 255 donde ya no."""
    corte = tolerance * 255
    ancho = softness * 255
    if ancho <= 0:
        return [0 if i <= corte else 255 for i in range(256)]
    return [min(255, max(0, round((i - corte) * 255 / ancho))) for i in range(256)]


def _unit(value, name) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise SpecError(f"{name} debe estar entre 0 y 1, llegó {value!r}")
    return float(value)