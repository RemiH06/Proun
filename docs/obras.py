"""Genera con el motor las obras que cuelgan en docs/index.html.

    python docs/obras.py             (necesita fuentes/, que no se versiona)

Nada de maquetas: cada obra sale de una receta o de un spec con la semilla
fija, así que correrlo de nuevo da los mismos píxeles. Las derivadas
(k-means, planchas de tinta) pasan por `recolorear.recolorear`, la misma
función de la CLI y de la pestaña "recolorear". Cada imagen se guarda en
docs/images/obras/ como WebP en dos anchos (1600 y 800, para `srcset`).
"""

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PIL import Image  # noqa: E402

from proun.cli import main  # noqa: E402
from recetas import alineada, tinta, vitrina  # noqa: E402
from recolorear import recolorear  # noqa: E402

SALIDA = RAIZ / "docs" / "images" / "obras"
ANCHOS = (1600, 800)

# nombre: argumentos de la CLI (con spec) o (CONFIG de una receta, argumentos)
OBRAS = {
    "penrose": ["--spec", "json/penrose.json"],
    "cuatricromia": ["--spec", "json/cuatricromia.json"],
    "campus": ["--spec", "json/campus.json"],
    "reticula": ["--spec", "json/ss4.json"],
    "tinta": (tinta.CONFIG, ["--seeds", "246884557", "--colors", "1c1c1c"]),
    "vitrina": (vitrina.CONFIG, ["--seeds", "959423107", "--colors", "7fb6d9"]),
    "alineada": (alineada.CONFIG, ["--seeds", "246884557", "--colors", "1c1c1c"]),
}

# nombre: (obra de origen, argumentos de recolorear)
DERIVADAS = {
    "vitrina_kmeans": ("vitrina", {"mode": "kmeans", "name": "magma", "colors": 6, "smooth": 3}),
    "campus_kmeans": ("campus", {"mode": "kmeans", "name": "viridis", "colors": 6, "smooth": 3}),
    **{f"plancha_{t}": ("cuatricromia",
                        {"mode": "channels", "channels": {k: [int(k == t), 0] for k in "cmyk"}})
       for t in "cmyk"},
}

# Bases que solo sirven de origen de una derivada: no se exhiben solas.
SIN_EXHIBIR = {"campus"}


def componer(nombre, receta, tmp: Path) -> Image.Image:
    config, args = (None, receta) if isinstance(receta, list) else receta
    destino = tmp / nombre
    codigo = main(config=config, argv=[*args, "--out", str(destino), "--resolutions", "1920x1080",
                                       "--yes", "--quiet", "--overwrite"])
    archivos = sorted(destino.rglob("*.png"))
    if codigo or len(archivos) != 1:
        raise SystemExit(f"{nombre}: se esperaba un solo PNG, salieron {len(archivos)} (código {codigo})")
    return Image.open(archivos[0]).convert("RGB")


def guardar(nombre, imagen: Image.Image):
    for ancho in ANCHOS:
        alto = round(imagen.height * ancho / imagen.width)
        imagen.resize((ancho, alto), Image.LANCZOS).save(
            SALIDA / f"{nombre}-{ancho}.webp", quality=84, method=6)


def run():
    os.chdir(RAIZ)  # las recetas declaran sus fuentes relativas a la raíz
    SALIDA.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        bases = {n: componer(n, r, Path(tmp)) for n, r in OBRAS.items()}
    for nombre, imagen in bases.items():
        if nombre not in SIN_EXHIBIR:
            guardar(nombre, imagen)
    for nombre, (origen, ajustes) in DERIVADAS.items():
        guardar(nombre, recolorear(bases[origen], **ajustes).convert("RGB"))
    print(f"{len(bases) - len(SIN_EXHIBIR) + len(DERIVADAS)} obras en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    run()
