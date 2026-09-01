"""Alineada: el registro del fondo de referencia.

Piezas que se tocan entre sí formando una banda irregular, con papel vacío
arriba y abajo. Es `layout.mode = "align"`: cada pieza cae en el hueco más
alto disponible dentro de un ancho fijo, como una estantería, en vez de caer
al azar en cualquier parte del lienzo.

La clave para que quede como banda y no como pared es un `layout.size` bajo:
con piezas grandes el bloque crece más alto que el lienzo y se recorta arriba
y abajo, que también se puede ver bien pero ya no deja el margen de papel.

Cuatro cosas para que no se sienta plana:
- `PROTAGONISTA` entra con un `resize` explícito bien por encima del rango
  general, así que el empaquetador la trata como una pieza grande entre
  piezas chicas y ancla la composición.
- Las piezas gráficas (`GRAFICAS`) llevan `repeat`, estampadas sobre sí
  mismas antes de entrar al bloque.
- Una textura entra por `mosaic` en vez de foto suelta.
- El fondo lleva bastante `stain`, con `threshold` para que se lea como
  mancha y no como desvanecido parejo.

    python -m recetas.alineada
"""

from proun.cli import main

from ._comun import (CETI, COOL_OBJETOS, CYANOTIPO_TONES, CYANOTIPO_TRANSPARENT,
                     CYANOTIPOS, GRAFICAS, MASCOTAS, MUSEOS, PROTAGONISTA,
                     RADIOGRAFIAS)

CONFIG = {
    "output": "wallpapers/alineada",
    "resolutions": ["1920x1080", "2560x1440"],
    "colors": ["#1c1c1c", "#2a1f1a"],
    "count": 4,
    "seed": 1843,

    "background": {"solid": "#f2efe8",
                   "stain": {"amount": 0.55, "scale": 0.4, "threshold": 0.35,
                            "color": "#c9beac"}},
    "layers": {"min": 11, "max": 16},
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
        # La protagonista: bastante más grande que el resto del bloque.
        {"src": PROTAGONISTA, "tones": {"normalize": True, "invert": True},
         "resize": {"size": [0.42, 0.42], "mode": "fit"},
         "stain": {"amount": 0.18, "scale": 0.4, "threshold": 0.45}},

        {"src": RADIOGRAFIAS, "tones": {"normalize": True, "invert": True}},
        {"src": CYANOTIPOS, "tones": CYANOTIPO_TONES,
         "transparent": CYANOTIPO_TRANSPARENT},

        # Gráficas repetidas sobre sí mismas antes de entrar al bloque.
        *[{"src": g, "repeat": {"step": [0, 0.5], "times": 2, "mirror": True}}
          for g in GRAFICAS],

        # Una textura por mosaico, para variar la escala del detalle.
        {"src": f"{MUSEOS}/wall.JPG", "mosaic": {"grid": [2, 2], "mirror": True},
         "resize": {"size": [0.2, 0.2], "mode": "fit"}},

        MUSEOS,
        MASCOTAS,
        CETI,
        *COOL_OBJETOS,
    ],
}

if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))