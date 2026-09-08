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

Claves generales, que cada secuencia puede pisar: `times`, `mirror`, `rotate`,
`fade`, `pivot` y `sectors`. `blend` es solo general, porque describe cómo se
apila todo el conjunto.

    times   copias además de la original
    mirror  true espeja las copias impares (es lo que da la simetría de
            mariposa), "all" espeja todas
    rotate  giro acumulado: la copia 2 gira el doble que la 1
    fade    cada copia pierde esa fracción de opacidad
    blend   cómo se funden las copias entre sí, por ejemplo multiply

Caleidoscopio: `pivot` y `sectors` arman una rueda de copias alrededor de un
punto, en vez de una fila que avanza con `step`.

    pivot     punto de giro, proporción de la propia imagen igual que `step`
              ([0, 0] es el centro, que no mueve nada; [0.5, 0] es el borde
              derecho). Sin `pivot`, `rotate` sigue girando cada copia sobre
              su propio centro como siempre.
    sectors   reemplaza a `times`: pide `sectors` copias repartidas en un
              círculo completo (`360 / sectors` grados cada una) en vez de
              decir cuántas y a qué ángulo a mano. No se combina con `times`
              ni con `rotate` en el mismo paso, porque ya fija los dos.

    {"pivot": [0.5, 0], "sectors": 6}    seis copias en abanico desde el
                                         borde derecho de la imagen
"""

from __future__ import annotations

import math

from PIL import Image

from ..errors import SpecError
from .blend import MODES, composite
from .rotate import apply as turn

KEYS = {"step", "steps", "times", "mirror", "rotate", "fade", "blend", "pivot", "sectors"}
STEP_KEYS = {"step", "times", "mirror", "rotate", "fade", "pivot", "sectors"}
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
    if raw is None and "sectors" in spec:
        raw = [{}]  # sectors por sí solo alcanza: no hace falta un step explícito
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

    # `sectors` puede venir del propio paso o, en la forma corta sin `steps`,
    # del nivel general (que ahí es el spec entero). El choque con times/rotate
    # se revisa en el mismo dict de donde salió sectors, no en el otro.
    origen = entrada if "sectors" in entrada else general
    sectors = origen.get("sectors")
    if sectors is not None:
        if "times" in origen:
            raise SpecError("repeat no admite sectors y times juntos en el mismo paso")
        if "rotate" in origen:
            raise SpecError("repeat.sectors ya fija el ángulo de giro, no lo combines con rotate")
        times = _sectors(sectors) - 1
        angle = 360.0 / (times + 1)
    else:
        times = _times(entrada.get("times", general.get("times", 1)))
        angle = _angle(entrada.get("rotate", general.get("rotate", 0)))

    if "step" not in entrada and sectors is None:
        raise SpecError(f"a este paso de repeat le falta 'step': {entrada!r}")
    dx, dy = _step(entrada["step"]) if "step" in entrada else (0.0, 0.0)

    mirror = _mirror(entrada.get("mirror", general.get("mirror", False)))
    fade = _fade(entrada.get("fade", general.get("fade", 0.0)))

    pivot_raw = entrada.get("pivot", general.get("pivot"))
    pivot = None
    if pivot_raw is not None:
        px, py = _pivot(pivot_raw)
        pivot = (px * im.width, py * im.height)

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
        if opacidad <= 0:
            continue
        centro = (dx * i * im.width, dy * i * im.height)
        if pivot is not None:
            # La copia orbita `pivot` en vez de solo correrse en línea recta:
            # se resta el propio pivot ya girado, así la original (que no se
            # mueve) queda fija y las demás abren en abanico a su alrededor.
            giro = _rotar(pivot, angle * i)
            centro = (centro[0] + pivot[0] - giro[0], centro[1] + pivot[1] - giro[1])
        salida.append((pieza, centro, opacidad))
    return salida


def _rotar(punto: tuple[float, float], angulo_grados: float) -> tuple[float, float]:
    """Gira `punto`, medido desde el origen, `angulo_grados` alrededor de él."""
    rad = math.radians(angulo_grados)
    x, y = punto
    coseno, seno = math.cos(rad), math.sin(rad)
    return (x * coseno - y * seno, x * seno + y * coseno)


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


def _sectors(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 2 <= value <= MAX_COPIES + 1:
        raise SpecError(
            f"repeat.sectors debe ser un entero entre 2 y {MAX_COPIES + 1}, llegó {value!r}"
        )
    return value


def _pivot(value) -> tuple[float, float]:
    if not _is_pair(value):
        raise SpecError(f"repeat.pivot debe ser [x, y] con dos números, llegó {value!r}")
    for v in value:
        if abs(v) > 20:
            raise SpecError(f"repeat.pivot es proporción de la imagen, {v} es absurdo")
    return (float(value[0]), float(value[1]))


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