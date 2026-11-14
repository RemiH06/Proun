"""Figuras isométricas de cubos, incluidas las imposibles (Penrose).

No son 3D de verdad: es un pintor de cubos en proyección isométrica. Cada
cubo tiene tres caras visibles y cada cara sale en un gris fijo, igual que
las demás figuras de `shapes`: arriba 255, izquierda 128, derecha 0. Así el
`recolor` de siempre decide los colores. Con `duotone` las tres caras caen
justo en sus tres anclas (luz, color principal, sombra), y con un colormap
de tres colores en `stops` (orden: derecha, izquierda, arriba) cada cara
toma uno.

Formas aceptadas en `shape`:
    {"kind": "iso", "figure": "penrose", "size": 5}
    {"kind": "iso", "voxels": [[0, 0, 0], [1, 0, 0], [1, 0, 1]]}

`figure` es una de FIGURAS y `size` el largo de sus brazos (cada figura
tiene su mínimo). `voxels` es una lista propia de cubos [x, y, z]; un cuarto
valor opcional `t` adelanta ese cubo en el orden de pintado, ver
`_profundidad`. Es lo que hace posibles las figuras imposibles.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageMath

from ..errors import SpecError

BASE = 512
SUPERSAMPLE = 4

ARRIBA, IZQUIERDA, DERECHA = 255, 128, 0

# Mínimo, valor por defecto y máximo de `size` para cada figura. El cubo no
# tiene brazos: uno más grande se vería igual, así que no admite otro tamaño.
FIGURAS = {
    "cubo": (1, 1, 1),
    "escalera": (2, 4, 8),
    "cruz": (1, 2, 8),
    "marco": (3, 4, 8),
    "penrose": (4, 5, 10),
}
MAX_VOXELS = 4096

_COS30 = math.cos(math.radians(30))

# Las tres caras visibles: dirección del vecino que la taparía, tono y sus
# cuatro esquinas relativas al cubo (en unidades de cubo).
_CARAS = (
    ((0, 0, 1), ARRIBA, ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
    ((0, 1, 0), IZQUIERDA, ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1))),
    ((1, 0, 0), DERECHA, ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
)


def build(shape: dict) -> Image.Image:
    """Genera la figura en escala de grises, lista para `recolor`, recortada
    a su contenido y con el lado mayor en BASE píxeles."""
    voxels = _voxels(shape)
    ocupados = {v[:3] for v in voxels} | {_desplazado(v) for v in voxels}

    caras = []
    for v in sorted(voxels, key=_profundidad):
        for vecino, tono, esquinas in _CARAS:
            if _tapada(v, vecino, ocupados):
                continue
            puntos = [_proyectar(v[0] + dx, v[1] + dy, v[2] + dz) for dx, dy, dz in esquinas]
            caras.append((puntos, tono))

    todos = [p for puntos, _ in caras for p in puntos]
    izquierda, arriba = min(x for x, _ in todos), min(y for _, y in todos)
    ancho, alto = max(x for x, _ in todos) - izquierda, max(y for _, y in todos) - arriba
    escala = BASE * SUPERSAMPLE / max(ancho, alto)
    tamano = (max(1, round(ancho * escala)), max(1, round(alto * escala)))

    gris = Image.new("L", tamano, 0)
    alfa = Image.new("L", tamano, 0)
    pinta_gris, pinta_alfa = ImageDraw.Draw(gris), ImageDraw.Draw(alfa)
    for puntos, tono in caras:
        poligono = [((x - izquierda) * escala, (y - arriba) * escala) for x, y in puntos]
        pinta_gris.polygon(poligono, fill=tono)
        pinta_alfa.polygon(poligono, fill=255)

    final = (max(1, round(tamano[0] / SUPERSAMPLE)), max(1, round(tamano[1] / SUPERSAMPLE)))
    gris = gris.resize(final, Image.Resampling.LANCZOS)
    alfa = alfa.resize(final, Image.Resampling.LANCZOS)
    # Al achicar, el borde mezcla el gris de la cara con el fondo vacío (0) y
    # quedaría un halo oscuro. Dividir entre el alfa devuelve el tono real.
    gris = ImageMath.lambda_eval(
        lambda a: a["min"](a["g"] * 255.0 / a["a"] + 0.5, 255.0),
        g=gris.convert("F"), a=alfa.convert("F"),
    ).convert("L")
    return Image.merge("RGBA", (gris, gris, gris, alfa))


def _proyectar(x, y, z) -> tuple[float, float]:
    """Isométrica estándar: +x baja a la derecha, +y baja a la izquierda,
    +z sube. Mover un punto por (1, 1, 1) no cambia su proyección, y de eso
    viven las figuras imposibles."""
    return ((x - y) * _COS30, (x + y) * 0.5 - z)


def _desplazado(v) -> tuple[int, int, int]:
    x, y, z, t = v
    return (x - t, y - t, z - t)


def _profundidad(v) -> int:
    """Orden de pintado, del fondo al frente. Un `t` positivo pinta el cubo
    como si estuviera en (x - t, y - t, z - t): mismo lugar en pantalla,
    pero más atrás, así lo que esté cerca lo tapa aunque en 3D estaría
    delante."""
    x, y, z = _desplazado(v)
    return x + y + z


def _tapada(v, vecino, ocupados) -> bool:
    """Una cara tocada por otro cubo no se dibuja, ni en su posición real ni
    en la desplazada. Sin esto, partir un brazo en dos órdenes de pintado
    dejaría una costura donde se juntan."""
    dx, dy, dz = vecino
    real = (v[0] + dx, v[1] + dy, v[2] + dz)
    x, y, z = _desplazado(v)
    return real in ocupados or (x + dx, y + dy, z + dz) in ocupados


def _voxels(shape: dict) -> list[tuple[int, int, int, int]]:
    unknown = set(shape) - {"kind", "figure", "size", "voxels"}
    if unknown:
        raise SpecError(f"claves desconocidas en una figura iso: {sorted(unknown)}")
    if "voxels" in shape:
        if "figure" in shape or "size" in shape:
            raise SpecError("una figura iso lleva 'figure' (con 'size' opcional) o 'voxels', no ambos")
        return _voxels_propios(shape["voxels"])

    figura = str(shape.get("figure", "cubo")).lower()
    if figura not in FIGURAS:
        raise SpecError(f"shape.figure debe ser una de {tuple(FIGURAS)}, llegó {figura!r}")
    minimo, defecto, maximo = FIGURAS[figura]
    n = shape.get("size", defecto)
    if isinstance(n, bool) or not isinstance(n, int) or not minimo <= n <= maximo:
        raise SpecError(
            f"shape.size de {figura!r} debe ser un entero entre {minimo} y {maximo}, llegó {n!r}"
        )
    return [(x, y, z, t) for x, y, z, t in _FABRICAS[figura](n)]


def _voxels_propios(raw) -> list[tuple[int, int, int, int]]:
    if not isinstance(raw, (list, tuple)) or not raw:
        raise SpecError("shape.voxels debe ser una lista no vacía de cubos [x, y, z]")
    if len(raw) > MAX_VOXELS:
        raise SpecError(f"shape.voxels admite hasta {MAX_VOXELS} cubos, llegaron {len(raw)}")
    salida = []
    for cubo in raw:
        if (not isinstance(cubo, (list, tuple)) or len(cubo) not in (3, 4)
                or any(isinstance(c, bool) or not isinstance(c, int) for c in cubo)):
            raise SpecError(f"cada cubo de shape.voxels es [x, y, z] o [x, y, z, t] enteros, llegó {cubo!r}")
        salida.append(tuple(cubo) if len(cubo) == 4 else (*cubo, 0))
    if len({v[:3] for v in salida}) != len(salida):
        raise SpecError("shape.voxels repite un cubo en la misma posición")
    return salida


def _cubo(n):
    return [(0, 0, 0, 0)]


def _escalera(n):
    """n escalones de dos cubos de fondo, subiendo hacia +x."""
    return [(i, j, k, 0) for i in range(n) for j in range(2) for k in range(i + 1)]


def _cruz(n):
    """Un cubo al centro y seis brazos de largo n, uno por cada sentido."""
    cubos = {(0, 0, 0)}
    for eje in range(3):
        for signo in (1, -1):
            for paso in range(1, n + 1):
                p = [0, 0, 0]
                p[eje] = signo * paso
                cubos.add(tuple(p))
    return [(*c, 0) for c in cubos]


def _marco(n):
    """Las doce aristas de un cubo de lado n: un cubo hueco con ventanas."""
    borde = {0, n - 1}
    return [
        (x, y, z, 0)
        for x in range(n) for y in range(n) for z in range(n)
        if (x in borde) + (y in borde) + (z in borde) >= 2
    ]


def _penrose(n):
    """Triángulo de Penrose de brazos de n cubos.

    Brazo A sobre +x, B sobre +y y C sube por +z. La punta de C, (n, n, n),
    cae en pantalla sobre el inicio de A, (0, 0, 0), porque difieren por
    n * (1, 1, 1). La mitad superior de C se pinta antes que todo (t = n),
    así A le pasa por delante arriba mientras C le pasa por delante a B
    abajo: cada esquina se ve bien por separado y el conjunto es imposible.
    El corte necesita al menos dos cubos de cada lado, de ahí el mínimo de 4.
    """
    corte = n // 2
    return (
        [(i, 0, 0, 0) for i in range(n)]
        + [(n, j, 0, 0) for j in range(n)]
        + [(n, n, k, 0 if k < corte else n) for k in range(n)]
    )


_FABRICAS = {
    "cubo": _cubo,
    "escalera": _escalera,
    "cruz": _cruz,
    "marco": _marco,
    "penrose": _penrose,
}
