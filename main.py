#!/usr/bin/env python3
"""Punto de entrada de Proun.

Se puede usar de dos maneras, y se pueden combinar:

1. Editando CONFIG aquí abajo y corriendo `python main.py`.
2. Con banderas: `python main.py --images fuentes/ --spectrum 6 --count 4`.

Las banderas pisan lo que diga CONFIG, así que aquí puede vivir la
configuración estable del proyecto y variarse lo puntual desde la terminal:

    python main.py --resolutions 3840x2160 --seeds 128004006

Las claves comentadas son opcionales y muestran su valor por defecto.
"""

from proun.cli import main

CONFIG = {
    # --- de dónde salen las imágenes --------------------------------------
    # Rutas, directorios o globs. Una entrada puede ser texto o un objeto con
    # ajustes propios; lo que ponga la capa gana sobre "defaults".
    "sources": [
        "fuentes/",
    ],

    # --- qué se genera ----------------------------------------------------
    "output": "wallpapers",
    "resolutions": ["1920x1080", "2560x1440"],
    "colors": ["#3ba7ff"],
    # "spectrum": {"count": 6, "saturation": 0.62, "value": 0.9},
    "count": 4,
    "seed": 2026,            # fija el lote completo; quítalo para que sea al azar
    # "seeds": [128004006],  # regenera exactamente estos wallpapers
    # "start_index": 1,

    # --- cómo se compone ---------------------------------------------------
    # "layers": {"min": 4, "max": 7},    # cuántas imágenes por collage
    "layout": {
        "mode": "scatter",       # scatter, free, grid, row, column, stack
        "bleed": 0.12,           # cuánto pueden salirse del borde
        "size": [0.38, 0.82],    # fracción del lienzo por capa sin resize propio
    },
    "background": "auto",        # "auto", None, un color, o {"gradient": [...]}
    # "finish": {"vignette": 0.3, "grain": 0.05, "contrast": 1.05},

    # --- ajustes que heredan todas las capas -------------------------------
    "defaults": {
        "rotate": "random",               # múltiplos de 90
        "tones": True,                    # normalización tonal
        "recolor": {"mode": "duotone"},   # duotone, tint, screen, hue, channels, none
    },

    # --- archivo de salida -------------------------------------------------
    # "format": "png",      # png, jpg, webp
    # "quality": 92,        # solo jpg y webp
    # "optimize": False,    # pesa poco menos y tarda mucho más
    # "reference": "1920x1080",
    # "scale_with_resolution": True,
}


# Una figura geométrica en vez de una foto: sin "src", con "shape". Sale en
# escala de grises y hereda el mismo recolor que las fotos, así que acompaña
# el color del lote (o su propia lista de colores) automáticamente.
#
# {
#     "shape": "circle",              # rect, circle, triangle, diamond, polygon
#     # "shape": {"kind": "polygon", "sides": 6},
#     "outline": {"inset": 0.12, "width": 0.03},  # el contorno vive hacia adentro
#     "color": ["#e0504a", "#4a9de0", "#e0c24a"],  # sortea uno por wallpaper
#     "opacity": 0.55,
#     "blend": "screen",
#     "resize": {"size": [0.3, 0.3]},
#     "rate": 0.7,      # probabilidad de aparecer en un wallpaper dado
#     "overlap": 0.15,  # máximo solape permitido contra otras capas con overlap
#     "copies": 4,
# }

# Un texto en vez de una foto o una figura: sin "src" ni "shape", con "text".
# Igual que las figuras, sale en escala de grises y hereda el recolor del
# lote. La fuente viene empaquetada (Big Shoulders, OFL) y cubre acentos,
# diéresis y ñ; para otro alfabeto hay que dar una ruta propia con "font".
#
# {
#     "text": "PROUN",                     # o una lista: sortea una por wallpaper
#     "text": {
#         "text": ["PROUN", "1926", "CONSTRUCTIVISMO"],
#         "weight": "bold",                # bold o regular; ignorado si hay "font"
#         # "font": "C:/ruta/a/una.ttf",
#         "align": "center",                # left, center, right
#         "wrap": 0.6,                      # ancho antes de saltar de línea; sin
#                                            # esto, todo en una sola línea
#         "line_spacing": 1.15,
#         "outline": {"width": 0.04},       # se traza en el borde real del glifo,
#     },                                    # no hacia adentro como en las figuras
#     "color": ["#e0504a", "#4a9de0"],
#     "opacity": 0.9,
#     "rate": 0.7,
# }

# Una capa con todos sus ajustes, por si hace falta copiarla a "sources":
#
# {
#     "src": "fuentes/textura.png",
#     "cover": False,      # True la estira al lienzo entero y la manda al fondo
#     "crop": {"aspect": "16:9", "anchor": "top"},
#     "resize": {"size": [0.5, 0.5], "mode": "fill"},
#     "mosaic": {"grid": [4, 1], "mirror": True},
#     "rotate": {"range": [-6, 6], "step": 3},
#     "tones": {"normalize": True, "gamma": 1.2, "invert": False},
#     "recolor": {"mode": "duotone", "strength": 0.9, "mix_with": "tones"},
#     "color": "#ffb347",  # ignora el color del lote
#     "opacity": 0.8,
#     "blend": "multiply",
#     "position": [0.5, 0.5],
#     "anchor": "center",
#     "repeat": {"step": [0.5, 0], "times": 2, "mirror": True},
#     "copies": 2,         # cuántas veces entra esta imagen al collage
# }


if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))