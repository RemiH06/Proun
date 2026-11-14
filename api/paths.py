"""Resolución de las rutas que manda el frontend.

Una ruta relativa (`"fuentes"`) se resuelve distinto según desde dónde se
haya lanzado el proceso de `uvicorn`, así que "funciona si lo corres desde
la raíz del repo, falla si lo corres desde cualquier otro lado" es un bug
esperando pasar. Ancla toda ruta relativa a la raíz del proyecto (dos
niveles arriba de este archivo: `api/paths.py` -> `api/` -> raíz), sin
importar el directorio de trabajo real del proceso.

Además, toda ruta que llega del cliente (carpeta a listar, `src` de una
capa, fuente de un texto, carpeta de salida, wallpaper a recolorear) tiene
que caer dentro de una de las carpetas permitidas. Sin esto, la API lee
cualquier imagen del disco y escribe PNG junto a cualquier ruta: aceptable
en una herramienta local, no detrás de una URL pública. Las carpetas
permitidas son `fuentes/` y `wallpapers/` del proyecto, o las que diga
`PROUN_RAICES` (separadas por `os.pathsep`: `;` en Windows, `:` en Linux).
"""

from __future__ import annotations

import os
from pathlib import Path

from proun.errors import SpecError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAICES_POR_DEFECTO = ("fuentes", "wallpapers")


def raices() -> tuple[Path, ...]:
    """Se lee en cada llamada (no al importar) para que un cambio de
    `PROUN_RAICES` se note sin reiniciar, y para que las pruebas lo ajusten."""
    declaradas = os.environ.get("PROUN_RAICES", "")
    nombres = [p for p in declaradas.split(os.pathsep) if p] or RAICES_POR_DEFECTO
    return tuple(_anclar(nombre).resolve() for nombre in nombres)


def _anclar(path: str) -> Path:
    ruta = Path(path).expanduser()
    return ruta if ruta.is_absolute() else PROJECT_ROOT / ruta


def resolve_sources_path(path: str) -> str:
    ruta = _anclar(path)
    # `resolve()` deshace `..` y enlaces simbólicos antes de comparar: si no,
    # "fuentes/../api/main.py" o un enlace dentro de fuentes/ se saldrían.
    real = ruta.resolve()
    if not any(real.is_relative_to(raiz) for raiz in raices()):
        raise SpecError(f"la ruta está fuera de las carpetas permitidas: {path}")
    return str(ruta)
