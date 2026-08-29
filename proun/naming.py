"""Convención de salida.

    wallpapers/1920x1080/wp_0007_3ba7ff_849213.png
               ^resolución  ^   ^índice ^color  ^semilla

El índice identifica la composición: el mismo número con distinto color es el
mismo collage recoloreado. La semilla del nombre es la que hay que pasarle a
`--seeds` para volver a generar exactamente ese wallpaper.
"""

from __future__ import annotations

import re
from pathlib import Path

from .errors import SpecError

PATTERN = re.compile(r"^wp_(?P<index>\d{4,})_(?P<color>[0-9a-f]{6})_(?P<seed>\d+)$")


def filename(index: int, color_hex: str, seed: int, ext: str = "png") -> str:
    if index < 0:
        raise SpecError(f"índice negativo: {index}")
    if seed < 0:
        raise SpecError(f"semilla negativa: {seed}")
    return f"wp_{index:04d}_{color_hex.lower().lstrip('#')}_{seed}.{ext.lstrip('.')}"


def resolution_dir(root, size: tuple[int, int]) -> Path:
    return Path(root) / f"{size[0]}x{size[1]}"


def parse(name) -> dict:
    """Lee un nombre generado y devuelve índice, color y semilla."""
    match = PATTERN.match(Path(name).stem)
    if not match:
        raise SpecError(f"'{name}' no sigue el patrón wp_####_color_semilla")
    data = match.groupdict()
    return {"index": int(data["index"]), "color": data["color"], "seed": int(data["seed"])}