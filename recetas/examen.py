"""Examen final: reconstrucción del fondo de referencia, anotada capa por capa.

Cada bloque de abajo corresponde a un color de las anotaciones que hicimos
sobre la imagen original. Los parámetros de `repeat` (pasos, cuántas copias,
espejado) son lectura visual mía sobre las capturas, no medición exacta:
van a necesitar tu ojo una vez que esto corra contra tus archivos reales, no
contra los míos de prueba.

    python -m recetas.examen

Mapa de anotaciones -> mecanismo:

    amarillo, verde, azul, morado   ops.repeat, cuatro configuraciones distintas
    naranja                         layout.mode = "align", con crop por
                                     capa, tomando cada pieza de un "pool":
                                     varias candidatas de Museos, sorteadas
                                     con más probabilidad la que mejor calza
                                     el recorte pedido (ver pendiente 8)
    vino tinto                      un crop aislado con "pool" y un aspecto
                                     angosto, position fija
    rosa/lima/celeste               tres capas independientes confinadas a
                                     una misma "region", solapándose
    marrón                          la capa de texto: sin tratamiento propio,
                                     la mancha de background la atraviesa sola
    azul (última entrega)           fotos casi lavadas a blanco, no
                                     background.stain: ops.stain vive SOLO en
                                     el fondo, nunca sobre las capas, así que
                                     estas manchas grandes son fotos normales
                                     con muy poco contraste, no ruido
"""

from proun.cli import main

from ._comun import CYANOTIPO_TONES, CYANOTIPO_TRANSPARENT, CYANOTIPOS, MUSEOS, RADIOGRAFIAS

# Casi blanco: shadow y highlight muy cerca uno del otro y los dos cerca del
# papel, así que solo sobrevive el borde relativo de cada foto, no su
# contenido. Es el duotono que reemplaza al ruido procedural para las
# manchas grandes del fondo.
LAVADO = {"mode": "duotone", "shadow": "#efe9dd", "highlight": "#fbf9f5", "strength": 1.0}

CONFIG = {
    "output": "wallpapers/examen",
    "resolutions": ["1920x1080"],
    "colors": ["#1c1c1c"],
    "count": 2,
    "seed": 1843,

    "background": "#f2efe8",  # sólido: las manchas grandes ya no son ruido,
                              # son las fotos "lavado" de más abajo

    "layout": {"mode": "align", "width": 0.55, "gap": 2, "anchor": "center",
              "size": [0.13, 0.22]},
    # El ancho del bloque align es angosto a propósito: en la referencia, el
    # bloque naranja ocupa poco más de la mitad izquierda del lienzo, no todo
    # el ancho, y deja el resto para las capas con posición fija.

    "finish": {"grain": 0.02},

    "defaults": {
        "rotate": None,
        "tones": {"normalize": True, "cutoff": 2, "dominant": "auto"},
        "transparent": {"color": "light", "tolerance": 0.04, "softness": 0.45},
        "recolor": {"mode": "duotone", "shadow": "#141210", "highlight": "#8a8078"},
        "blend": "multiply",
        # Nada de "stain" aquí: las manchas de las capas quedaron descartadas,
        # confirmaste que viven solo en el fondo.
    },

    "sources": [
        # --- manchas grandes del fondo: fotos casi lavadas, no ruido -------
        # Rectángulos con posición fija, calcados de los recuadros azules de
        # la última captura. Casi blancas y en multiply: el orden en que se
        # dibujen contra las demás capas apenas cambia el resultado, así que
        # no depende de que caigan primero en el revuelto aleatorio.
        {"src": f"{MUSEOS}/wall.JPG", "position": [0.0, 0.0], "anchor": "topleft",
         "resize": {"size": [0.12, 0.16], "mode": "fill"},
         "recolor": LAVADO, "opacity": 0.5},
        {"src": f"{MUSEOS}/dome.JPG", "position": [0.42, 0.0], "anchor": "top",
         "resize": {"size": [0.35, 0.28], "mode": "fill"},
         "recolor": LAVADO, "opacity": 0.5},
        {"src": f"{MUSEOS}/stones.JPG", "position": [1.0, 0.15], "anchor": "topright",
         "resize": {"size": [0.1, 0.55], "mode": "fill"},
         "recolor": LAVADO, "opacity": 0.5},
        {"src": f"{MUSEOS}/vessels.JPG", "position": [0.35, 1.0], "anchor": "bottom",
         "resize": {"size": [0.5, 0.16], "mode": "fill"},
         "recolor": LAVADO, "opacity": 0.5},

        # --- amarillo: horizontal, copias casi pegadas, poco solape -------
        # Pool en vez de un archivo fijo: no sé cuál de tus fotos tiene la
        # textura de rejilla que se ve en la referencia, así que Proun elige
        # entre todo Museos, ponderado hacia lo que mejor calza el recorte
        # angosto. Si ya identificaste el archivo correcto, cámbialo por un
        # "src" normal, que es más rápido y no adivina nada.
        {"pool": MUSEOS, "position": [0.16, 0.12], "anchor": "topleft",
         "crop": {"aspect": "1:2", "auto_rotate": True}, "resize": {"size": [0.11, 0.22]},
         "repeat": {"step": [0.85, 0], "times": 3}},

        # --- verde: mismo principio, menos copias, otra esquina -----------
        {"pool": MUSEOS, "position": [0.0, 1.0], "anchor": "bottomleft",
         "crop": {"aspect": "1:2", "auto_rotate": True}, "resize": {"size": [0.08, 0.14]},
         "repeat": {"step": [0.85, 0], "times": 1}},

        # --- azul: vertical, piezas que se tocan y siguen ------------------
        {"src": RADIOGRAFIAS, "position": [0.28, 0.47], "anchor": "left",
         "tones": {"normalize": True, "invert": True},
         "resize": {"size": [0.3, 0.09]},
         "repeat": {"step": [0, 0.92], "times": 2}},

        # --- morado: vertical también, pero fundido, más solape -----------
        {"src": CYANOTIPOS, "position": [0.83, 0.03], "anchor": "top",
         "tones": CYANOTIPO_TONES, "transparent": CYANOTIPO_TRANSPARENT,
         "resize": {"size": [0.15, 0.3]},
         "repeat": {"step": [0, 0.55], "times": 1}},

        # --- vino tinto: un crop aislado, posición fija --------------------
        # Busca en tus fuentes algo con líneas horizontales tipo redacción de
        # documento (tachaduras, subrayados). Mientras tanto, pool sobre
        # Museos con un aspecto muy angosto: no va a encontrar líneas de
        # texto porque Museos no las tiene, es solo para que el hueco no
        # quede vacío. Cuando identifiques la fuente correcta, sería mejor
        # un "src" fijo aquí, porque el contenido específico importa más que
        # la proporción.
        {"pool": MUSEOS, "crop": {"aspect": "5:1", "anchor": "center", "auto_rotate": True},
         "position": [0.03, 0.32], "anchor": "topleft", "resize": {"size": [0.1, 0.03]}},

        # --- rosa/lima/celeste: tres capas distintas, misma region ---------
        # No es un crop de una sola fuente: son tres imágenes completas
        # solapándose dentro de la misma zona chica del lienzo.
        {"src": f"{MUSEOS}/flowers.JPG", "region": [0.38, 0.08, 0.55, 0.4],
         "resize": {"size": [0.17, 0.3]}, "opacity": 0.75},
        {"src": f"{MUSEOS}/crouch.JPG", "region": [0.38, 0.08, 0.55, 0.4],
         "resize": {"size": [0.17, 0.3]}, "opacity": 0.7, "blend": "screen"},
        {"src": f"{MUSEOS}/three.JPG", "region": [0.38, 0.08, 0.55, 0.4],
         "resize": {"size": [0.17, 0.3]}, "opacity": 0.65},

        # --- bloque naranja: align, con crop por capa -----------------------
        # Sin position ni region, así que caen en el bloque empaquetado.
        # Cada entrada es un pool sobre todo Museos: cada una pide un
        # recorte de proporción distinta, y Proun sortea qué archivo real
        # usar ponderado hacia el que mejor calza ese recorte en particular.
        # El mismo archivo puede salir elegido en más de una entrada, que es
        # exactamente lo que pasa en la referencia: la misma pieza recortada
        # de formas distintas en distintos lugares del bloque.
        {"pool": MUSEOS, "crop": {"aspect": "4:3", "anchor": "top", "auto_rotate": True}},
        {"pool": MUSEOS, "crop": {"aspect": "1:1", "auto_rotate": True}},
        {"pool": MUSEOS, "crop": {"aspect": "16:9", "anchor": "center", "auto_rotate": True}},
        {"pool": MUSEOS, "crop": {"aspect": "1:1", "anchor": "left", "auto_rotate": True}},
        {"pool": MUSEOS, "crop": {"aspect": "3:4", "anchor": "top", "auto_rotate": True}},
        {"pool": MUSEOS, "crop": {"margin": 0.1}},
        {"pool": MUSEOS, "crop": {"aspect": "4:3", "auto_rotate": True}},
        {"pool": MUSEOS, "crop": {"aspect": "16:9", "anchor": "bottom", "auto_rotate": True}},

        # --- texto: sin tratamiento propio, la mancha del fondo lo atraviesa
        {"text": {"text": "PROUN", "weight": "bold"}, "region": [0.02, 0.3, 0.2, 0.5],
         "resize": {"size": [0.15, 0.05]}, "opacity": 0.9},
    ],
}

if __name__ == "__main__":
    raise SystemExit(main(config=CONFIG))