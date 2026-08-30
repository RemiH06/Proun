"""Manchas: come el canal alfa de la capa con ruido de nubes.

Es lo que hace que una pieza se vea con humedad, desgastada o comida por los
bordes, como papel viejo. En papel eso se llama foxing, en impresión se le dice
grunge o distress; aquí se llama `stain`.

No pinta nada: solo modula la transparencia que la capa ya tenía, así que lo que
se ve por debajo es el fondo o las otras capas.

Formas aceptadas en `stain`:
    0.4                          desgaste parejo con los valores por defecto
    {"amount": 0.6}              qué tanto alfa puede comerse
    {"scale": 0.5}               tamaño de las manchas, en fracción del lado mayor
    {"octaves": 4}               capas de detalle: más octavas, más borde sucio
    {"threshold": 0.45}          corta duro y da manchas con contorno definido
    {"edges": 0.8}               concentra el desgaste en el borde de la pieza
    {"invert": true}             da vuelta la mancha entera: se come lo que
                                 conservaría y conserva lo que se comería, así
                                 que junto a "edges" mancha el centro

El ruido sale del generador que se reciba, así que la misma semilla da la misma
mancha. Sin generador falla, porque una mancha irrepetible rompería la promesa
de que el nombre del archivo permite regenerar el wallpaper.
"""

from __future__ import annotations

from PIL import Image, ImageChops

from ..errors import SpecError

KEYS = {"amount", "scale", "octaves", "threshold", "edges", "invert"}

MAX_OCTAVES = 6


def apply(im: Image.Image, spec, rng=None) -> Image.Image:
    if spec is None or spec is False:
        return im
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        spec = {"amount": spec}
    if not isinstance(spec, dict):
        raise SpecError(f"stain debe ser un número o un objeto, llegó {spec!r}")
    unknown = set(spec) - KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en stain: {sorted(unknown)}")

    amount = _unit(spec.get("amount", 0.5), "stain.amount")
    if amount == 0:
        return im
    if rng is None:
        raise SpecError(
            "stain necesita un generador aleatorio para ser reproducible; "
            "pásale un random.Random con la semilla del wallpaper"
        )

    scale = _positive(spec.get("scale", 0.35), "stain.scale", top=4)
    octaves = spec.get("octaves", 3)
    if isinstance(octaves, bool) or not isinstance(octaves, int) or not 1 <= octaves <= MAX_OCTAVES:
        raise SpecError(f"stain.octaves debe ser un entero entre 1 y {MAX_OCTAVES}")
    threshold = _unit(spec.get("threshold", 0.0), "stain.threshold")
    edges = _unit(spec.get("edges", 0.0), "stain.edges")

    mancha = _clouds(im.size, scale, octaves, rng)
    if threshold:
        mancha = mancha.point(_knee(threshold))
    if edges:
        mancha = ImageChops.multiply(mancha, _border(im.size, edges))
    if spec.get("invert", False):
        # Va al final y no sobre el ruido: invertir solo las nubes dejaba el
        # sesgo de bordes intacto, así que "manchar el centro" no funcionaba.
        mancha = ImageChops.invert(mancha)

    # La mancha dice cuánto se conserva: 255 intacto, 0 comido del todo.
    conserva = mancha.point([round(255 - amount * (255 - i)) for i in range(256)])
    out = im.copy()
    out.putalpha(ImageChops.multiply(im.getchannel("A"), conserva))
    return out


def _clouds(size: tuple[int, int], scale: float, octaves: int, rng) -> Image.Image:
    """Ruido de nubes: varias capas de ruido grueso suavizado y sumadas.

    Cada octava tiene el doble de detalle y la mitad de peso. Se genera chico y
    se agranda con interpolación suave, que es lo que da las manchas redondeadas
    en vez de un moteado de televisor.
    """
    ancho, alto = size
    lado = max(ancho, alto)
    acumulado = Image.new("L", size, 0)
    peso_total = 0.0
    for octava in range(octaves):
        celdas = max(2, round(lado / max(1.0, scale * lado / (2 ** octava))))
        pequeno = Image.frombytes(
            "L", (celdas, celdas), rng.randbytes(celdas * celdas)
        ).resize(size, Image.Resampling.BICUBIC)
        peso = 0.5 ** octava
        acumulado = ImageChops.add(
            acumulado, pequeno.point([round(i * peso) for i in range(256)])
        )
        peso_total += peso
    return acumulado.point([min(255, round(i / peso_total)) for i in range(256)])


def _border(size: tuple[int, int], strength: float) -> Image.Image:
    """Mapa que vale 0 en el borde y 255 al centro, atenuado por `strength`.

    Se arma chico y se escala: es un degradado, no tiene detalle que perder.
    """
    lado = 64
    piso = round(255 * (1 - strength))
    mapa = Image.new("L", (lado, lado))
    datos = []
    for y in range(lado):
        for x in range(lado):
            # La caída ocupa el cuarto exterior: repartida en media pieza,
            # el desgaste quedaba casi parejo y "edges" no se notaba.
            cerca = min(x, y, lado - 1 - x, lado - 1 - y) / (lado / 4)
            datos.append(piso + round((255 - piso) * min(1.0, cerca)))
    mapa.putdata(datos)
    return mapa.resize(size, Image.Resampling.BILINEAR)


def _knee(threshold: float) -> list[int]:
    """Curva que aplasta por debajo del umbral y estira por encima."""
    corte = threshold * 255
    rango = max(1.0, 255 - corte)
    return [0 if i <= corte else min(255, round((i - corte) * 255 / rango)) for i in range(256)]


def _unit(value, name) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise SpecError(f"{name} debe estar entre 0 y 1, llegó {value!r}")
    return float(value)


def _positive(value, name, top: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= top:
        raise SpecError(f"{name} debe estar entre 0 y {top}, llegó {value!r}")
    return float(value)