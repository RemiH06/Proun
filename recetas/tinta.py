"""Tinta sobre papel: el registro del fondo de referencia.

El lienzo es papel claro, el extremo claro de cada foto desaparece y solo lo
oscuro se acumula donde las piezas se solapan. Funciona mejor con fotos de
sujeto aislado sobre fondo claro.

    python -m recetas.tinta
"""

from proun.cli import main

from ._comun import (CLARAS, CYANOTIPO_TONES, CYANOTIPO_TRANSPARENT, CYANOTIPOS, GRAFICAS, MUSEOS,
                     RADIOGRAFIAS, XRAY_OSCURO)

CONFIG = {
    "output": "wallpapers/tinta",
    "resolutions": ["1920x1080", "2560x1440"],
    "colors": ["#1c1c1c", "#3b2f1e", "#1b2a3a", "#2c1f2b"],
    "count": 4,
    "seed": 1843,

    "background": {"solid": "#f2efe8",
                   "stain": {"amount": 0.35, "scale": 0.5, "color": "#d8d2c4"}},
    "layers": {"min": 7, "max": 11},
    "layout": {"mode": "scatter", "bleed": 0.2, "size": [0.3, 0.72]},
    "finish": {"grain": 0.04, "contrast": 1.05},

    "defaults": {
        "rotate": "random",
        # dominant lleva el tono más frecuente de cada foto al blanco, que
        # casi siempre es su fondo. Es lo que hace que una foto de museo se
        # lea como objeto y no como neblina rectangular.
        "tones": {"normalize": True, "cutoff": 2, "dominant": "light", "gamma": 0.8},
        "transparent": {"color": "light", "tolerance": 0.02, "softness": 0.4},
        "recolor": {"mode": "duotone", "shadow": "#141210", "highlight": "#8a8078"},
        "blend": "multiply",
        "stain": {"amount": 0.55, "scale": 0.3, "edges": 0.55, "threshold": 0.4},
    },

    "sources": [
        # Las radiografías van invertidas: vienen claras sobre negro y aquí
        # se necesita el esqueleto oscuro sobre papel. Espejadas sobre sí
        # mismas, que es de donde salen las figuras de mariposa.
        {"src": RADIOGRAFIAS, "tones": XRAY_OSCURO,
         "repeat": {"step": [0.58, 0], "times": 1, "mirror": True,
                    "blend": "multiply"},
         "stain": {"amount": 0.4, "scale": 0.35, "edges": 0.6}},
        {"src": CYANOTIPOS, "tones": CYANOTIPO_TONES,
         "transparent": CYANOTIPO_TRANSPARENT},
    ] + CLARAS + [
        # Las gráficas entran repetidas sobre sí mismas, como las barras del
        # fondo de referencia.
        {"src": g, "repeat": {"step": [0, 0.55], "times": 2, "mirror": True},
         "stain": {"amount": 0.35, "scale": 0.2}}
        for g in GRAFICAS
    ] + [
        {"src": f"{MUSEOS}/squares.JPG", "mosaic": {"grid": [2, 2], "mirror": True},
         "opacity": 0.7},
    ],
}

if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))