"""Vuelve a colorear un wallpaper ya exportado con un colormap de varios
colores (inferno y similares), sin reconstruirlo desde sus capas
originales: recupera el tono de cada píxel (blanco a negro) y lo vuelve a
mapear con proun.ops.recolor en modo "colormap". Corre desde la raíz del
proyecto:

    python recolorear.py wallpapers/1920x1080/wp_0001_3ba7ff_123456.png
    python recolorear.py wallpapers/1920x1080/wp_0001_3ba7ff_123456.png --name inferno
    python recolorear.py foto.png --stops "#000814" "#ffd60a" --out foto_sol.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from proun.errors import SpecError
from proun.ops import recolor

# Sin color principal de verdad: el modo "colormap" lo ignora, pero
# recolor.apply lo pide igual (lo usan los demás modos).
_SIN_USAR = "#000000"


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="recolorear",
        description='Repinta un wallpaper ya exportado con un colormap (recolor.py, modo "colormap").',
    )
    p.add_argument("imagen", help="ruta al PNG/JPG ya exportado")
    p.add_argument("--name", default="inferno",
                    help='colormap con nombre (ver proun.ops.recolor.COLORMAPS), por defecto "inferno"')
    p.add_argument("--stops", nargs="+", metavar="HEX",
                    help="en vez de --name, una lista propia de colores para el degradado")
    p.add_argument("--out", metavar="RUTA",
                    help="archivo de salida (por defecto, el mismo nombre con el colormap como sufijo)")
    return p.parse_args(argv)


def recolorear(imagen: Image.Image, *, name: str = "inferno", stops=None) -> Image.Image:
    spec: dict = {"mode": "colormap"}
    if stops:
        spec["stops"] = list(stops)
    else:
        spec["name"] = name
    return recolor.apply(imagen.convert("RGBA"), _SIN_USAR, spec)


def main(argv=None) -> int:
    args = parse_args(argv)
    origen = Path(args.imagen)
    try:
        with Image.open(origen) as im:
            salida = recolorear(im, name=args.name, stops=args.stops)
    except FileNotFoundError:
        print(f"error: no existe {origen}", file=sys.stderr)
        return 2
    except SpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    sufijo = "personalizado" if args.stops else args.name
    destino = Path(args.out) if args.out else origen.with_stem(f"{origen.stem}_{sufijo}")
    salida.convert("RGB").save(destino)
    print(f"guardado {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
