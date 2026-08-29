"""Línea de comandos: junta todo y escribe en el directorio de salida.

Se puede trabajar solo con banderas, solo con un archivo de especificación o con
los dos: lo que llegue por bandera pisa lo que diga el archivo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import colors, compose, naming, spec as spec_module
from .errors import SpecError


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="proun",
        description="Genera wallpapers tipo collage con la paleta normalizada.",
        epilog="Ejemplo: proun --images fotos/ --resolutions 1920x1080 3840x2160 "
               "--spectrum 6 --count 4",
    )
    p.add_argument("--spec", help="archivo JSON con la especificación completa")
    p.add_argument("--images", nargs="+", metavar="RUTA",
                   help="archivos, directorios o globs con las imágenes de origen")
    p.add_argument("--out", metavar="DIR", help="directorio de salida (por defecto wallpapers)")
    p.add_argument("--resolutions", nargs="+", metavar="WxH",
                   help="una carpeta por cada resolución, por ejemplo 1920x1080")
    p.add_argument("--colors", nargs="+", metavar="HEX", help="colores principales, por ejemplo 3ba7ff")
    p.add_argument("--spectrum", type=int, metavar="N",
                   help="genera N colores repartidos por el círculo cromático")
    p.add_argument("--count", type=int, help="cuántas composiciones distintas generar")
    p.add_argument("--seed", type=int, help="semilla maestra: fija el lote completo")
    p.add_argument("--seeds", nargs="+", type=int, metavar="N",
                   help="semillas exactas a regenerar, tal como aparecen en el nombre del archivo")
    p.add_argument("--layers", metavar="N|MIN-MAX",
                   help="cuántas imágenes entran en cada collage (por defecto todas)")
    p.add_argument("--layout", choices=("scatter", "free", "grid", "row", "column", "stack"),
                   help="cómo se reparten las capas")
    p.add_argument("--mode", metavar="MODO",
                   help="modo de recoloreado: duotone, tint, screen, hue, channels, none")
    p.add_argument("--strength", type=float, metavar="0..1",
                   help="cuánto pesa el recoloreado frente a los tonos normalizados")
    p.add_argument("--no-tones", action="store_true",
                   help="no normalizar el rango tonal: cada imagen conserva su contraste")
    p.add_argument("--background", metavar="COLOR", help="'auto', 'none' o un color sólido")
    p.add_argument("--format", choices=("png", "jpg", "webp"), help="formato de salida")
    p.add_argument("--quality", type=int, metavar="1..100", help="calidad para jpg y webp")
    p.add_argument("--optimize", action="store_true",
                   help="recomprime al guardar: pesa un poco menos y tarda bastante más")
    p.add_argument("--start-index", type=int, metavar="N", help="número inicial del contador ####")
    p.add_argument("--no-scale", action="store_true",
                   help="no reescalar las medidas al cambiar de resolución")
    p.add_argument("--overwrite", action="store_true", help="sobrescribir archivos existentes")
    p.add_argument("--dry-run", action="store_true", help="solo listar lo que se generaría")
    p.add_argument("--quiet", action="store_true", help="no imprimir cada archivo")
    return p.parse_args(argv)


def to_data(args: argparse.Namespace) -> dict:
    """Fusiona el archivo de especificación con las banderas."""
    data = spec_module.load(args.spec) if args.spec else {}

    if args.images:
        data["sources"] = list(args.images)
    if args.out:
        data["output"] = args.out
    if args.resolutions:
        data["resolutions"] = args.resolutions
    if args.colors:
        data["colors"] = args.colors
    if args.spectrum:
        data["spectrum"] = args.spectrum
    if args.count:
        data["count"] = args.count
        data.pop("seeds", None)
    if args.seed is not None:
        data["seed"] = args.seed
        data.pop("seeds", None)
    if args.seeds:
        data["seeds"] = args.seeds
    if args.layers:
        data["layers"] = _layers(args.layers)
    if args.layout:
        data["layout"] = {**(data.get("layout") or {}), "mode": args.layout}
    if args.background:
        data["background"] = None if args.background.lower() == "none" else args.background
    if args.format:
        data["format"] = args.format
    if args.quality:
        data["quality"] = args.quality
    if args.optimize:
        data["optimize"] = True
    if args.start_index is not None:
        data["start_index"] = args.start_index
    if args.no_scale:
        data["scale_with_resolution"] = False

    if args.mode or args.strength is not None or args.no_tones:
        defaults = dict(data.get("defaults") or {})
        recolor = dict(defaults.get("recolor") or {})
        if args.mode:
            recolor["mode"] = args.mode
        if args.strength is not None:
            recolor["strength"] = args.strength
        if recolor:
            defaults["recolor"] = recolor
        if args.no_tones:
            defaults["tones"] = False
        data["defaults"] = defaults

    if not data.get("sources"):
        raise SpecError("hacen falta imágenes: usa --images o un --spec con 'sources'")
    return data


def run(config: spec_module.Spec, *, overwrite=False, dry_run=False, quiet=False) -> list[Path]:
    written: list[Path] = []
    for offset, seed in enumerate(config.seeds):
        index = config.start_index + offset
        current = compose.plan(config, seed)
        for resolution in config.resolutions:
            folder = naming.resolution_dir(config.output, resolution)
            shaped = None
            for color in config.colors:
                name = naming.filename(index, colors.to_hex(color), seed, config.fmt)
                path = folder / name
                if path.exists() and not overwrite:
                    if not quiet:
                        print(f"  omitido (ya existe) {path}")
                    continue
                if dry_run:
                    if not quiet:
                        print(f"  {path}")
                    written.append(path)
                    continue
                if shaped is None:
                    shaped = compose.prepare(config, current, resolution)
                image = compose.render(config, current, resolution, color, shaped)
                compose.save(image, path, config.fmt, config.quality, config.optimize)
                written.append(path)
                if not quiet:
                    print(f"  {path}")
    return written


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        config = spec_module.build(to_data(args))
        if not args.quiet:
            print(
                f"{len(config.sources)} imágenes, {len(config.seeds)} composiciones, "
                f"{len(config.resolutions)} resoluciones, {len(config.colors)} colores "
                f"= {config.total} archivos en {config.output}/"
            )
        written = run(config, overwrite=args.overwrite, dry_run=args.dry_run, quiet=args.quiet)
    except SpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\ninterrumpido", file=sys.stderr)
        return 130
    if not args.quiet:
        verbo = "se generarían" if args.dry_run else "generados"
        print(f"{len(written)} archivos {verbo}")
    return 0


def _layers(value: str):
    text = value.strip()
    if "-" in text:
        low, _, high = text.partition("-")
        try:
            return {"min": int(low), "max": int(high)}
        except ValueError:
            raise SpecError(f"--layers inválido: {value!r}. Usa 5 o 3-8") from None
    try:
        return int(text)
    except ValueError:
        raise SpecError(f"--layers inválido: {value!r}. Usa 5 o 3-8") from None