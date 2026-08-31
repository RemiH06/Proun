"""Retícula: el registro constructivista.

Piezas en cuadrícula, giros de un cuarto de vuelta, un color fuerte y un acento
que no sigue al lote. Es la receta más gráfica y la que mejor aguanta fotos con
fondo, porque no depende de aislar el sujeto.

    python -m recetas.reticula
"""

from proun.cli import main

from ._comun import GRAFICAS, MUSEOS

CONFIG = {
    "output": "wallpapers/reticula",
    "resolutions": ["1920x1080", "2560x1440"],
    "colors": ["#d94f3d", "#2f5fa8", "#1f7a5a", "#c9a227"],
    "count": 4,
    "seed": 1922,

    "background": {"gradient": ["auto_dark", "#0e0e10"], "direction": "diagonal"},
    "layers": {"min": 4, "max": 6},
    "layout": {"mode": "grid", "jitter": 0.22, "bleed": 0.1, "size": [0.42, 0.62]},
    "finish": {"grain": 0.03, "contrast": 1.1},

    "defaults": {
        "rotate": "random",
        "tones": {"normalize": True, "cutoff": 3},
        "recolor": {"mode": "duotone", "shadow": "#111013"},
        "blend": "normal",
    },

    "sources": [
        {"src": f"{MUSEOS}/wall.JPG", "cover": True, "opacity": 0.5,
         "recolor": {"mode": "duotone", "strength": 0.9},
         "stain": {"amount": 0.5, "scale": 0.6, "edges": 0.4}},
        f"{MUSEOS}/sabertooth.JPG",
        f"{MUSEOS}/crouch.JPG",
        f"{MUSEOS}/three.JPG",
        f"{MUSEOS}/stones.JPG",
        f"{MUSEOS}/teeth.JPG",
        {"src": f"{MUSEOS}/tut.JPG", "crop": {"aspect": "1:2", "anchor": "center"}},
        # Las gráficas se estampan en tira, sin girar.
        *[{"src": g, "rotate": None,
           "repeat": {"step": [0.5, 0], "times": 2, "fade": 0.15}} for g in GRAFICAS],
        # El acento no sigue al color del lote: aparece siempre en el mismo tono.
        {"src": f"{MUSEOS}/small.JPG", "color": "#f2f0e6", "opacity": 0.95,
         "resize": {"size": [0.3, 0.3], "mode": "fill"}},
    ],
}

if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))
