"""Formas de request/response de la API.

Traducen HTTP a los dicts que ya acepta `proun.spec.build`; no revalidan nada
que el motor ya valide, eso lo sigue haciendo `spec.build` y sus mensajes de
error en español llegan tal cual al cliente (ver `main.py`).
"""

from __future__ import annotations

from pydantic import BaseModel


class LayerSpec(BaseModel):
    """Una capa (imagen, figura o texto) con sus propios ajustes.

    Exactamente una de `src`/`shape`/`text` identifica el tipo de capa,
    igual que en el motor (`proun.spec._sources` lo valida). El resto de
    las claves opcionales son las mismas que ya acepta una capa del motor
    (`proun.spec.LAYER_KEYS`); se mandan tal cual, sin reinterpretarlas acá.
    """

    src: str | None = None
    shape: str | dict | None = None
    outline: dict | None = None
    text: str | dict | None = None
    crop: dict | None = None
    resize: dict | None = None
    stain: dict | None = None
    finish: dict | None = None
    rotate: dict | None = None
    opacity: float | None = None
    blend: str | None = None
    color: str | None = None
    repeat: dict | None = None
    mosaic: dict | None = None
    position: list[float] | None = None
    z: float | None = None


class PreviewRequest(BaseModel):
    layers: list[LayerSpec]
    layout_mode: str = "scatter"
    color: str = "#3ba7ff"
    recolor_mode: str = "duotone"
    seed: int = 100_000
    background: dict | str | None = None
    finish: dict | None = None
    # Dimensiones del canvas (mismo aspecto que va a exportarse). La vista
    # previa reusa este valor, solo que achicado, para que el encuadre real
    # se vea desde el primer momento: ver
    # `routes_render._resolucion_de_vista_previa`.
    resolution: str = "1920x1080"


class ExportRequest(PreviewRequest):
    format: str = "png"
    output: str = "wallpapers"


class SourceImage(BaseModel):
    path: str
    name: str


class SourceListResponse(BaseModel):
    path: str
    count: int
    images: list[SourceImage]


class RecolorRequest(BaseModel):
    """Repinta un wallpaper YA exportado (`path`) con un colormap, sin
    reconstruirlo desde sus capas: ver `recolorear.py`."""

    path: str
    name: str = "inferno"
    stops: list[str] | None = None
