"""Mosaico: repetir una imagen en cuadrícula en vez de escalarla.

Formas aceptadas en `mosaic`:
    2                            cuadrícula 2x2 (300x300 -> 600x600)
    [4, 1]                       tira de 4 columnas por 1 fila (300x300 -> 1200x300)
    {"grid": [4, 1]}             lo mismo
    {"size": [1920, 1080]}       repite lo necesario y recorta al tamaño exacto
    {"size": [1.0, 1.0]}         mismo caso pero relativo al lienzo
    {"tile": [150, 150]}         reescala la pieza antes de repetir
    {"mirror": true}             espeja filas y columnas alternas (bordes continuos)
    {"offset": [0.5, 0]}         desfase de filas tipo ladrillo, en fracción de pieza
"""

from __future__ import annotations

import math

from PIL import Image

from ..errors import SpecError
from ..geometry import pair
from .resize import RESAMPLE


def apply(im: Image.Image, spec, canvas: tuple[int, int], rng=None) -> Image.Image:
    if spec is None or spec is False:
        return im
    if isinstance(spec, int) and not isinstance(spec, bool):
        spec = {"grid": [spec, spec]}
    elif isinstance(spec, (list, tuple)):
        spec = {"grid": list(spec)}
    if not isinstance(spec, dict):
        raise SpecError(f"mosaic debe ser un entero, un par o un objeto, llegó {spec!r}")

    unknown = set(spec) - {"grid", "size", "tile", "mirror", "offset", "resample"}
    if unknown:
        raise SpecError(f"claves desconocidas en mosaic: {sorted(unknown)}")

    modes = {"grid", "size"} & set(spec)
    if not modes:
        raise SpecError("mosaic necesita grid o size")
    if len(modes) > 1:
        raise SpecError("mosaic admite grid o size, no los dos: grid fija la cantidad de "
                        "piezas y size fija el resultado final")

    tile = im
    if "tile" in spec:
        filt = RESAMPLE.get(str(spec.get("resample", "lanczos")).lower())
        if filt is None:
            raise SpecError(f"resample debe ser uno de {sorted(RESAMPLE)}")
        tile = im.resize(pair(spec["tile"], im.size, name="mosaic.tile"), filt)

    mirror = bool(spec.get("mirror", False))
    offset = _offset(spec.get("offset"))

    if "size" in spec:
        out_size = pair(spec["size"], canvas, name="mosaic.size")
        cols = math.ceil(out_size[0] / tile.width) + (1 if offset[0] else 0)
        rows = math.ceil(out_size[1] / tile.height) + (1 if offset[1] else 0)
    elif "grid" in spec:
        grid = spec["grid"]
        if not isinstance(grid, (list, tuple)) or len(grid) != 2:
            raise SpecError(f"mosaic.grid debe ser [columnas, filas], llegó {grid!r}")
        cols, rows = (_count(grid[0], "columnas"), _count(grid[1], "filas"))
        out_size = (tile.width * cols, tile.height * rows)

    if cols * rows > 20_000:
        raise SpecError(f"el mosaico pediría {cols * rows} piezas, revisa el tamaño de la pieza")

    sheet = Image.new("RGBA", (tile.width * cols, tile.height * rows), (0, 0, 0, 0))
    for row in range(rows):
        for col in range(cols):
            piece = tile
            if mirror:
                if col % 2:
                    piece = piece.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if row % 2:
                    piece = piece.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            sheet.paste(piece, (col * tile.width, row * tile.height))

    dx = round(offset[0] * tile.width)
    dy = round(offset[1] * tile.height)
    if dx or dy:
        sheet = _stagger(sheet, tile.size, (cols, rows), (dx, dy))

    if "size" in spec:
        left = dx if dx else 0
        top = dy if dy else 0
        return sheet.crop((left, top, left + out_size[0], top + out_size[1]))
    return sheet


def _stagger(sheet, tile_size, grid, delta):
    """Desplaza filas o columnas alternas para el patrón tipo ladrillo."""
    tw, th = tile_size
    cols, rows = grid
    out = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
    for row in range(rows):
        band = sheet.crop((0, row * th, sheet.width, (row + 1) * th))
        shift = delta[0] * (row % 2)
        out.paste(band, (-shift, row * th))
        if shift:
            out.paste(band, (sheet.width - shift, row * th))
    if delta[1]:
        shifted = Image.new("RGBA", out.size, (0, 0, 0, 0))
        for col in range(cols):
            band = out.crop((col * tw, 0, (col + 1) * tw, out.height))
            shift = delta[1] * (col % 2)
            shifted.paste(band, (col * tw, -shift))
            if shift:
                shifted.paste(band, (col * tw, out.height - shift))
        out = shifted
    return out


def _count(value, name) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SpecError(f"mosaic.grid[{name}] debe ser un entero positivo, llegó {value!r}")
    return value


def _offset(value) -> tuple[float, float]:
    if value is None:
        return (0.0, 0.0)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = [value, 0]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"mosaic.offset debe ser un número o un par, llegó {value!r}")
    out = []
    for v in value:
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v < 1:
            raise SpecError(f"mosaic.offset debe estar en [0, 1), llegó {v!r}")
        out.append(float(v))
    return (out[0], out[1])