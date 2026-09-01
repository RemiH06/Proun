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
        "mode": "scatter",       # scatter, free, grid, row, column, stack, align
        "bleed": 0.12,           # cuánto pueden salirse del borde (no aplica a align)
        "size": [0.38, 0.82],    # fracción del lienzo por capa sin resize propio
        # "width": 0.92,         # solo align: ancho del bloque, fracción del lienzo
        # "gap": 2,              # solo align: separación entre piezas, en píxeles
        # "anchor": "center",    # solo align: top, center o bottom
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


# Una capa con todos sus ajustes, por si hace falta copiarla a "sources":
#
# {
#     "src": "fuentes/textura.png",
#     "cover": False,      # True la estira al lienzo entero y la manda al fondo
#     "crop": {"aspect": "16:9", "anchor": "top"},
#     "resize": {"size": [0.5, 0.5], "mode": "fill"},
#     "mosaic": {"grid": [4, 1], "mirror": True},
#     "rotate": {"range": [-6, 6], "step": 3},
#     "stain": {"amount": 0.6, "scale": 0.3, "edges": 0.8, "threshold": 0.4},
#     "tones": {"normalize": True, "gamma": 1.2, "invert": False},
#     "transparent": {"color": "light", "tolerance": 0, "softness": 1},
#     "recolor": {"mode": "duotone", "strength": 0.9, "mix_with": "tones"},
#     "color": "#ffb347",  # ignora el color del lote
#     "opacity": 0.8,
#     "blend": "multiply",
#     "position": [0.5, 0.5],   # posición exacta; manda sobre region
#     "anchor": "center",
#     "region": [0.5, 0, 1, 0.5],   # o "topright": dónde puede caer al azar
#     "bleed": 0.15,       # cuánto puede salirse, en fracción de su tamaño
#     "color": ["#ff0000", "#3ba7ff"],   # sortea uno por wallpaper
#     "repeat": {"step": [0.5, 0], "times": 2, "mirror": True},
#     "copies": 2,         # cuántas veces entra esta imagen al collage
# }


# Tinta sobre papel, el registro del fondo de referencia: el lienzo es claro,
# el extremo claro de cada imagen desaparece y solo lo oscuro se acumula al
# solaparse. No es un preset, son cuatro claves en "defaults":
#
# "background": "#f4f1ea",
# "defaults": {
#     "tones": True,
#     "transparent": {"color": "light", "tolerance": 0.05, "softness": 0.9},
#     "recolor": {"mode": "duotone", "shadow": "#111111", "highlight": "#777777"},
#     "blend": "multiply",
# },
#
# Para la polaridad contraria, tinta clara sobre fondo oscuro, basta cambiar
# "light" por "dark", el fondo por uno oscuro y el blend por "screen".


if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))