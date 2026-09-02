"""Lista cada imagen en fuentes/ con su tamaño y proporción. Corre desde la
raíz del proyecto: python inspeccionar.py > dimensiones.txt
"""
import pathlib
from PIL import Image

EXT = {".jpg", ".jpeg", ".png", ".JPG", ".PNG", ".webp", ".bmp"}

for p in sorted(pathlib.Path("fuentes").rglob("*")):
    if p.suffix in EXT:
        with Image.open(p) as im:
            w, h = im.size
            print(f"{p}\t{w}x{h}\t{w/h:.3f}")