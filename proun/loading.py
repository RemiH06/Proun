"""Descubrimiento y carga de las imágenes de origen."""

from __future__ import annotations

import glob
import os
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import SourceError

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif"}

# Imágenes ya decodificadas (RGBA, 4 bytes por píxel), las de uso más
# reciente al final. Con tope de memoria: sin él, recorrer las 165 fotos de
# fuentes/ dejaba 3.7 GB retenidos para siempre en el proceso de la API. En
# un lote de la CLI que reusa pocas fotos entre semillas sigue igual de útil.
# `PROUN_CACHE_MB` lo ajusta.
_cache: OrderedDict[Path, Image.Image] = OrderedDict()
CACHE_BYTES = int(os.environ.get("PROUN_CACHE_MB", "512")) * 1024 * 1024


def expand(patterns) -> list[Path]:
    """Convierte archivos, directorios y globs en una lista ordenada de archivos.

    No falla si un patrón no encuentra nada; eso lo decide quien llama, que sí
    sabe si la lista vacía es un problema.
    """
    if isinstance(patterns, (str, Path)):
        patterns = [patterns]
    found: list[Path] = []
    for pattern in patterns:
        path = Path(pattern).expanduser()
        if path.is_dir():
            found += sorted(p for p in path.rglob("*") if _usable(p))
        elif path.is_file():
            found.append(path)
        else:
            found += sorted(
                Path(m) for m in glob.glob(str(path), recursive=True) if _usable(Path(m))
            )
    seen: dict[Path, None] = {}
    for p in found:
        seen.setdefault(p.resolve(), None)
    return list(seen)


def _usable(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in EXTENSIONS


def load(path) -> Image.Image:
    """Abre una imagen en RGBA, corrige la orientación EXIF y la deja en caché.

    Devuelve siempre una copia, así que quien la recibe puede mutarla sin miedo.
    """
    key = Path(path).expanduser().resolve()
    cached = _cache.get(key)
    if cached is None:
        if not key.is_file():
            raise SourceError(f"no existe la imagen: {path}")
        try:
            with Image.open(key) as im:
                im.load()
                cached = ImageOps.exif_transpose(im).convert("RGBA")
        except (UnidentifiedImageError, OSError) as exc:
            raise SourceError(f"no se pudo leer la imagen {path}: {exc}") from exc
        _cache[key] = cached
        while sum(_bytes(i) for i in _cache.values()) > CACHE_BYTES and len(_cache) > 1:
            _cache.popitem(last=False)
    _cache.move_to_end(key)
    return cached.copy()


def _bytes(im: Image.Image) -> int:
    return im.width * im.height * 4


def thumbnail(path, side: int) -> Image.Image:
    """Miniatura sin pasar por la caché de `load`: una lista de cientos de
    fotos no debe decodificarlas todas a tamaño completo. `draft` deja que
    el decodificador de JPEG reduzca al leer, mucho más barato."""
    key = Path(path).expanduser()
    if not key.is_file():
        raise SourceError(f"no existe la imagen: {path}")
    try:
        with Image.open(key) as im:
            im.draft("RGB", (side, side))
            mini = ImageOps.exif_transpose(im)
            mini.thumbnail((side, side))
            return mini.convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise SourceError(f"no se pudo leer la imagen {path}: {exc}") from exc


def peek_size(path) -> tuple[int, int]:
    """El tamaño de una imagen sin decodificar los píxeles, con la corrección
    de orientación EXIF ya aplicada.

    Sirve para pesar candidatas de un pool sin pagar el costo de abrir y
    decodificar cada una entera: `Image.open` sin `.load()` solo lee la
    cabecera.
    """
    key = Path(path).expanduser()
    try:
        with Image.open(key) as im:
            w, h = im.size
            orientacion = im.getexif().get(0x0112, 1)
    except (UnidentifiedImageError, OSError) as exc:
        raise SourceError(f"no se pudo leer la imagen {path}: {exc}") from exc
    if orientacion in (5, 6, 7, 8):
        w, h = h, w
    return (w, h)


def clear_cache() -> None:
    _cache.clear()