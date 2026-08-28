"""Descubrimiento y carga de las imágenes de origen."""

from __future__ import annotations

import glob
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import SourceError

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif"}

_cache: dict[Path, Image.Image] = {}


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
    return cached.copy()


def clear_cache() -> None:
    _cache.clear()