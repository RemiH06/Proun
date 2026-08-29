"""Acabados sobre el wallpaper ya compuesto.

Formas aceptadas en `finish`:
    {"vignette": 0.35, "grain": 0.04, "blur": 0, "contrast": 1.1,
     "brightness": 1.0, "saturation": 1.0, "overlay": {"color": "auto", "opacity": 0.1,
     "mode": "soft_light"}}
Todo es opcional; lo que no se declara no se aplica.
"""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter

from .. import colors
from ..errors import SpecError
from .blend import composite

_KEYS = {"vignette", "grain", "blur", "contrast", "brightness", "saturation", "overlay"}


def apply(im: Image.Image, main, spec=None, rng=None) -> Image.Image:
    if not spec:
        return im
    if not isinstance(spec, dict):
        raise SpecError(f"finish debe ser un objeto, llegó {spec!r}")
    unknown = set(spec) - _KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en finish: {sorted(unknown)}")

    # `composite` muta el lienzo que recibe, así que overlay y grain
    # ensuciarían la imagen de quien llama. Una copia por wallpaper no se nota
    # al lado de lo que cuesta comprimir el PNG.
    im = im.copy()

    blur = spec.get("blur")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(_number(blur, "finish.blur", 0, 200)))

    for key, enhancer in (
        ("brightness", ImageEnhance.Brightness),
        ("contrast", ImageEnhance.Contrast),
        ("saturation", ImageEnhance.Color),
    ):
        if key in spec:
            im = enhancer(im).enhance(_number(spec[key], f"finish.{key}", 0, 10))

    overlay = spec.get("overlay")
    if overlay:
        if not isinstance(overlay, dict):
            raise SpecError(f"finish.overlay debe ser un objeto, llegó {overlay!r}")
        raw = overlay.get("color", "auto")
        tone = colors.shade(main, 1.0) if raw == "auto" else colors.parse(raw)
        veil = Image.new("RGBA", im.size, tone + (255,))
        im = composite(im, veil, (0, 0),
                       mode=overlay.get("mode", "soft_light"),
                       opacity=_number(overlay.get("opacity", 0.15), "finish.overlay.opacity", 0, 1))

    vignette = spec.get("vignette")
    if vignette:
        strength = _number(vignette, "finish.vignette", 0, 1)
        mask = Image.radial_gradient("L").resize(im.size, Image.Resampling.BILINEAR)
        mask = mask.point(lambda v: round(v * strength))
        dark = Image.new("RGBA", im.size, (0, 0, 0, 255))
        im = Image.composite(dark, im, mask).convert("RGBA")

    grain = spec.get("grain")
    if grain:
        im = composite(im, _noise(im.size, _number(grain, "finish.grain", 0, 1), rng),
                       (0, 0), mode="overlay", opacity=_number(grain, "finish.grain", 0, 1))

    return im


def _noise(size, amount: float, rng) -> Image.Image:
    """Ruido reproducible a partir del generador que se reciba.

    `Image.effect_noise` de Pillow no acepta semilla y da algo distinto en cada
    corrida, así que rompería la promesa de que el nombre del archivo permite
    regenerarlo. Se arma con randbytes, que sí es determinista y es igual de
    rápido: unos 100 ms para un 4K completo.
    """
    if rng is None:
        raise SpecError(
            "finish.grain necesita un generador aleatorio para ser reproducible; "
            "pásale un random.Random con la semilla del wallpaper"
        )
    ancho, alto = size
    plano = Image.frombytes("L", size, rng.randbytes(ancho * alto))
    # El ruido crudo va de 0 a 255 y taparía la imagen: se comprime alrededor
    # del gris medio, que es el neutro del modo overlay.
    spread = 0.15 + 0.85 * amount
    return plano.point(
        [min(255, max(0, round(128 + (i - 128) * spread))) for i in range(256)]
    ).convert("RGBA")


def _number(value, name, low, high) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise SpecError(f"{name} debe estar entre {low} y {high}, llegó {value!r}")
    return float(value)