"""Rutas para generar el collage: preview de baja resolución y export final.

Todo el trabajo real ya existe en `proun.spec`/`proun.compose`; estas rutas
solo arman el dict que `spec.build` acepta y devuelven la imagen resultante.
"""

from __future__ import annotations

import io
import json
import re

from fastapi import APIRouter
from fastapi.responses import Response

from proun import colors, compose, naming
from proun import spec as spec_module
from proun.errors import SpecError

from .cache import cache, geometry_hash
from .paths import resolve_sources_path
from .schemas import ExportRequest, PreviewRequest

router = APIRouter()

PREVIEW_LADO_MAYOR = 480
# Tope del lado mayor de cualquier lienzo que pida el cliente: cubre 4K y
# todas las pantallas de celular de `RESOLUTIONS` en `client.ts`, y evita
# que una sola petición ocupe el CPU minutos con un lienzo gigante. La CLI
# no pasa por aquí: sigue sin tope.
LADO_MAXIMO = 4096

_MEDIA_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp"}


def dimensiones(resolution: str) -> tuple[int, int]:
    """`spec.parse_resolutions` de una sola resolución, con `LADO_MAXIMO`."""
    ancho, alto = spec_module.parse_resolutions([resolution])[0]
    if max(ancho, alto) > LADO_MAXIMO:
        raise SpecError(f"la resolución no puede pasar de {LADO_MAXIMO} px por lado, llegó {resolution}")
    return ancho, alto


def _resolucion_de_vista_previa(resolution: str) -> str:
    """Vista previa chica, pero con el mismo aspecto que se va a exportar:
    si no, elegir un tamaño de celular (vertical) se seguiría viendo
    horizontal en la vista previa hasta exportar de verdad."""
    ancho, alto = dimensiones(resolution)
    factor = PREVIEW_LADO_MAYOR / max(ancho, alto)
    return f"{max(1, round(ancho * factor))}x{max(1, round(alto * factor))}"


def _sin_explosion_de_mosaico(capa: dict, lado_mayor: int) -> dict:
    """Si la capa pide `mosaic` sin su propio `resize`, el motor salta el
    ajuste automático al hueco del layout (`compose._shape_layer`: `auto =
    layer.resize is None and layer.mosaic is None`) y arranca del tamaño
    nativo del archivo. Con una foto de verdad (miles de px) y una grilla de
    3x3, eso da una capa de decenas de miles de px, gigante contra el
    lienzo. Se achica el mosaico antes de armarlo para que el resultado se
    quede en la escala del lienzo, no en la del archivo original."""
    grid = capa.get("mosaic", {}).get("grid") if isinstance(capa.get("mosaic"), dict) else None
    if not capa.get("mosaic") or "resize" in capa or not grid:
        return capa
    factor = max(1, max(grid))
    return {**capa, "resize": {"max_side": max(1, round(lado_mayor / factor))}}


def _rutas_permitidas(capa: dict) -> dict:
    """Las dos rutas de archivo que puede traer una capa (`src` y la `font`
    de un texto) pasan por `resolve_sources_path`: ver `api/paths.py`."""
    if "src" in capa:
        capa = {**capa, "src": resolve_sources_path(capa["src"])}
    texto = capa.get("text")
    if isinstance(texto, dict) and "font" in texto:
        capa = {**capa, "text": {**texto, "font": resolve_sources_path(str(texto["font"]))}}
    return capa


def _spec_dict(body: PreviewRequest, resolution: str, fmt: str = "png",
               output: str = "wallpapers") -> dict:
    """El dict tal cual lo espera `spec.build` (y la CLI vía `--spec`), sin
    normalizar: separado de `_build_spec` para poder devolvérselo al
    frontend como JSON editable/reconstruible (`/api/spec`), no solo para
    armar la `Spec` ya resuelta que necesita `compose`."""
    lado_mayor = max(dimensiones(resolution))
    # `output` se valida aquí pero se guarda tal cual llegó: este dict es
    # también el JSON que se descarga, y una ruta absoluta de esta máquina no
    # le sirve a la CLI en otra. `_build_spec` usa la ya resuelta.
    resolve_sources_path(output)
    sources = [
        _sin_explosion_de_mosaico(_rutas_permitidas(capa.model_dump(exclude_none=True)), lado_mayor)
        for capa in body.layers
    ]
    return {
        "sources": sources,
        "resolutions": [resolution],
        "colors": [body.color],
        "seeds": [body.seed],
        "layout": {"mode": body.layout_mode},
        "defaults": {"recolor": {"mode": body.recolor_mode}},
        "background": body.background if body.background is not None else "auto",
        "finish": body.finish or {},
        "format": fmt,
        "output": output,
    }


def _build_spec(body: PreviewRequest, resolution: str, fmt: str = "png",
                output: str = "wallpapers"):
    datos = _spec_dict(body, resolution, fmt, output)
    return spec_module.build({**datos, "output": resolve_sources_path(output)})


def _render(body: PreviewRequest, resolution: str, fmt: str = "png", output: str = "wallpapers"):
    """Arma la Spec y devuelve (built, imagen). Reusa `prepare()` de la cache
    cuando la geometría (todo salvo color/recolor) ya se calculó antes."""
    built = _build_spec(body, resolution, fmt, output)
    current = compose.plan(built, built.seeds[0])
    key = (geometry_hash(built), built.seeds[0], built.resolutions[0])
    shaped = cache.get(key)
    if shaped is None:
        shaped = compose.prepare(built, current, built.resolutions[0])
        cache.put(key, shaped)
    image = compose.render(built, current, built.resolutions[0], built.colors[0], shaped)
    return built, image


@router.post("/preview")
def preview(body: PreviewRequest) -> Response:
    _, image = _render(body, _resolucion_de_vista_previa(body.resolution))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.post("/spec")
def spec_as_json(body: ExportRequest) -> dict:
    """La spec actual del GUI, tal cual la entendería la CLI con `--spec`:
    para reconstruir el wallpaper actual fuera del GUI, o para guardarlo y
    volver a importarlo después. Valida con `spec.build` (tira SpecError,
    400 en español, si algo no cierra) pero devuelve el dict de antes de
    normalizar, no la Spec ya resuelta: ese es el que tiene sentido a mano
    o para reimportar."""
    data = _spec_dict(body, body.resolution, body.format, body.output)
    spec_module.build(data)
    return data


def _slug(nombre: str) -> str:
    """Nombre de carpeta/archivo seguro a partir del que escribió el
    usuario: minúsculas, todo lo que no sea letra o número se vuelve guión
    bajo, tope de 60 caracteres."""
    limpio = re.sub(r"[^a-z0-9]+", "_", nombre.strip().lower()).strip("_")
    return limpio[:60]


def _wallpaper_paths(body: ExportRequest, built) -> tuple:
    """Carpeta dedicada a este wallpaper dentro de wallpapers/<resolución>/
    (una por export desde el GUI, ver CLAUDE.md) y el nombre base de sus
    archivos adentro: el que puso el usuario, saneado, o
    wp_<color>_<semilla> si lo dejó vacío. Exportar dos veces con el mismo
    nombre pisa esa carpeta a propósito, es la misma composición vuelta a
    guardar."""
    base = _slug(body.name) if body.name else ""
    if not base:
        base = f"wp_{colors.to_hex(built.colors[0])}_{built.seeds[0]}"
    carpeta = naming.resolution_dir(built.output, built.resolutions[0]) / base
    return carpeta, base


@router.post("/export")
def export(body: ExportRequest) -> Response:
    built, image = _render(body, body.resolution, body.format, body.output)
    carpeta, base = _wallpaper_paths(body, built)
    path = carpeta / f"{base}.{built.fmt}"
    compose.save(image, path, built.fmt, built.quality, built.optimize)
    spec_data = _spec_dict(body, body.resolution, body.format, body.output)
    (carpeta / f"{base}.json").write_text(
        json.dumps(spec_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return Response(
        content=path.read_bytes(),
        media_type=_MEDIA_TYPES[built.fmt],
        headers={"X-Export-Path": str(path)},
    )
