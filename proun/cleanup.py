"""Borrado de los wallpapers generados.

Solo toca archivos cuyo nombre siga la convención `wp_####_color_semilla`, así
que un directorio de salida compartido con otras cosas queda intacto. Los
subdirectorios de resolución que quedan vacíos se eliminan después.
"""

from __future__ import annotations

from pathlib import Path

from . import colors, naming
from .errors import SpecError


def find(root, resolutions=None, palette=None, seeds=None) -> list[Path]:
    """Wallpapers generados bajo `root`, filtrados por lo que se pida.

    Un filtro en None no filtra. Los tres se combinan con "y".
    """
    directory = Path(root).expanduser()
    if not directory.is_dir():
        return []

    folders = {f"{w}x{h}" for w, h in resolutions} if resolutions else None
    wanted = {colors.to_hex(c) for c in palette} if palette else None
    marks = set(seeds) if seeds else None

    found = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        try:
            data = naming.parse(path.name)
        except SpecError:
            continue
        if folders is not None and path.parent.name not in folders:
            continue
        if wanted is not None and data["color"] not in wanted:
            continue
        if marks is not None and data["seed"] not in marks:
            continue
        found.append(path)
    return found


def remove(paths, root=None) -> int:
    """Borra los archivos y luego los directorios que quedaron vacíos."""
    deleted = 0
    for path in paths:
        try:
            Path(path).unlink()
            deleted += 1
        except OSError as exc:
            raise SpecError(f"no se pudo borrar {path}: {exc}") from exc
    if root is not None:
        _prune(Path(root).expanduser())
    return deleted


def _prune(root: Path) -> None:
    """Quita subdirectorios vacíos, de adentro hacia afuera. Deja la raíz."""
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()