"""Convención de salida.

    wallpapers/1920x1080/wp_0007_3ba7ff_849213_1a2b3c4d.png
               ^resolución  ^   ^índice ^color  ^semilla ^hash de config

El índice identifica la composición: el mismo número con distinto color es el
mismo collage recoloreado. La semilla del nombre es la que hay que pasarle a
`--seeds` para volver a generar exactamente ese wallpaper.

El hash es opcional y resume todo lo que influye en el resultado pero no
viaja ya en el nombre (layout, fondo, recoloreado, capas...). Sin él, comparar
solo por nombre no alcanza: cambiar uno de esos parámetros deja un archivo
viejo que `--overwrite` nunca toca porque el nombre no cambió. Con el hash,
un cambio de configuración cambia el nombre, así que el archivo viejo queda
como lo que es, un sobrante, y no se confunde con uno vigente. Ver
`content_hash`.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from pathlib import Path

from .errors import SpecError

PATTERN = re.compile(
    r"^wp_(?P<index>\d{4,})_(?P<color>[0-9a-f]{6})_(?P<seed>\d+)(?:_(?P<hash>[0-9a-f]{8}))?$"
)

# Campos de Spec que ya viajan en el nombre (color, semilla) o que no cambian
# el resultado visual (encoding, ubicación, numeración): quedan fuera del hash.
_SIN_HASH = {"resolutions", "colors", "seeds", "output", "fmt", "quality",
             "optimize", "start_index"}


def filename(index: int, color_hex: str, seed: int, ext: str = "png",
            config_hash: str | None = None) -> str:
    if index < 0:
        raise SpecError(f"índice negativo: {index}")
    if seed < 0:
        raise SpecError(f"semilla negativa: {seed}")
    sufijo = ""
    if config_hash is not None:
        if not re.fullmatch(r"[0-9a-f]{8}", config_hash):
            raise SpecError(
                f"config_hash debe ser 8 caracteres hexadecimales, llegó {config_hash!r}"
            )
        sufijo = f"_{config_hash}"
    return f"wp_{index:04d}_{color_hex.lower().lstrip('#')}_{seed}{sufijo}.{ext.lstrip('.')}"


def content_hash(spec) -> str:
    """Hash corto de la parte de `Spec` que decide el resultado pero no
    viaja en el nombre del archivo. Determinista para la misma configuración,
    distinto en cuanto cambia cualquier cosa que afecte la composición."""
    datos = dataclasses.asdict(spec)
    for clave in _SIN_HASH:
        datos.pop(clave, None)
    crudo = json.dumps(datos, sort_keys=True, default=str)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:8]


def resolution_dir(root, size: tuple[int, int]) -> Path:
    return Path(root) / f"{size[0]}x{size[1]}"


def parse(name) -> dict:
    """Lee un nombre generado y devuelve índice, color, semilla y, si lo
    trae, el hash de configuración."""
    match = PATTERN.match(Path(name).stem)
    if not match:
        raise SpecError(f"'{name}' no sigue el patrón wp_####_color_semilla")
    data = match.groupdict()
    resultado = {"index": int(data["index"]), "color": data["color"], "seed": int(data["seed"])}
    if data["hash"] is not None:
        resultado["hash"] = data["hash"]
    return resultado
