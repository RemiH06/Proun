"""Mezcla: todas las temáticas en un mismo collage.

Cada origen entra con un tratamiento distinto para que se distingan sin dejar de
compartir paleta. El archivo científico manda la estructura, las fotos
personales aportan el material, y la normalización tonal hace que convivan.

Es la receta más lenta porque el conjunto de fuentes es grande, pero `layers`
elige un subconjunto por wallpaper, así que cada semilla saca una combinación
distinta.

    python -m recetas.mezcla
"""

from proun.cli import main

from ._comun import BIOFOTOS, CETI, COOL, MASCOTAS, MUSEOS, RADIOGRAFIAS, XRAY_OSCURO

CONFIG = {
    "output": "wallpapers/mezcla",
    "resolutions": ["1920x1080", "2560x1440"],
    "spectrum": {"count": 4, "saturation": 0.4, "value": 0.85},
    "count": 4,
    "seed": 2026,

    "background": "#efeae0",
    "layers": {"min": 5, "max": 8},
    "layout": {"mode": "scatter", "bleed": 0.18, "size": [0.42, 0.9]},
    "finish": {"grain": 0.045, "contrast": 1.05},

    "defaults": {
        "rotate": "random",
        "tones": {"normalize": True, "cutoff": 2},
        "transparent": {"color": "light", "tolerance": 0.0, "softness": 0.55},
        "recolor": {"mode": "duotone", "shadow": "#17151a", "highlight": "#9a8f86"},
        "blend": "multiply",
        "stain": {"amount": 0.35, "scale": 0.35, "edges": 0.45},
    },

    "sources": [
        # Una pieza densa de fondo, para que el papel no quede desnudo.
        {"src": f"{MUSEOS}/wall.JPG", "cover": True, "opacity": 0.22,
         "transparent": None, "stain": {"amount": 0.5, "scale": 0.6}},

        # Radiografías: la estructura. Invertidas para que el esqueleto quede
        # oscuro sobre el papel, y espejadas sobre sí mismas.
        {"src": RADIOGRAFIAS, "tones": XRAY_OSCURO,
         "repeat": {"step": [0.58, 0], "times": 1, "mirror": True,
                    "blend": "multiply"}},

        # Museos: objetos sobre fondo plano, se llevan bien con el keyeado.
        MUSEOS,

        # Bio en foto: naturaleza, textura orgánica.
        {"src": BIOFOTOS, "stain": {"amount": 0.5, "scale": 0.25, "edges": 0.6}},

        # Personales: más suaves, para que no compitan con la estructura.
        {"src": CETI, "opacity": 0.7, "stain": {"amount": 0.6, "edges": 0.7}},
        {"src": MASCOTAS, "opacity": 0.8},
        {"src": COOL, "opacity": 0.75},
    ],
}

if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))