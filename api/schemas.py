"""Formas de request/response de la API.

Traducen HTTP a los dicts que ya acepta `proun.spec.build`; no revalidan nada
que el motor ya valide, eso lo sigue haciendo `spec.build` y sus mensajes de
error en español llegan tal cual al cliente (ver `main.py`).
"""

from __future__ import annotations

from pydantic import BaseModel


class ImageLayer(BaseModel):
    """Una imagen elegida a mano, con sus propios ajustes de capa.

    Las claves opcionales son las mismas que ya acepta una capa del motor
    (`proun.spec.LAYER_KEYS`); se mandan tal cual, sin reinterpretarlas acá.
    """

    src: str
    rotate: dict | None = None
    opacity: float | None = None
    blend: str | None = None
    color: str | None = None
    repeat: dict | None = None
    mosaic: dict | None = None


class PreviewRequest(BaseModel):
    images: list[ImageLayer]
    layout_mode: str = "scatter"
    color: str = "#3ba7ff"
    recolor_mode: str = "duotone"
    seed: int = 100_000


class ExportRequest(PreviewRequest):
    resolution: str = "1920x1080"
    format: str = "png"
    output: str = "wallpapers"


class SourceImage(BaseModel):
    path: str
    name: str


class SourceListResponse(BaseModel):
    path: str
    count: int
    images: list[SourceImage]
