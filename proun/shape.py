"""Figuras geométricas generadas, no cargadas de una imagen.

No hornean color: salen en escala de grises (relleno blanco puro, contorno en
un gris intermedio) y de ahí en más pasan por el mismo `recolor` que las
fotos. Es lo que las hace reutilizables entre los colores de un lote sin
escribir nada nuevo, y lo que hace que el contorno salga solo en una sombra
del mismo color sin necesitar un "color de contorno" aparte: `recolor.duotone`
mapea el blanco a la luz y el gris del contorno a un tono intermedio.

Formas aceptadas en `shape`:
    "circle"                     un tipo entre rect, circle, triangle, diamond
    {"kind": "polygon", "sides": 6}   polígono regular de n lados (3 a 12)

Contorno, en `outline`, opcional:
    {"inset": 0.12, "width": 0.03}
`inset` y `width` son fracción del tamaño de la figura, no del lienzo. El
contorno no vive en el borde real: se traza sobre una copia de la silueta
encogida hacia el centro por `inset`, así que queda un poco hacia adentro.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

from ..errors import SpecError
from ..geometry import measure

KINDS = ("rect", "circle", "triangle", "diamond", "polygon")

BASE = 512  # tamaño nominal de referencia para inset/width, antes de resize
SUPERSAMPLE = 4

FILL = 255
CONTORNO = 90


def build(shape, outline=None) -> Image.Image:
    """Genera la figura en escala de grises, lista para `recolor`."""
    kind, sides = _parse_kind(shape)
    inset, width = _parse_outline(outline)

    lado = BASE * SUPERSAMPLE
    im = Image.new("L", (lado, lado), 0)
    draw = ImageDraw.Draw(im)

    puntos = _vertices(kind, sides, lado)
    if kind == "circle":
        margen = round(lado * 0.02)
        draw.ellipse([margen, margen, lado - margen, lado - margen], fill=FILL)
    else:
        draw.polygon(puntos, fill=FILL)

    if width > 0:
        centro = _centroid(puntos) if kind != "circle" else (lado / 2, lado / 2)
        factor = 1 - inset
        ancho_px = round(width * lado)
        if kind == "circle":
            radio = (lado / 2 - round(lado * 0.02)) * factor
            caja = [centro[0] - radio, centro[1] - radio, centro[0] + radio, centro[1] + radio]
            draw.ellipse(caja, outline=CONTORNO, width=max(1, ancho_px))
        else:
            interior = [
                (centro[0] + (x - centro[0]) * factor, centro[1] + (y - centro[1]) * factor)
                for x, y in puntos
            ]
            _stroke_polygon(draw, interior, max(1, ancho_px), CONTORNO)

    pequeno = im.resize((BASE, BASE), Image.Resampling.LANCZOS)
    return _componer(pequeno)


def _componer(mascara: Image.Image) -> Image.Image:
    """Convierte la máscara de trabajo (0 fuera, 255 relleno, 90 contorno) a RGBA.

    El alfa sale de "hay algo dibujado o no"; los tonos de gris (255 relleno,
    90 contorno) quedan en los tres canales de color, listos para que
    `recolor.duotone` los lea como si fueran una foto ya normalizada.
    """
    alfa = mascara.point(lambda v: 255 if v > 0 else 0)
    salida = Image.merge("RGBA", (mascara, mascara, mascara, alfa))
    return salida


def _vertices(kind: str, sides: int, lado: int) -> list[tuple[float, float]]:
    cx = cy = lado / 2
    if kind == "rect":
        m = lado * 0.02
        return [(m, m), (lado - m, m), (lado - m, lado - m), (m, lado - m)]
    if kind == "diamond":
        r = lado / 2 * 0.98
        return [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if kind == "triangle":
        r = lado / 2 * 0.98
        return [_point(cx, cy, r, -90), _point(cx, cy, r, 30), _point(cx, cy, r, 150)]
    if kind == "polygon":
        r = lado / 2 * 0.98
        paso = 360 / sides
        return [_point(cx, cy, r, -90 + paso * i) for i in range(sides)]
    return []


def _point(cx, cy, r, grados):
    rad = math.radians(grados)
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def _centroid(puntos):
    n = len(puntos)
    return (sum(p[0] for p in puntos) / n, sum(p[1] for p in puntos) / n)


def _stroke_polygon(draw, puntos, width, color):
    """Traza el contorno de un polígono, con las esquinas rellenas para que
    no queden huecos donde ImageDraw.line no las une bien."""
    n = len(puntos)
    for i in range(n):
        draw.line([puntos[i], puntos[(i + 1) % n]], fill=color, width=width)
    r = width / 2
    for x, y in puntos:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _parse_kind(shape):
    if isinstance(shape, str):
        shape = {"kind": shape}
    if not isinstance(shape, dict):
        raise SpecError(f"shape debe ser un texto o un objeto, llegó {shape!r}")
    kind = str(shape.get("kind", "")).lower()
    if kind not in KINDS:
        raise SpecError(f"shape.kind debe ser uno de {KINDS}, llegó {kind!r}")
    sides = shape.get("sides", 6)
    if kind == "polygon":
        if isinstance(sides, bool) or not isinstance(sides, int) or not 3 <= sides <= 12:
            raise SpecError(f"shape.sides debe ser un entero entre 3 y 12, llegó {sides!r}")
    return kind, sides


def _parse_outline(outline):
    if not outline:
        return (0.12, 0.0)
    if not isinstance(outline, dict):
        raise SpecError(f"outline debe ser un objeto, llegó {outline!r}")
    unknown = set(outline) - {"inset", "width"}
    if unknown:
        raise SpecError(f"claves desconocidas en outline: {sorted(unknown)}")
    inset = outline.get("inset", 0.12)
    if isinstance(inset, bool) or not isinstance(inset, (int, float)) or not 0 <= inset < 0.5:
        raise SpecError(f"outline.inset debe estar entre 0 y 0.5, llegó {inset!r}")
    width = outline.get("width", 0.03)
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not 0 <= width <= 0.3:
        raise SpecError(f"outline.width debe estar entre 0 y 0.3, llegó {width!r}")
    return (float(inset), float(width))