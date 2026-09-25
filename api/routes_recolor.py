"""Rutas para volver a colorear un wallpaper YA exportado, sin reconstruirlo
desde sus capas originales: reusan `recolorear.recolorear` tal cual, la
misma función que usa el script de línea de comandos. También pueden
rotar/voltear y encajar en otra resolución antes de recolorear (comparten
`_preparar`), y `/recolor/export-all` genera de una todas las variantes
(todos los colormaps más el negativo), guardándolas junto al original.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response
from PIL import Image

import recolorear
from proun import loading
from proun import spec as spec_module
from proun.errors import SpecError
from proun.ops import resize as resize_op
from proun.ops import rotate
from proun.ops.recolor import COLORMAPS

from .paths import resolve_sources_path
from .schemas import RecolorAllRequest, RecolorGeometry, RecolorRequest

router = APIRouter()


def _flip_mode(flip_h: bool, flip_v: bool) -> str:
    if flip_h and flip_v:
        return "both"
    if flip_h:
        return "horizontal"
    if flip_v:
        return "vertical"
    return "none"


def _preparar(body: RecolorGeometry, ruta: str) -> Image.Image:
    """Carga la imagen y le aplica rotar/voltear y encajar en otra
    resolución, si se pidió: lo comparten preview, export y export-all."""
    if body.angle not in rotate.QUARTERS:
        raise SpecError(f"angle debe ser uno de {rotate.QUARTERS}, llegó {body.angle!r}")
    imagen = loading.load(ruta)
    if body.angle or body.flip_h or body.flip_v:
        imagen = rotate.apply(imagen, body.angle, _flip_mode(body.flip_h, body.flip_v))
    if body.resolution:
        ancho, alto = spec_module.parse_resolutions([body.resolution])[0]
        imagen = resize_op.apply(imagen, {"size": [ancho, alto], "mode": "fill"}, (ancho, alto))
    return imagen


def _repintar(body: RecolorRequest) -> Image.Image:
    ruta = resolve_sources_path(body.path)
    imagen = _preparar(body, ruta)
    return recolorear.recolorear(imagen, mode=body.mode, name=body.name, stops=body.stops)


@router.post("/recolor/preview")
def preview(body: RecolorRequest) -> Response:
    imagen = _repintar(body)
    buffer = io.BytesIO()
    imagen.convert("RGB").save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.post("/recolor/export")
def export(body: RecolorRequest) -> Response:
    imagen = _repintar(body)
    origen = Path(resolve_sources_path(body.path))
    sufijo = "invertido" if body.mode == "invert" else ("personalizado" if body.stops else body.name)
    destino = origen.with_stem(f"{origen.stem}_{sufijo}")
    imagen.convert("RGB").save(destino)
    return Response(
        content=destino.read_bytes(),
        media_type="image/png",
        headers={"X-Export-Path": str(destino)},
    )


@router.post("/recolor/export-all")
def export_all(body: RecolorAllRequest) -> dict:
    """Genera los colormaps con nombre más el negativo y los guarda todos
    junto al original, en su misma carpeta: para tener listas todas las
    variantes de un wallpaper sin exportarlas una por una."""
    ruta = resolve_sources_path(body.path)
    imagen = _preparar(body, ruta)
    origen = Path(ruta)

    guardadas = []
    for nombre in COLORMAPS:
        salida = recolorear.recolorear(imagen, mode="colormap", name=nombre)
        destino = origen.with_stem(f"{origen.stem}_{nombre}")
        salida.convert("RGB").save(destino)
        guardadas.append(str(destino))

    salida = recolorear.recolorear(imagen, mode="invert")
    destino = origen.with_stem(f"{origen.stem}_invertido")
    salida.convert("RGB").save(destino)
    guardadas.append(str(destino))

    return {"folder": str(origen.parent), "paths": guardadas}
