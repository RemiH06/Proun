"""Resolución de la ruta de fuentes que manda el frontend.

Una ruta relativa (`"fuentes"`) se resuelve distinto según desde dónde se
haya lanzado el proceso de `uvicorn`, así que "funciona si lo corres desde
la raíz del repo, falla si lo corres desde cualquier otro lado" es un bug
esperando pasar. Ancla toda ruta relativa a la raíz del proyecto (dos
niveles arriba de este archivo: `api/paths.py` -> `api/` -> raíz), sin
importar el directorio de trabajo real del proceso.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_sources_path(path: str) -> str:
    ruta = Path(path).expanduser()
    return str(ruta if ruta.is_absolute() else PROJECT_ROOT / ruta)
