"""Texto generado, igual que las figuras: sale en escala de grises listo para
`recolor`, y entra a `sources` con `"text"` en vez de `"src"` o `"shape"`.

La fuente por defecto viene empaquetada con Proun (Big Shoulders, licencia
OFL, en `proun/assets/fonts/`), así que funciona igual en Windows, macOS y
Linux sin depender de qué fuentes tenga instaladas el sistema. Se puede pedir
otra con `font`, dando una ruta a un `.ttf` propio.

Formas aceptadas en `text`:
    "PROUN"                       una sola línea, con los valores por defecto
    ["PROUN", "1926", "LISSITZKY"]  se sortea una por wallpaper, como `color`
    {"text": "PROUN", "weight": "bold", "align": "center", "wrap": 0.8,
     "line_spacing": 1.15, "outline": {"width": 0.04}}

`wrap` es la fracción del ancho de línea de trabajo antes de saltar de
renglón; sin ella, el texto sale en una sola línea sin importar qué tan larga
quede. El contorno de texto se traza en el borde real del glifo (vía el
trazo nativo de Pillow), a diferencia del contorno de las figuras, que vive
hacia adentro: un glifo no es convexo y encogerlo de forma confiable pediría
morfología de imagen, que no vale la pena para este caso.

La fuente empaquetada cubre acentos, diéresis, ñ y los signos de apertura del
español. No hay verificación de que una fuente propia cubra un alfabeto no
latino: si faltan glifos, Pillow los dibuja como un cuadro vacío en silencio.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..errors import SpecError

FILL = 255
CONTORNO = 90
SUPERSAMPLE = 4
WORKING_SIZE = 200  # alto de línea de trabajo en px, antes de recortar al bbox real

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
DEFAULT_FONTS = {
    "regular": FONTS_DIR / "BigShoulders-Regular.ttf",
    "bold": FONTS_DIR / "BigShoulders-Bold.ttf",
}

ALIGNS = ("left", "center", "right")
KEYS = {"text", "font", "weight", "align", "wrap", "line_spacing", "outline"}


def build(spec) -> Image.Image:
    """Genera el texto en escala de grises, con relleno blanco y el contorno
    (si se pide) en un gris intermedio, listo para que `recolor` lo lea igual
    que a una figura."""
    if isinstance(spec, str):
        spec = {"text": spec}
    if not isinstance(spec, dict):
        raise SpecError(f"text debe ser un texto o un objeto, llegó {spec!r}")
    unknown = set(spec) - KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en text: {sorted(unknown)}")
    if "text" not in spec or not str(spec["text"]).strip():
        raise SpecError("text necesita una cadena no vacía")

    texto = str(spec["text"])
    ruta = _font_path(spec)
    align = str(spec.get("align", "left")).lower()
    if align not in ALIGNS:
        raise SpecError(f"text.align debe ser uno de {ALIGNS}, llegó {align!r}")
    espaciado = _positive(spec.get("line_spacing", 1.15), "text.line_spacing")
    stroke_fraction = _stroke_fraction(spec.get("outline"))

    tamano_normal = WORKING_SIZE * SUPERSAMPLE
    font = _load_font(ruta, tamano_normal)
    lado = tamano_normal
    lineas = _wrap(texto, font, spec.get("wrap"), lado) if "wrap" in spec else [texto]

    im = _rasterize(ruta, lineas, align, espaciado, stroke_fraction, tamano_normal)

    pequeno = im.resize((max(1, im.width // SUPERSAMPLE), max(1, im.height // SUPERSAMPLE)),
                        Image.Resampling.LANCZOS)
    alfa = pequeno.point(lambda v: 255 if v > 0 else 0)
    return Image.merge("RGBA", (pequeno, pequeno, pequeno, alfa))


def _rasterize(ruta, lineas, align, espaciado, stroke_fraction, tamano) -> Image.Image:
    """Dibuja `lineas` al tamaño de trabajo normal y, si FreeType revienta con
    "raster overflow", reintenta con una fuente más chica y agranda el
    resultado al tamaño que hubiera tenido.

    Es un bug real del rasterizador con ciertas formas de glifo a tamaños de
    fuente grandes (reproducido con "marzo 2027" en Big Shoulders Bold a
    800px, no con "enero 2027" al mismo tamaño), no algo que dependa de la
    especificación: no hay forma de saber de antemano qué combinación de
    letras lo va a disparar, así que hay que poder recuperarse en caliente.
    """
    intento = tamano
    while True:
        font = _load_font(ruta, intento)
        try:
            im = _draw(font, lineas, align, espaciado, round(stroke_fraction * intento))
        except OSError:
            intento //= 2
            if intento < 50:
                raise
            continue
        if intento != tamano:
            factor = tamano / intento
            im = im.resize(
                (max(1, round(im.width * factor)), max(1, round(im.height * factor))),
                Image.Resampling.LANCZOS,
            )
        return im


def _draw(font, lineas, align, espaciado, ancho_stroke) -> Image.Image:
    alto_linea = round((font.getbbox("Ay")[3] - font.getbbox("Ay")[1]) * espaciado)
    cajas = [font.getbbox(linea, stroke_width=ancho_stroke) for linea in lineas]
    ancho_total = max((c[2] - c[0] for c in cajas), default=1)
    alto_total = alto_linea * len(lineas)

    im = Image.new("L", (max(1, ancho_total), max(1, alto_total)), 0)
    draw = ImageDraw.Draw(im)
    for i, (linea, caja) in enumerate(zip(lineas, cajas)):
        ancho_linea = caja[2] - caja[0]
        if align == "left":
            x = -caja[0]
        elif align == "right":
            x = ancho_total - ancho_linea - caja[0]
        else:
            x = (ancho_total - ancho_linea) / 2 - caja[0]
        y = i * alto_linea
        if ancho_stroke > 0:
            draw.text((x, y), linea, font=font, fill=FILL,
                      stroke_width=ancho_stroke, stroke_fill=CONTORNO)
        else:
            draw.text((x, y), linea, font=font, fill=FILL)
    return im


def _font_path(spec) -> Path:
    if "font" in spec:
        ruta = Path(str(spec["font"])).expanduser()
        if not ruta.is_file():
            raise SpecError(f"no existe la fuente: {spec['font']}")
        return ruta
    weight = str(spec.get("weight", "bold")).lower()
    if weight not in DEFAULT_FONTS:
        raise SpecError(f"text.weight debe ser uno de {sorted(DEFAULT_FONTS)}, llegó {weight!r}")
    return DEFAULT_FONTS[weight]


def _load_font(ruta: Path, tamano: int) -> "ImageFont.FreeTypeFont":
    try:
        return ImageFont.truetype(str(ruta), tamano)
    except OSError as exc:
        raise SpecError(f"no se pudo abrir la fuente {ruta}: {exc}") from exc


def _wrap(texto: str, font, wrap, ancho_lienzo: int) -> list[str]:
    if wrap is None:
        return [texto]
    if isinstance(wrap, bool) or not isinstance(wrap, (int, float)) or not 0 < wrap <= 1:
        raise SpecError(f"text.wrap debe estar entre 0 y 1, llegó {wrap!r}")
    limite = wrap * ancho_lienzo
    palabras = texto.split()
    if not palabras:
        return [texto]
    lineas, actual = [], palabras[0]
    for palabra in palabras[1:]:
        candidata = f"{actual} {palabra}"
        caja = font.getbbox(candidata)
        if caja[2] - caja[0] <= limite:
            actual = candidata
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def _stroke_fraction(outline) -> float:
    if not outline:
        return 0.0
    if not isinstance(outline, dict):
        raise SpecError(f"outline debe ser un objeto, llegó {outline!r}")
    unknown = set(outline) - {"width"}
    if unknown:
        raise SpecError(f"claves desconocidas en outline: {sorted(unknown)}")
    width = outline.get("width", 0.03)
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not 0 <= width <= 0.3:
        raise SpecError(f"outline.width debe estar entre 0 y 0.3, llegó {width!r}")
    return float(width)


def _positive(value, name) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise SpecError(f"{name} debe ser un número positivo, llegó {value!r}")
    return float(value)