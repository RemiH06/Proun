"""Cache en memoria de la etapa cara de compose (`prepare`), para no rehacer
geometría cuando lo único que cambia es color o recoloreado.

Aparte de `naming.content_hash`: ese hash existe para nombrar archivos e
incluye a propósito el recoloreado (dos recoloreados distintos merecen
nombres distintos al exportar). `compose.prepare` no lee `recolor`,
`opacity` ni `blend` para nada, esos tres se leen recién en
`compose.render` (`blend.composite(canvas, tile, position,
mode=placement.layer.blend, opacity=placement.layer.opacity)`), así que
usar `content_hash` tal cual acá forzaría rehacer geometría por gusto cada
vez que cambia cualquiera de los tres. `geometry_hash` es el mismo
mecanismo, con `recolor`/`color`/`opacity`/`blend` también afuera de cada
capa.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections import OrderedDict

from proun.naming import _SIN_HASH

MAX_ENTRADAS = 8

_SIN_HASH_POR_CAPA = {"recolor", "color", "opacity", "blend"}


def geometry_hash(spec) -> str:
    datos = dataclasses.asdict(spec)
    for clave in _SIN_HASH:
        datos.pop(clave, None)
    for capa in datos.get("sources", []):
        for clave in _SIN_HASH_POR_CAPA:
            capa.pop(clave, None)
    crudo = json.dumps(datos, sort_keys=True, default=str)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:8]


class ShapedCache:
    """LRU chico: un solo usuario local activo, alcanza con guardar unas pocas."""

    def __init__(self, max_entradas: int = MAX_ENTRADAS):
        self._datos: OrderedDict = OrderedDict()
        self._max = max_entradas

    def get(self, key):
        valor = self._datos.get(key)
        if valor is not None:
            self._datos.move_to_end(key)
        return valor

    def put(self, key, value) -> None:
        self._datos[key] = value
        self._datos.move_to_end(key)
        while len(self._datos) > self._max:
            self._datos.popitem(last=False)

    def clear(self) -> None:
        self._datos.clear()


cache = ShapedCache()
