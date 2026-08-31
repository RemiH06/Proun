"""Lectura y validación de la especificación.

Toda la validación vive aquí para que el resto del código pueda asumir que lo
que recibe ya tiene sentido. Si algo está mal, se falla temprano y con un
mensaje que dice qué clave es la que está mal.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from . import colors, loading
from .geometry import anchor_factors
from .errors import SpecError

LAYER_KEYS = {
    "src", "crop", "resize", "mosaic", "rotate", "stain", "tones", "transparent",
    "recolor", "color",
    "opacity", "blend", "position", "anchor", "region", "bleed", "copies",
    "repeat", "cover",
}

SPEC_KEYS = {
    "output", "resolutions", "reference", "scale_with_resolution", "colors", "spectrum",
    "count", "seed", "seeds", "format", "quality", "optimize", "start_index", "layers", "layout",
    "background", "finish", "defaults", "sources",
}

FORMATS = frozenset({"png", "jpg", "jpeg", "webp"})


@dataclass(frozen=True)
class Layer:
    """Una imagen del collage con sus ajustes ya fusionados con los generales."""

    src: Path
    crop: object = None
    resize: object = None
    mosaic: object = None
    repeat: object = None
    rotate: object = None
    stain: object = None
    tones: object = True
    transparent: object = None
    recolor: dict = field(default_factory=dict)
    color: object = None
    opacity: float = 1.0
    blend: str = "normal"
    position: object = None
    anchor: str = "center"
    region: object = None
    bleed: object = None
    cover: bool = False


@dataclass(frozen=True)
class Spec:
    sources: tuple[Layer, ...]
    resolutions: tuple[tuple[int, int], ...]
    colors: tuple[tuple[int, int, int], ...]
    seeds: tuple[int, ...]
    output: Path = Path("wallpapers")
    reference: tuple[int, int] | None = None
    scale_with_resolution: bool = True
    fmt: str = "png"
    quality: int = 92
    optimize: bool = False
    start_index: int = 1
    layers: tuple[int, int] | None = None
    layout: dict = field(default_factory=dict)
    background: object = "auto"
    finish: dict = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.seeds) * len(self.resolutions) * len(self.colors)


def load(path) -> dict:
    """Lee un archivo JSON de especificación."""
    file = Path(path).expanduser()
    if not file.is_file():
        raise SpecError(f"no existe el archivo de especificación: {path}")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"JSON inválido en {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError(f"la especificación de {path} debe ser un objeto JSON")
    return _relative_sources(data, file.parent)


def _strip_notes(data: dict) -> dict:
    """Las claves que empiezan con guión bajo son comentarios y se ignoran.

    JSON no tiene comentarios y una especificación larga sin notas se vuelve
    ilegible, así que se reserva ese prefijo.
    """
    return {k: v for k, v in data.items() if not str(k).startswith("_")}


def build(data: dict) -> Spec:
    """Valida el diccionario completo y lo convierte en un `Spec` utilizable."""
    data = _strip_notes(data)
    unknown = set(data) - SPEC_KEYS
    if unknown:
        raise SpecError(f"claves desconocidas en la especificación: {sorted(unknown)}")

    # Ausente significa "usa el default"; presente pero vacío es un error de
    # quien escribió la especificación, y callarlo lo escondería.
    declared = data.get("resolutions")
    resolutions = parse_resolutions(["1920x1080"] if declared is None else declared)
    palette = _palette(data)
    defaults = data.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise SpecError("defaults debe ser un objeto")
    sources = _sources(data.get("sources"), defaults)

    fmt = str(data.get("format", "png")).lower().lstrip(".")
    if fmt not in FORMATS:
        raise SpecError(f"format debe ser uno de {sorted(FORMATS)}, llegó {fmt!r}")
    quality = data.get("quality", 92)
    if not isinstance(quality, int) or isinstance(quality, bool) or not 1 <= quality <= 100:
        raise SpecError(f"quality debe ser un entero entre 1 y 100, llegó {quality!r}")
    start = data.get("start_index", 1)
    if not isinstance(start, int) or isinstance(start, bool) or start < 0:
        raise SpecError(f"start_index debe ser un entero no negativo, llegó {start!r}")

    reference = parse_resolutions([data["reference"]])[0] if data.get("reference") else resolutions[0]

    return Spec(
        sources=sources,
        resolutions=resolutions,
        colors=palette,
        seeds=_seeds(data),
        output=Path(str(data.get("output", "wallpapers"))).expanduser(),
        reference=reference,
        scale_with_resolution=bool(data.get("scale_with_resolution", True)),
        fmt=fmt,
        quality=quality,
        optimize=bool(data.get("optimize", False)),
        start_index=start,
        layers=_layer_range(data.get("layers"), len(sources)),
        layout=data.get("layout") or {},
        background=data.get("background", "auto"),
        finish=data.get("finish") or {},
    )


def _relative_sources(data: dict, base: Path) -> dict:
    """Las rutas del archivo de especificación se resuelven junto a él."""
    def fix(value):
        path = Path(str(value)).expanduser()
        return str(path if path.is_absolute() else base / path)

    out = dict(data)
    if isinstance(out.get("sources"), list):
        fixed = []
        for item in out["sources"]:
            if isinstance(item, str):
                fixed.append(fix(item))
            elif isinstance(item, dict) and "src" in item:
                fixed.append({**item, "src": fix(item["src"])})
            else:
                fixed.append(item)
        out["sources"] = fixed
    return out


def parse_resolutions(value) -> tuple[tuple[int, int], ...]:
    """Normaliza "1920x1080", [1920, 1080] o una lista de ambos."""
    if isinstance(value, (str, tuple)) or (isinstance(value, list) and len(value) == 2
                                           and all(isinstance(v, int) for v in value)):
        value = [value]
    if not isinstance(value, list) or not value:
        raise SpecError(f"resolutions debe ser una lista no vacía, llegó {value!r}")
    out = []
    for item in value:
        if isinstance(item, str):
            parts = item.lower().replace("×", "x").split("x")
            if len(parts) != 2:
                raise SpecError(f"resolución inválida: {item!r}. Usa 1920x1080")
            try:
                size = (int(parts[0]), int(parts[1]))
            except ValueError:
                raise SpecError(f"resolución inválida: {item!r}") from None
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            size = (int(item[0]), int(item[1]))
        else:
            raise SpecError(f"resolución inválida: {item!r}")
        if size[0] < 1 or size[1] < 1:
            raise SpecError(f"resolución sin área: {item!r}")
        if size[0] * size[1] > 100_000_000:
            raise SpecError(f"resolución excesiva: {size[0]}x{size[1]}")
        out.append(size)
    return tuple(dict.fromkeys(out))


def _palette(data: dict) -> tuple[tuple[int, int, int], ...]:
    listed = data.get("colors")
    spectrum = data.get("spectrum")
    if isinstance(listed, list) and not listed:
        raise SpecError("colors está vacío: quítalo para usar el color por defecto")
    out: list = []
    if listed:
        if isinstance(listed, (str, int)):
            listed = [listed]
        if not isinstance(listed, list):
            raise SpecError(f"colors debe ser una lista, llegó {listed!r}")
        out += [colors.parse(c) for c in listed]
    if spectrum:
        if isinstance(spectrum, int) and not isinstance(spectrum, bool):
            spectrum = {"count": spectrum}
        if not isinstance(spectrum, dict):
            raise SpecError(f"spectrum debe ser un entero o un objeto, llegó {spectrum!r}")
        unknown = set(spectrum) - {"count", "saturation", "value", "start", "span"}
        if unknown:
            raise SpecError(f"claves desconocidas en spectrum: {sorted(unknown)}")
        out += colors.spectrum(**spectrum)
    if not out:
        out = [colors.parse("#7aa2f7")]
    return tuple(dict.fromkeys(out))


def _seeds(data: dict) -> tuple[int, ...]:
    listed = data.get("seeds")
    if listed:
        if isinstance(listed, int) and not isinstance(listed, bool):
            listed = [listed]
        if not isinstance(listed, list) or not all(
            isinstance(s, int) and not isinstance(s, bool) and s >= 0 for s in listed
        ):
            raise SpecError(f"seeds debe ser una lista de enteros no negativos, llegó {listed!r}")
        return tuple(listed)

    count = data.get("count", 1)
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise SpecError(f"count debe ser un entero positivo, llegó {count!r}")
    base = data.get("seed")
    if base is not None and (isinstance(base, bool) or not isinstance(base, int)):
        raise SpecError(f"seed debe ser un entero, llegó {base!r}")
    master = random.Random(base)
    return tuple(master.randrange(100_000, 999_999_999) for _ in range(count))


def _layer_range(value, available: int) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        value = {"min": value, "max": value}
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        value = {"min": value[0], "max": value[1]}
    if not isinstance(value, dict):
        raise SpecError(f"layers debe ser un entero, un par o un objeto, llegó {value!r}")
    unknown = set(value) - {"min", "max"}
    if unknown:
        raise SpecError(f"claves desconocidas en layers: {sorted(unknown)}")
    low = value.get("min", 1)
    high = value.get("max", available)
    for name, v in (("min", low), ("max", high)):
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise SpecError(f"layers.{name} debe ser un entero positivo, llegó {v!r}")
    if low > high:
        raise SpecError(f"layers.min ({low}) no puede superar a layers.max ({high})")
    return (low, high)


def _region(value):
    """Rectángulo del lienzo donde puede caer el centro de una capa.

    [x0, y0, x1, y1] en fracciones, o un ancla nombrada, que equivale al noveno
    correspondiente del lienzo.
    """
    if value is None:
        return None
    if isinstance(value, str):
        fx, fy = anchor_factors(value)
        return (max(0.0, fx - 1 / 6), max(0.0, fy - 1 / 6),
                min(1.0, fx + 1 / 6), min(1.0, fy + 1 / 6))
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise SpecError(f"region debe ser [x0, y0, x1, y1] o un ancla, llegó {value!r}")
    valores = []
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1:
            raise SpecError(f"region va en fracciones de 0 a 1, llegó {v!r}")
        valores.append(float(v))
    x0, y0, x1, y1 = valores
    if x0 >= x1 or y0 >= y1:
        raise SpecError(f"region sin área: {value!r}")
    return (x0, y0, x1, y1)


def _bleed(value):
    """Cuánto puede salirse la capa del lienzo, en fracción de su propio tamaño."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = [value, value]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"bleed debe ser un número o un par [x, y], llegó {value!r}")
    salida = []
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1:
            raise SpecError(f"bleed va de 0 (nada afuera) a 1 (todo afuera), llegó {v!r}")
        salida.append(float(v))
    return (salida[0], salida[1])


def _sources(value, defaults: dict) -> tuple[Layer, ...]:
    if not value:
        raise SpecError("hace falta al menos una imagen en sources")
    if isinstance(value, (str, dict)):
        value = [value]
    if not isinstance(value, list):
        raise SpecError(f"sources debe ser una lista, llegó {value!r}")

    layers: list[Layer] = []
    for item in value:
        entry = {"src": item} if isinstance(item, str) else item
        if not isinstance(entry, dict):
            raise SpecError(f"cada entrada de sources debe ser una ruta o un objeto: {item!r}")
        entry = _strip_notes(entry)
        unknown = set(entry) - LAYER_KEYS
        if unknown:
            raise SpecError(f"claves desconocidas en una imagen: {sorted(unknown)}")
        if "src" not in entry:
            raise SpecError(f"a esta imagen le falta 'src': {entry!r}")

        paths = loading.expand(entry["src"])
        if not paths:
            raise SpecError(f"ningún archivo coincide con {entry['src']!r}")
        merged = {**defaults, **{k: v for k, v in entry.items() if k != "src"}}
        copies = merged.pop("copies", 1)
        if not isinstance(copies, int) or isinstance(copies, bool) or not 1 <= copies <= 500:
            raise SpecError(f"copies debe ser un entero entre 1 y 500, llegó {copies!r}")

        cover = merged.pop("cover", False)
        if not isinstance(cover, bool):
            raise SpecError(f"cover debe ser true o false, llegó {cover!r}")
        if cover:
            choca = {"resize", "position"} & set(merged)
            if choca:
                raise SpecError(
                    f"una capa con cover se ajusta sola al lienzo, así que no admite "
                    f"{sorted(choca)}"
                )

        recolor = merged.pop("recolor", {})
        if not isinstance(recolor, dict):
            raise SpecError(f"recolor debe ser un objeto, llegó {recolor!r}")
        opacity = merged.pop("opacity", 1.0)
        if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) \
                or not 0 <= opacity <= 1:
            raise SpecError(f"opacity debe estar entre 0 y 1, llegó {opacity!r}")

        for path in paths:
            for _ in range(copies):
                layers.append(Layer(
                    src=path,
                    crop=merged.get("crop"),
                    resize=merged.get("resize"),
                    mosaic=merged.get("mosaic"),
                    repeat=merged.get("repeat"),
                    rotate=merged.get("rotate"),
                    stain=merged.get("stain"),
                    tones=merged.get("tones", True),
                    transparent=merged.get("transparent"),
                    recolor=dict(recolor),
                    color=merged.get("color"),
                    opacity=float(opacity),
                    blend=str(merged.get("blend", "normal")),
                    position=merged.get("position"),
                    anchor=merged.get("anchor", "center"),
                    region=_region(merged.get("region")),
                    bleed=_bleed(merged.get("bleed")),
                    cover=cover,
                ))
    return tuple(layers)