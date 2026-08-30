"""Repetición: la imagen se estampa varias veces solapándose consigo misma.

Distinto de `mosaic`, que llena un área con piezas pegadas borde con borde.
Aquí el paso entre copia y copia se expresa como proporción de la propia
imagen, así que funciona igual con una pieza de 300 px que con una de 4000:

    1     la copia arranca justo donde termina la anterior, sin solaparse
    0.5   la corre media imagen, así que se solapan a la mitad
    -0.33 la corre un tercio de imagen en dirección contraria

Formas aceptadas en `repeat`:
    [0.5, 0]                                una secuencia hacia la derecha
    {"step": [0, 0.4], "times": 3}          tres copias hacia abajo
    {"steps": [[0.5, 0], [0, 0.5]]}         una cruz: cada paso arranca su
                                            propia secuencia desde la original
    {"steps": [{"step": [0.3, 0], "rotate": 90, "times": 3}]}

Claves generales, que cada secuencia puede pisar: `times`, `mirror`, `rotate`
y `fade`. `blend` es solo general, porque describe cómo se apila todo el
conjunto.

    times   copias además de la original
    mirror  true espeja las copias impares (es lo que da la simetría de
            mariposa), "all" espeja todas
    rotate  giro acumulado: la copia 2 gira el doble que la 1
    fade    cada copia pierde esa fracción de opacidad
    blend   cómo se funden las copias entre sí, por ejemplo multiply
"""

from __future__ import annotations

from PIL import Image

from ..errors import SpecError
from .blend import MODES, composite
from .rotate import apply as turn

KEYS = {"step", "steps", "times", "mirror", "rotate", "fade", "blend"}
STEP_KEYS = {"step", "times", "mirror", "rotate", "fade"}
MIRRORS = ("none", "alternate", "all")

MAX_COPIES = 200
MAX_PIXELS = 80_000_000


def apply(im: Image.Image, spec, canvas=None) -> Image.Image:
    if spec is None or spec is False:
        return im
    spec = _as_dict(spec)

    unknown = set(spec) - KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en repeat: {sorted(unknown)}")
    if "step" in spec and "steps" in spec:
        raise SpecError("repeat admite step o steps, no los dos")

    raw = spec.get("steps", [spec["step"]] if "step" in spec else None)
    if raw is None:
        raise SpecError("repeat necesita step o steps")
    if _is_pair(raw):
        raw = [raw]
    if not isinstance(raw, (list, tuple)) or not raw:
        raise SpecError(f"repeat.steps debe ser un par o una lista de pasos, llegó {raw!r}")

    blend_mode = str(spec.get("blend", "normal")).lower()
    if blend_mode not in MODES:
        raise SpecError(f"repeat.blend debe ser uno de {sorted(MODES)}, llegó {blend_mode!r}")

    piezas = [(im, (0.0, 0.0), 1.0)]
    for entrada in raw:
        piezas += _sequence(im, entrada, spec)
    if len(piezas) - 1 > MAX_COPIES:
        raise SpecError(f"repeat pediría {len(piezas) - 1} copias, el tope es {MAX_COPIES}")

    return _assemble(piezas, blend_mode)


def _sequence(im: Image.Image, entrada, general) -> list:
    """Las copias que genera un paso, con su desplazamiento y su opacidad."""
    if _is_pair(entrada):
        entrada = {"step": list(entrada)}
    if not isinstance(entrada, dict):
        raise SpecError(f"cada paso debe ser un par o un objeto, llegó {entrada!r}")
    unknown = set(entrada) - STEP_KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en un paso de repeat: {sorted(unknown)}")
    if "step" not in entrada:
        raise SpecError(f"a este paso de repeat le falta 'step': {entrada!r}")

    dx, dy = _step(entrada["step"])
    times = _times(entrada.get("times", general.get("times", 1)))
    mirror = _mirror(entrada.get("mirror", general.get("mirror", False)))
    angle = _angle(entrada.get("rotate", general.get("rotate", 0)))
    fade = _fade(entrada.get("fade", general.get("fade", 0.0)))

    # El espejo se aplica sobre los ejes en los que hay avance: así la copia
    # se refleja contra su vecina y las dos se leen como una sola figura.
    flip = "both" if (dx, dy) == (0.0, 0.0) else (
        "both" if dx and dy else ("horizontal" if dx else "vertical")
    )

    salida = []
    for i in range(1, times + 1):
        pieza = im
        if mirror == "all" or (mirror == "alternate" and i % 2):
            pieza = turn(pieza, 0, flip)
        if angle:
            pieza = turn(pieza, angle * i)
        opacidad = max(0.0, 1.0 - fade * i)
        if opacidad > 0:
            salida.append((pieza, (dx * i * im.width, dy * i * im.height), opacidad))
    return salida


def _assemble(piezas, blend_mode: str) -> Image.Image:
    """Arma el lienzo mínimo que contiene todas las copias y las compone.

    Los desplazamientos se miden entre centros, no entre esquinas: así una
    copia girada sigue cayendo donde debe aunque haya cambiado de tamaño.
    """
    cajas = [
        (
            centro[0] - pieza.width / 2,
            centro[1] - pieza.height / 2,
            centro[0] + pieza.width / 2,
            centro[1] + pieza.height / 2,
        )
        for pieza, centro, _ in piezas
    ]
    izquierda = min(c[0] for c in cajas)
    arriba = min(c[1] for c in cajas)
    ancho = max(1, round(max(c[2] for c in cajas) - izquierda))
    alto = max(1, round(max(c[3] for c in cajas) - arriba))
    if ancho * alto > MAX_PIXELS:
        raise SpecError(
            f"repeat daría una capa de {ancho}x{alto}: revisa el paso o la cantidad de copias"
        )

    lienzo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    for (pieza, centro, opacidad), caja in zip(piezas, cajas):
        composite(lienzo, pieza, (round(caja[0] - izquierda), round(caja[1] - arriba)),
                  mode=blend_mode, opacity=opacidad)
    return lienzo


def _as_dict(spec) -> dict:
    if _is_pair(spec):
        return {"step": list(spec)}
    if isinstance(spec, (list, tuple)):
        return {"steps": list(spec)}
    if not isinstance(spec, dict):
        raise SpecError(f"repeat debe ser un par, una lista o un objeto, llegó {spec!r}")
    return spec


def _is_pair(value) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
    )


def _step(value) -> tuple[float, float]:
    if not _is_pair(value):
        raise SpecError(f"repeat.step debe ser [x, y] con dos números, llegó {value!r}")
    for v in value:
        if abs(v) > 20:
            raise SpecError(f"repeat.step es proporción de la imagen, {v} es absurdo")
    return (float(value[0]), float(value[1]))


def _times(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_COPIES:
        raise SpecError(f"repeat.times debe ser un entero entre 0 y {MAX_COPIES}, llegó {value!r}")
    return value


def _mirror(value) -> str:
    if value is True:
        return "alternate"
    if value is False or value is None:
        return "none"
    texto = str(value).lower()
    if texto not in MIRRORS:
        raise SpecError(f"repeat.mirror debe ser booleano o uno de {MIRRORS}, llegó {value!r}")
    return texto


def _angle(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpecError(f"repeat.rotate debe ser un número, llegó {value!r}")
    return float(value)


def _fade(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise SpecError(f"repeat.fade debe estar entre 0 y 1, llegó {value!r}")
    return float(value)