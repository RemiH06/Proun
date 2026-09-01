"""Alineada: el registro exacto del fondo de referencia.

Piezas que se tocan entre sí formando una banda irregular, con papel vacío
arriba y abajo. Es `layout.mode = "align"`: cada pieza cae en el hueco más
alto disponible dentro de un ancho fijo, como una estantería, en vez de caer
al azar en cualquier parte del lienzo.

La clave para que quede como banda y no como pared es un `layout.size` bajo:
con piezas grandes el bloque crece más alto que el lienzo y se recorta arriba
y abajo, que también se puede ver bien pero ya no dej el margen de papel.

    python -m recetas.alineada
"""

from proun.cli import main

from ._comun import CYANOTIPO_TONES, CYANOTIPO_TRANSPARENT, CYANOTIPOS, MUSEOS, RADIOGRAFIAS, XRAY_OSCURO

CONFIG = {
    "output": "wallpapers/alineada",
    "resolutions": ["1920x1080", "2560x1440"],
    "colors": ["#1c1c1c", "#2a1f1a"],
    "count": 4,
    "seed": 1843,

    "background": {"solid": "#f2efe8",
                   "stain": {"amount": 0.3, "scale": 0.5, "color": "#ddd6c6"}},
    "layers": {"min": 9, "max": 14},
    "layout": {"mode": "align", "width": 0.92, "gap": 2, "anchor": "center",
              "size": [0.14, 0.24]},
    "finish": {"grain": 0.03},

    "defaults": {
        "rotate": None,
        # dominant "auto" en vez de "light": con piezas oscuras forzar el
        # blanco las invierte todas y el bloque queda demasiado lavado.
        "tones": {"normalize": True, "cutoff": 2, "dominant": "auto"},
        "transparent": {"color": "light", "tolerance": 0.05, "softness": 0.5},
        "recolor": {"mode": "duotone", "shadow": "#141210", "highlight": "#8a8078"},
        "blend": "multiply",
        "stain": {"amount": 0.35, "scale": 0.3, "threshold": 0.4},
    },

    "sources": [
        {"src": RADIOGRAFIAS, "tones": {"normalize": True, "invert": True}},
        {"src": CYANOTIPOS, "tones": CYANOTIPO_TONES,
         "transparent": CYANOTIPO_TRANSPARENT},
        MUSEOS,
    ],
}

if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))