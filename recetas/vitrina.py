"""Vitrina: el registro de radiografía, luz sobre oscuridad.

La polaridad contraria a la receta de tinta. El fondo es oscuro, el extremo
oscuro de cada foto desaparece y lo que brilla se acumula con `screen`. Es la
receta para las piezas densas y para el material de archivo.

    python -m recetas.vitrina
"""

from proun.cli import main

from ._comun import HUESOS, MUSEOS, OSCURAS, RADIOGRAFIAS, XRAY_CLARO

CONFIG = {
    "output": "wallpapers/vitrina",
    "resolutions": ["1920x1080", "2560x1440"],
    "colors": ["#7fb6d9", "#a8c7b0", "#d9c48f", "#c9a7c7"],
    "count": 4,
    "seed": 1930,

    "background": {"gradient": ["#0b0d10", "#161a20"], "direction": "radial"},
    "layers": {"min": 5, "max": 9},
    "layout": {"mode": "scatter", "bleed": 0.18, "size": [0.35, 0.8]},
    "finish": {"vignette": 0.35, "grain": 0.05, "contrast": 1.15},

    "defaults": {
        "rotate": "random",
        "tones": {"normalize": True, "cutoff": 1, "gamma": 1.6},
        "transparent": {"color": "dark", "tolerance": 0.22, "softness": 0.45},
        "recolor": {"mode": "duotone", "shadow": "#0d1014", "highlight": "#ffffff"},
        "blend": "screen",
        "stain": {"amount": 0.45, "scale": 0.35, "edges": 0.6},
    },

    "sources": [
        # Las radiografías entran tal cual: ya son claro sobre oscuro, que es
        # justo la polaridad de esta receta. Van dos veces y espejadas.
        {"src": RADIOGRAFIAS, "tones": XRAY_CLARO,
         "repeat": {"step": [0.6, 0], "times": 1, "mirror": True,
                    "blend": "screen"}},
    ] + OSCURAS + [
        # Los esqueletos de museo acompañan, con el mismo tratamiento.
        {"src": h, "repeat": {"step": [0.62, 0], "times": 1, "mirror": True,
                              "blend": "screen"},
         "tones": {"normalize": True, "gamma": 1.5}}
        for h in HUESOS
    ] + [
        {"src": f"{MUSEOS}/hexthree.JPG", "cover": True, "opacity": 0.18,
         "blend": "screen", "stain": {"amount": 0.6, "scale": 0.5}},
    ],
}

if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))