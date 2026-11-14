"""Rutas para explorar carpetas de imágenes: listado y miniaturas."""

from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import Response

from proun import loading

from .paths import resolve_sources_path
from .schemas import SourceListResponse

router = APIRouter()


@router.get("/sources/used")
def used_sources() -> dict:
    return {"paths": usadas_en(Path(resolve_sources_path("wallpapers")))}


def usadas_en(carpeta: Path) -> list[str]:
    """Imágenes (`src` de cada capa) que aparecen en los JSON que el GUI dejó
    junto a sus wallpapers. Un JSON roto no tira el listado entero: se salta."""
    if not carpeta.is_dir():
        return []
    usadas: set[str] = set()
    for archivo in carpeta.rglob("*.json"):
        try:
            spec = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        capas = spec.get("sources", []) if isinstance(spec, dict) else []
        for capa in capas if isinstance(capas, list) else []:
            src = capa.get("src") if isinstance(capa, dict) else None
            if isinstance(src, str):
                usadas.add(str(Path(src).expanduser().resolve()))
    return sorted(usadas)


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
