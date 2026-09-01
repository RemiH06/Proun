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

from . import colors, layout, loading
from .errors import SourceError, SpecError
from .ops import (background, blend, crop, finish, mosaic, recolor, repeat, resize,
                  rotate, stain, tones, transparency)
from .spec import Layer, Spec


@dataclass(frozen=True)
class Placement:
    layer: Layer
    angle: float
    flip: str
    center: tuple[float, float]
    fill: float
    color: object = None


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
    resto = _pick([layer for layer in spec.sources if not layer.cover], spec.layers, rng)
    rng.shuffle(resto)

    placements = [
        Placement(layer=layer, angle=angle, flip=flip, center=(0.5, 0.5), fill=1.0,
                  color=_choose_color(layer.color, rng))
        for layer, (angle, flip) in zip(covers, [rotate.decide(c.rotate, rng) for c in covers])
    ]
    turns = [rotate.decide(layer.rotate, rng) for layer in resto]
    centers = layout.positions(len(resto), rng, spec.layout)
    fills = layout.sizes(len(resto), rng, spec.layout)
    placements += [
        Placement(layer=layer, angle=angle, flip=flip,
                  center=_region_center(center, layer.region), fill=fill,
                  color=_choose_color(layer.color, rng))
        for layer, (angle, flip), center, fill in zip(resto, turns, centers, fills)
    ]
    return Plan(seed=seed, placements=tuple(placements))


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


def _choose_color(color, rng: random.Random):
    """Una capa puede declarar varios colores y se sortea uno por wallpaper."""
    if isinstance(color, list):
        if not color:
            raise SpecError("la lista de colores de una capa está vacía")
        return rng.choice(color)
    return color


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
    try:
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
        tonal = transparency.apply(tones.apply(im, layer.tones), layer.transparent)
        keep = str(layer.recolor.get("mix_with", "tones")).lower() == "source"
        return Shaped(tonal=tonal, source=im if keep else None)
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError(f"falló el procesado de {layer.src.name}: {exc}") from exc


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