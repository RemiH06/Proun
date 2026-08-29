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
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from . import colors, layout, loading
from .errors import SourceError
from .ops import background, blend, crop, finish, mosaic, recolor, resize, rotate, tones
from .spec import Layer, Spec


@dataclass(frozen=True)
class Placement:
    layer: Layer
    angle: float
    flip: str
    center: tuple[float, float]
    fill: float


@dataclass(frozen=True)
class Plan:
    seed: int
    placements: tuple[Placement, ...]


def plan(spec: Spec, seed: int) -> Plan:
    rng = random.Random(seed)
    chosen = _pick(list(spec.sources), spec.layers, rng)
    rng.shuffle(chosen)
    turns = [rotate.decide(layer.rotate, rng) for layer in chosen]
    centers = layout.positions(len(chosen), rng, spec.layout)
    fills = layout.sizes(len(chosen), rng, spec.layout)
    return Plan(
        seed=seed,
        placements=tuple(
            Placement(layer=layer, angle=angle, flip=flip, center=center, fill=fill)
            for layer, (angle, flip), center, fill in zip(chosen, turns, centers, fills)
        ),
    )


@dataclass(frozen=True)
class Shaped:
    """Capa ya recortada, escalada y normalizada, lista para recibir color."""

    tonal: Image.Image
    source: Image.Image | None


def prepare(spec: Spec, current: Plan, resolution: tuple[int, int]) -> tuple[Shaped, ...]:
    """Recorta, escala, arma mosaicos y gira, todo lo que no depende del color.

    Se guarda aparte porque un mismo plan se dibuja en varios colores: sin esto,
    la geometría se recalcularía una vez por color y es la parte cara.
    """
    measure_canvas = spec.reference if spec.scale_with_resolution else resolution
    scale = _scale(spec, resolution)
    return tuple(
        _shape_layer(placement, measure_canvas, scale) for placement in current.placements
    )


def render(spec: Spec, current: Plan, resolution: tuple[int, int], main,
           shaped: tuple[Shaped, ...] | None = None) -> Image.Image:
    main = colors.parse(main)
    if shaped is None:
        shaped = prepare(spec, current, resolution)
    canvas = background.build(resolution, main, spec.background)

    for placement, base in zip(current.placements, shaped):
        layer = placement.layer
        try:
            tile = recolor.apply(base.tonal, layer.color or main, layer.recolor, base.source)
        except Exception as exc:
            raise SourceError(f"falló el recoloreado de {layer.src.name}: {exc}") from exc
        if placement.layer.position is not None:
            position = layout.explicit(
                placement.layer.position, tile.size, resolution, placement.layer.anchor
            )
        else:
            position = layout.to_pixels(placement.center, tile.size, resolution)
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


def _shape_layer(placement: Placement, measure_canvas, scale: float) -> "Shaped":
    layer = placement.layer
    try:
        im = loading.load(layer.src)
        im = crop.apply(im, layer.crop)
        auto = layer.resize is None and layer.mosaic is None
        fallback = {"size": [placement.fill, placement.fill], "mode": "fit"}
        im = resize.apply(im, fallback if auto else layer.resize, measure_canvas)
        im = mosaic.apply(im, layer.mosaic, measure_canvas)
        im = rotate.apply(im, placement.angle, placement.flip)
        if scale != 1.0:
            im = im.resize(
                (max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                Image.Resampling.LANCZOS,
            )
        tonal = tones.apply(im, layer.tones)
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