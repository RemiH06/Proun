"""El armado del collage, en dos tiempos.

`plan` sortea todo lo que depende del azar (qué imágenes entran, en qué orden,
con qué giro y en qué posición) usando solo la semilla. `render` toma ese plan y
lo dibuja para una resolución y un color concretos, sin volver a tocar el
generador aleatorio. Esa separación es la que garantiza que la misma semilla dé
la misma composición en todas las resoluciones y en todos los colores.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image

from . import colors, layout, loading, pool as pool_module
from .errors import SourceError, SpecError
from .geometry import parse_aspect
from .ops import (background, blend, crop, finish, mosaic, recolor, repeat, resize,
                  rotate, shapes, stain, text as text_op, tones, transparency)
from .spec import Layer, Spec


@dataclass(frozen=True)
class Placement:
    layer: Layer
    angle: float
    flip: str
    center: tuple[float, float]
    fill: float
    color: object = None
    text: object = None
    pool_choice: object = None


@dataclass(frozen=True)
class Plan:
    seed: int
    placements: tuple[Placement, ...]


def plan(spec: Spec, seed: int) -> Plan:
    """Sortea la composición. Depende solo de la semilla.

    Las capas con `cover` van primero y siempre entran: son el fondo, no
    participan del sorteo de cuántas capas hay ni del acomodo, y su orden es el
    declarado para que se puedan apilar de forma predecible.
    """
    rng = random.Random(seed)
    covers = [layer for layer in spec.sources if layer.cover]
    candidatos = _filter_by_rate([layer for layer in spec.sources if not layer.cover], rng)
    resto = _pick(candidatos, spec.layers, rng)
    rng.shuffle(resto)

    placements = [
        Placement(layer=layer, angle=angle, flip=flip, center=(0.5, 0.5), fill=1.0,
                  color=_choose(layer.color, rng, "colores"),
                  text=_choose_text(layer.text, rng),
                  pool_choice=_choose_pool(layer, rng))
        for layer, (angle, flip) in zip(covers, [rotate.decide(c.rotate, rng) for c in covers])
    ]
    turns = [rotate.decide(layer.rotate, rng) for layer in resto]
    centers = layout.positions(len(resto), rng, spec.layout)
    fills = layout.sizes(len(resto), rng, spec.layout)
    centers = _avoid_overlap(resto, centers, fills, rng)
    placements += [
        Placement(layer=layer, angle=angle, flip=flip,
                  center=_region_center(center, layer.region), fill=fill,
                  color=_choose(layer.color, rng, "colores"),
                  text=_choose_text(layer.text, rng),
                  pool_choice=_choose_pool(layer, rng))
        for layer, (angle, flip), center, fill in zip(resto, turns, centers, fills)
    ]
    return Plan(seed=seed, placements=tuple(placements))


def _filter_by_rate(layers, rng: random.Random):
    """Cada capa tiene una probabilidad `rate` de entrar al sorteo de cuántas hay.

    No consume el generador para una capa con rate=1 (el default), así que
    ninguna especificación existente cambia de resultado por esta función.
    """
    return [l for l in layers if l.rate >= 1.0 or rng.random() < l.rate]


def _avoid_overlap(layers, centers, fills, rng: random.Random):
    """Reubica por rechazo las capas que declararon `overlap`.

    Es una aproximación: compara contra `fill`, el tamaño de respaldo que
    sortea `layout.sizes`, así que una capa con `resize`, `crop` o `mosaic`
    propio (cuyo tamaño real no se conoce hasta `prepare`) no se mide bien
    contra las demás. Las capas sin `overlap` no se tocan y no consumen el
    generador: se devuelven en las mismas coordenadas crudas que entregó
    `layout.positions`, para que el mapeo de región de más abajo siga
    aplicándose una sola vez.
    """
    cajas = []
    crudos = list(centers)
    for i, layer in enumerate(layers):
        mapeado = _region_center(centers[i], layer.region)
        media = fills[i] / 2
        if layer.overlap is None:
            cajas.append((*mapeado, media, media))
            continue
        mejor_crudo, mejor_mapeado = centers[i], mapeado
        peor = _worst_overlap(mejor_mapeado, media, cajas)
        intentos = 0
        while peor > layer.overlap and intentos < 30:
            crudo = (rng.random(), rng.random())
            candidato = _region_center(crudo, layer.region)
            solape = _worst_overlap(candidato, media, cajas)
            if solape < peor:
                mejor_crudo, mejor_mapeado, peor = crudo, candidato, solape
            intentos += 1
        crudos[i] = mejor_crudo
        cajas.append((*mejor_mapeado, media, media))
    return crudos


def _worst_overlap(centro, media, cajas) -> float:
    peor = 0.0
    for cx, cy, chw, chh in cajas:
        ix = max(0.0, min(centro[0] + media, cx + chw) - max(centro[0] - media, cx - chw))
        iy = max(0.0, min(centro[1] + media, cy + chh) - max(centro[1] - media, cy - chh))
        interseccion = ix * iy
        if interseccion == 0:
            continue
        area_menor = min((2 * media) ** 2, (2 * chw) * (2 * chh))
        if area_menor > 0:
            peor = max(peor, interseccion / area_menor)
    return peor


def _region_center(center, region):
    """Mete el centro sorteado dentro de la región declarada por la capa.

    No consume el generador: reusa el sorteo que ya se hizo y lo remapea. Así
    una capa sin `region` sigue cayendo exactamente donde caía antes.
    """
    if region is None:
        return center
    x0, y0, x1, y1 = region
    dentro = (min(max(center[0], 0.0), 1.0), min(max(center[1], 0.0), 1.0))
    return (x0 + dentro[0] * (x1 - x0), y0 + dentro[1] * (y1 - y0))


def _choose(value, rng: random.Random, que: str):
    """Una capa puede declarar varias opciones (colores, textos) y se sortea
    una por wallpaper."""
    if isinstance(value, list):
        if not value:
            raise SpecError(f"la lista de {que} de una capa está vacía")
        return rng.choice(value)
    return value


def _choose_text(value, rng: random.Random):
    """Como `_choose`, pero el texto también puede traer la lista adentro de
    un objeto de configuración: {"text": [...], "weight": "bold"}."""
    if isinstance(value, dict) and isinstance(value.get("text"), list):
        opciones = value["text"]
        if not opciones:
            raise SpecError("la lista de textos de una capa está vacía")
        return {**value, "text": rng.choice(opciones)}
    return _choose(value, rng, "textos")


def _choose_pool(layer: Layer, rng: random.Random):
    """Resuelve qué archivo del pool usa esta capa, ponderado por qué tan
    bien calza contra `crop.aspect` y, si se pide, qué tan oscuro saldría."""
    if layer.pool is None:
        return None
    return pool_module.choose(
        layer.pool, _target_aspect(layer), layer.pool_bias, rng,
        crop_spec=layer.crop, tones_spec=layer.tones, dark_bias=layer.pool_dark_bias,
    )


def _target_aspect(layer: Layer):
    """El aspecto del hueco que esta capa dice que quiere llenar, si lo dice."""
    if isinstance(layer.crop, dict) and "aspect" in layer.crop:
        return parse_aspect(layer.crop["aspect"])
    return None


@dataclass(frozen=True)
class Shaped:
    """Capa ya recortada, escalada y normalizada, lista para recibir color."""

    tonal: Image.Image
    source: Image.Image | None
    position: tuple[int, int] | None = None


def prepare(spec: Spec, current: Plan, resolution: tuple[int, int]) -> tuple[Shaped, ...]:
    """Recorta, escala, arma mosaicos y gira, todo lo que no depende del color.

    Se guarda aparte porque un mismo plan se dibuja en varios colores: sin esto,
    la geometría se recalcularía una vez por color y es la parte cara.
    """
    measure_canvas = spec.reference if spec.scale_with_resolution else resolution
    scale = _scale(spec, resolution)
    shaped = tuple(
        _shape_layer(placement, measure_canvas, scale, resolution, current.seed, indice)
        for indice, placement in enumerate(current.placements)
    )
    if str(spec.layout.get("mode", "")).lower() == "align":
        shaped = _pack(shaped, current.placements, resolution, spec.layout)
    return shaped


def _pack(shaped: tuple[Shaped, ...], placements: tuple[Placement, ...],
          resolution: tuple[int, int], layout_spec: dict) -> tuple[Shaped, ...]:
    """Acomoda en estantería las capas que no tienen colocación manual propia.

    Se excluyen las capas `cover` (van al fondo, no al bloque) y cualquiera con
    `position` o `region` explícitos: esas ya tienen instrucciones concretas de
    dónde ir, y mezclarlas con el empaquetado no tiene una semántica clara.
    """
    indices = [
        i for i, p in enumerate(placements)
        if not p.layer.cover and p.layer.position is None and p.layer.region is None
    ]
    if not indices:
        return shaped

    width_frac, gap, anchor = layout.pack_options(layout_spec)
    sizes = [shaped[i].tonal.size for i in indices]
    posiciones, bloque = layout.pack(sizes, round(resolution[0] * width_frac), gap)
    offset = layout.center_block(bloque, resolution, anchor)

    resultado = list(shaped)
    for (x, y), i in zip(posiciones, indices):
        resultado[i] = replace(shaped[i], position=(offset[0] + x, offset[1] + y))
    return tuple(resultado)


def render(spec: Spec, current: Plan, resolution: tuple[int, int], main,
           shaped: tuple[Shaped, ...] | None = None) -> Image.Image:
    main = colors.parse(main)
    if shaped is None:
        shaped = prepare(spec, current, resolution)
    canvas = background.build(resolution, main, spec.background,
                              random.Random(current.seed ^ 0x5EED))

    for placement, base in zip(current.placements, shaped):
        layer = placement.layer
        try:
            tile = recolor.apply(base.tonal, placement.color or main, layer.recolor,
                                 base.source)
        except Exception as exc:
            raise SourceError(f"falló el recoloreado de {layer.src.name}: {exc}") from exc
        if layer.cover:
            position = (0, 0)
        elif base.position is not None:
            position = base.position
        elif placement.layer.position is not None:
            position = layout.explicit(
                placement.layer.position, tile.size, resolution, placement.layer.anchor
            )
        else:
            position = layout.to_pixels(placement.center, tile.size, resolution)
            if layer.bleed is not None:
                position = layout.clamp(position, tile.size, resolution, layer.bleed)
        blend.composite(canvas, tile, position,
                        mode=placement.layer.blend, opacity=placement.layer.opacity)

    return finish.apply(canvas, main, spec.finish, random.Random(current.seed))


def save(image: Image.Image, path: Path, fmt: str = "png", quality: int = 92,
         optimize: bool = False) -> Path:
    """Escribe el archivo. `optimize` recomprime el PNG: pesa menos y tarda mucho más."""
    path.parent.mkdir(parents=True, exist_ok=True)
    target = fmt.upper().replace("JPG", "JPEG")
    if target == "JPEG":
        flat = Image.new("RGB", image.size, (0, 0, 0))
        flat.paste(image, mask=image.getchannel("A"))
        flat.save(path, "JPEG", quality=quality, optimize=optimize, subsampling=1)
    elif target == "WEBP":
        image.save(path, "WEBP", quality=quality, method=5 if optimize else 3)
    else:
        image.save(path, "PNG", compress_level=6, optimize=optimize)
    return path


def _shape_layer(placement: Placement, measure_canvas, scale: float, resolution,
                 seed: int, indice: int) -> "Shaped":
    layer = placement.layer
    if layer.src is not None:
        nombre = layer.src.name
    elif layer.shape is not None:
        nombre = f"figura {layer.shape}"
    elif layer.pool is not None:
        nombre = f"{placement.pool_choice.name} (de un pool de {len(layer.pool)})"
    else:
        nombre = f"texto {str(layer.text)[:40]!r}"
    try:
        if layer.shape is not None:
            im = shapes.build(layer.shape, layer.outline)
        elif layer.text is not None:
            im = text_op.build(placement.text)
        elif layer.pool is not None:
            im = loading.load(placement.pool_choice)
        else:
            im = loading.load(layer.src)
        im = crop.apply(im, layer.crop)
        if layer.cover:
            # El ajuste al lienzo va al final, después de girar: si se hiciera
            # antes, un cuarto de vuelta dejaría el fondo sin cubrir.
            im = mosaic.apply(im, layer.mosaic, resolution)
            im = repeat.apply(im, layer.repeat)
            im = rotate.apply(im, placement.angle, placement.flip)
            im = resize.apply(im, {"size": list(resolution), "mode": "fill",
                                   "anchor": layer.anchor}, resolution)
        else:
            auto = layer.resize is None and layer.mosaic is None
            fallback = {"size": [placement.fill, placement.fill], "mode": "fit"}
            im = resize.apply(im, fallback if auto else layer.resize, measure_canvas)
            im = mosaic.apply(im, layer.mosaic, measure_canvas)
            im = repeat.apply(im, layer.repeat)
            im = rotate.apply(im, placement.angle, placement.flip)
            if scale != 1.0:
                im = im.resize(
                    (max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                    Image.Resampling.LANCZOS,
                )
        if layer.stain:
            # La semilla se deriva, no se saca del generador del plan: así una
            # capa manchada no corre el sorteo de las demás ni cambia los
            # wallpapers que ya existen.
            im = stain.apply(im, layer.stain, random.Random(seed * 1_000_003 + indice))
        if layer.shape is not None or layer.text is not None:
            # Ya sale en escala de grises exacta (relleno y contorno), sin
            # nada que normalizar o volver transparente por color.
            tonal = im
        else:
            tonal = transparency.apply(tones.apply(im, layer.tones), layer.transparent)
        keep = (layer.src is not None or layer.pool is not None) \
            and str(layer.recolor.get("mix_with", "tones")).lower() == "source"
        return Shaped(tonal=tonal, source=im if keep else None)
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError(f"falló el procesado de {nombre}: {exc}") from exc


def _scale(spec: Spec, resolution) -> float:
    if not spec.scale_with_resolution or spec.reference is None:
        return 1.0
    ref = spec.reference
    if ref == resolution:
        return 1.0
    return math.sqrt((resolution[0] * resolution[1]) / (ref[0] * ref[1]))


def _pick(available: list[Layer], limits, rng: random.Random) -> list[Layer]:
    if not limits:
        return available
    low, high = limits
    wanted = rng.randint(low, high)
    if wanted <= len(available):
        return rng.sample(available, wanted)
    return available + rng.choices(available, k=wanted - len(available))