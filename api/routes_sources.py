"""Rutas para explorar carpetas de imágenes: listado y miniaturas."""

from __future__ import annotations

import io

from fastapi import APIRouter, Query
from fastapi.responses import Response

from proun import loading

from .paths import resolve_sources_path
from .schemas import SourceListResponse

router = APIRouter()


@router.get("/sources", response_model=SourceListResponse)
def list_sources(path: str = Query(...)) -> dict:
    resuelta = resolve_sources_path(path)
    encontradas = loading.expand([resuelta])
    return {
        # La ruta ya resuelta (absoluta), no la que mandó el cliente: así se
        # ve exactamente qué carpeta se buscó de verdad, sin adivinar contra
        # qué directorio de trabajo se resolvió una ruta relativa.
        "path": resuelta,
        "count": len(encontradas),
        "images": [{"path": str(p), "name": p.name} for p in encontradas],
    }


@router.get("/sources/thumbnail")
def thumbnail(path: str = Query(...), size: int = 160) -> Response:
    imagen = loading.load(path)
    imagen.thumbnail((size, size))
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
