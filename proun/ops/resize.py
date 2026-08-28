"""Redimensionado de una capa.

Formas aceptadas en `resize`:
    0.5                          escala relativa al tamaño propio
    [1200, 300]                  destino explícito
    {"size": [0.5, 0.5]}         mitad del lienzo (flotantes = fracción del lienzo)
    {"scale": 2}                 el doble de su tamaño original
    {"size": [w, h], "keep_aspect": false}   deforma para llenar exacto
    {"size": [w, h], "mode": "fill"}         cubre y recorta el sobrante
    {"max_side": 800}            limita el lado mayor sin deformar
    {"size": [w, h], "shrink_only": true}    nunca agranda, solo reduce

modes:
    fit     (por defecto) cabe completa dentro del destino, conserva proporción
    fill    cubre el destino y recorta el excedente, conserva proporción
    stretch deforma hasta el destino exacto
`keep_aspect: false` es un atajo de `mode: "stretch"`.
"""

from __future__ import annotations

from PIL import Image

from ..errors import SpecError
from ..geometry import anchor_factors, measure, pair, place_box

RESAMPLE = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}

MODES = ("fit", "fill", "stretch")


def apply(im: Image.Image, spec, canvas: tuple[int, int], rng=None) -> Image.Image:
    if spec in (None, False):
        return im
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        spec = {"scale": spec}
    elif isinstance(spec, (list, tuple)):
        spec = {"size": list(spec)}
    if not isinstance(spec, dict):
        raise SpecError(f"resize debe ser un número, un par o un objeto, llegó {spec!r}")

    unknown = set(spec) - {
        "size", "scale", "max_side", "keep_aspect", "mode", "anchor", "resample", "shrink_only",
    }
    if unknown:
        raise SpecError(f"claves desconocidas en resize: {sorted(unknown)}")

    mode = str(spec.get("mode", "fit" if spec.get("keep_aspect", True) else "stretch")).lower()
    if mode not in MODES:
        raise SpecError(f"resize.mode debe ser uno de {MODES}, llegó {mode!r}")
    filt = RESAMPLE.get(str(spec.get("resample", "lanczos")).lower())
    if filt is None:
        raise SpecError(f"resample debe ser uno de {sorted(RESAMPLE)}")

    targets = {"size", "scale", "max_side"} & set(spec)
    if not targets:
        raise SpecError("resize necesita size, scale o max_side")
    if len(targets) > 1:
        raise SpecError(
            f"resize admite solo uno de size, scale o max_side: llegaron {sorted(targets)}"
        )

    if "size" in spec:
        target = pair(spec["size"], canvas, name="resize.size")
    elif "scale" in spec:
        factor = spec["scale"]
        if not isinstance(factor, (int, float)) or isinstance(factor, bool) or factor <= 0:
            raise SpecError(f"resize.scale debe ser un número positivo, llegó {factor!r}")
        target = (max(1, round(im.width * factor)), max(1, round(im.height * factor)))
        mode = "stretch"
    elif "max_side" in spec:
        limit = measure(spec["max_side"], max(canvas), name="resize.max_side")
        longest = max(im.size)
        if longest <= limit:
            return im
        factor = limit / longest
        target = (max(1, round(im.width * factor)), max(1, round(im.height * factor)))
        mode = "stretch"

    if target == im.size:
        return im
    if mode == "stretch":
        return im.resize(target, filt)
    if mode == "fit":
        factor = min(target[0] / im.width, target[1] / im.height)
        if spec.get("shrink_only", False):
            factor = min(factor, 1.0)
        return im.resize(
            (max(1, round(im.width * factor)), max(1, round(im.height * factor))), filt
        )
    factor = max(target[0] / im.width, target[1] / im.height)
    grown = im.resize((max(target[0], round(im.width * factor)),
                       max(target[1], round(im.height * factor))), filt)
    x, y = place_box(target, grown.size, anchor_factors(spec.get("anchor", "center"), rng))
    return grown.crop((x, y, x + target[0], y + target[1]))