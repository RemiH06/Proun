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
        # a: fondo, se ajusta al lienzo entero y va detrás de todo
        {
            "src": "fuentes/umifu.tif",
            "cover": True,
            "opacity": 0.35,
            "rotate": None,          # no gira, aunque el default diga random
        },

        # b: recorte 16:9 desde arriba, media pantalla, sin normalizar tonos
        {
            "src": "fuentes/Milkshake.jpg",
            "crop": {"aspect": "16:9", "anchor": "top"},
            "resize": {"size": [0.5, 0.5], "mode": "fill"},
            "tones": False,
            "recolor": {"mode": "tint"},
            "blend": "screen",
        },

        # c: textura chica repetida en tira, en su propio color, entra dos veces
        {
            "src": "fuentes/dresscat.png",
            "mosaic": {"grid": [5, 1], "mirror": True},
            "color": "#ffb347",
            "rotate": [0, 90],
            "opacity": 0.8,
            "repeat": 2,
        },
    ],

    # --- qué se genera ----------------------------------------------------
    "output": "wallpapers",
    "resolutions": ["1920x1080", "2560x1440"],
    "colors": ["#ffffff"],
    # "spectrum": {"count": 6, "saturation": 0.62, "value": 0.9},
    "count": 8,
    "seed": 69,            # fija el lote completo; quítalo para que sea al azar
    # "seeds": [128004006],  # regenera exactamente estos wallpapers
    # "start_index": 1,

    # --- cómo se compone ---------------------------------------------------
    # "layers": {"min": 4, "max": 7},    # cuántas imágenes por collage
    "layout": {
        "mode": "scatter",       # scatter, free, grid, row, column, stack
        "bleed": 0.12,           # cuánto pueden salirse del borde
        "size": [0.38, 0.82],    # fracción del lienzo por capa sin resize propio
    },
    "background": "#ffffff",        # "auto", None, un color, o {"gradient": [...]}
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
#     "tones": {"normalize": True, "gamma": 1.2, "invert": False},
#     "recolor": {"mode": "duotone", "strength": 0.9, "mix_with": "tones"},
#     "color": "#ffb347",  # ignora el color del lote
#     "opacity": 0.8,
#     "blend": "multiply",
#     "position": [0.5, 0.5],
#     "anchor": "center",
#     "repeat": 2,         # cuántas veces entra esta imagen al collage
# }


if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))