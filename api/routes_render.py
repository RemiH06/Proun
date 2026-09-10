"""Rutas para generar el collage: preview de baja resolución y export final.

Todo el trabajo real ya existe en `proun.spec`/`proun.compose`; estas rutas
solo arman el dict que `spec.build` acepta y devuelven la imagen resultante.
"""

from __future__ import annotations

import io

from fastapi import APIRouter
from fastapi.responses import Response

from proun import colors, compose, naming
from proun import spec as spec_module

from .cache import cache, geometry_hash
from .schemas import ExportRequest, PreviewRequest

router = APIRouter()

PREVIEW_RESOLUTION = "480x270"

_MEDIA_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp"}


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


def _build_spec(body: PreviewRequest, resolution: str, fmt: str = "png",
                output: str = "wallpapers"):
    lado_mayor = max(spec_module.parse_resolutions([resolution])[0])
    sources = [
        _sin_explosion_de_mosaico(img.model_dump(exclude_none=True), lado_mayor)
        for img in body.images
    ]
    data = {
        "sources": sources,
        "resolutions": [resolution],
        "colors": [body.color],
        "seeds": [body.seed],
        "layout": {"mode": body.layout_mode},
        "defaults": {"recolor": {"mode": body.recolor_mode}},
        "format": fmt,
        "output": output,
    }
    return spec_module.build(data)


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
    _, image = _render(body, PREVIEW_RESOLUTION)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.post("/export")
def export(body: ExportRequest) -> Response:
    built, image = _render(body, body.resolution, body.format, body.output)
    color_hex = colors.to_hex(built.colors[0])
    name = naming.filename(1, color_hex, built.seeds[0], built.fmt, naming.content_hash(built))
    path = naming.resolution_dir(built.output, built.resolutions[0]) / name
    compose.save(image, path, built.fmt, built.quality, built.optimize)
    return Response(
        content=path.read_bytes(),
        media_type=_MEDIA_TYPES[built.fmt],
        headers={"X-Export-Path": str(path)},
    )
