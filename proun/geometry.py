"""Helpers de medidas compartidos por las operaciones.

Convención única en toda la herramienta: los enteros son píxeles y los flotantes
son fracciones de la referencia (el lienzo o la imagen, según el caso).
Así `600` son 600 px y `0.5` es la mitad. Es la razón de que `1` y `1.0`
signifiquen cosas distintas y está documentado en el README.
"""

from __future__ import annotations

from .errors import SpecError

ANCHORS = {
    "center": (0.5, 0.5),
    "top": (0.5, 0.0),
    "bottom": (0.5, 1.0),
    "left": (0.0, 0.5),
    "right": (1.0, 0.5),
    "topleft": (0.0, 0.0),
    "topright": (1.0, 0.0),
    "bottomleft": (0.0, 1.0),
    "bottomright": (1.0, 1.0),
    "random": None,
}


def measure(value, reference: int, *, name: str = "medida", minimum: int = 1) -> int:
    """Convierte un valor px/fracción a píxeles enteros contra `reference`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpecError(f"{name} debe ser un número, llegó {value!r}")
    px = round(value * reference) if isinstance(value, float) else int(value)
    if px < minimum:
        raise SpecError(f"{name} quedó en {px} px, debe ser al menos {minimum}")
    return px


def pair(value, reference: tuple[int, int], *, name: str = "tamaño") -> tuple[int, int]:
    """Igual que `measure` pero para un par [ancho, alto]."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"{name} debe ser [ancho, alto], llegó {value!r}")
    return (
        measure(value[0], reference[0], name=f"{name}[ancho]"),
        measure(value[1], reference[1], name=f"{name}[alto]"),
    )


def anchor_factors(anchor, rng=None) -> tuple[float, float]:
    """Devuelve el par (fx, fy) en 0..1 de un ancla nombrada o explícita."""
    if isinstance(anchor, (list, tuple)) and len(anchor) == 2:
        return (float(anchor[0]), float(anchor[1]))
    key = str(anchor).strip().lower().replace("-", "").replace("_", "")
    if key not in ANCHORS:
        raise SpecError(f"ancla desconocida: {anchor!r}. Opciones: {sorted(ANCHORS)}")
    if key == "random":
        if rng is None:
            raise SpecError("el ancla 'random' necesita un generador aleatorio")
        return (rng.random(), rng.random())
    return ANCHORS[key]


def parse_aspect(value) -> float:
    """Acepta 1.777, "16:9" o "16/9" y devuelve ancho/alto."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        ratio = float(value)
    else:
        text = str(value).replace("/", ":").strip()
        parts = text.split(":")
        if len(parts) != 2:
            raise SpecError(f"proporción inválida: {value!r}. Usa 16:9 o 1.777")
        try:
            ratio = float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            raise SpecError(f"proporción inválida: {value!r}") from None
    if ratio <= 0:
        raise SpecError(f"la proporción debe ser positiva, llegó {ratio}")
    return ratio


def fit_box(size: tuple[int, int], aspect: float) -> tuple[int, int]:
    """El recorte más grande con la proporción pedida que cabe dentro de `size`."""
    w, h = size
    if w / h > aspect:
        return (max(1, round(h * aspect)), h)
    return (w, max(1, round(w / aspect)))


def place_box(
    inner: tuple[int, int], outer: tuple[int, int], factors: tuple[float, float]
) -> tuple[int, int]:
    """Esquina superior izquierda al colocar `inner` dentro de `outer` según el ancla."""
    fx, fy = factors
    return (
        round((outer[0] - inner[0]) * fx),
        round((outer[1] - inner[1]) * fy),
    )