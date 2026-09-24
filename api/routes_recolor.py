"""Rutas para volver a colorear un wallpaper YA exportado, sin reconstruirlo
desde sus capas originales: reusan `recolorear.recolorear` tal cual, la
misma función que usa el script de línea de comandos.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response
from PIL import Image

import recolorear
from proun import loading

from .paths import resolve_sources_path
from .schemas import RecolorRequest

router = APIRouter()


def _repintar(body: RecolorRequest) -> Image.Image:
    ruta = resolve_sources_path(body.path)
    imagen = loading.load(ruta)
    return recolorear.recolorear(imagen, name=body.name, stops=body.stops)


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
    sufijo = "personalizado" if body.stops else body.name
    destino = origen.with_stem(f"{origen.stem}_{sufijo}")
    imagen.convert("RGB").save(destino)
    return Response(
        content=destino.read_bytes(),
        media_type="image/png",
        headers={"X-Export-Path": str(destino)},
    )
