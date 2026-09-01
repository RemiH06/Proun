"""Rutas y agrupaciones compartidas por las recetas.

Los grupos no están hechos por tema sino por cómo se comporta cada pieza en el
pipeline, que es lo que de verdad importa para el resultado.
"""

BIO = "fuentes/Bio"
CETI = "fuentes/Ceti"
COOL = "fuentes/Cool pics"
MASCOTAS = "fuentes/Mascotas"
MUSEOS = "fuentes/Museos"

# Las radiografías del Smithsonian son los únicos .png de Bio, así que el glob
# ya significa "radiografías". Vienen claras sobre negro y con simetría
# bilateral, que es justo lo que pide el espejado de `repeat`.
RADIOGRAFIAS = f"{BIO}/*.png"

# El resto de Bio son fotos normales.
BIOFOTOS = f"{BIO}/*.jpg"

# Museos, agrupado por comportamiento.
CLARAS = [f"{MUSEOS}/{n}.JPG" for n in
          ("golden", "golden2", "small", "squares", "tests", "yellow", "flowers")]
OSCURAS = [f"{MUSEOS}/{n}.JPG" for n in
           ("ark", "tut", "wall", "vessels", "mamooth", "hexthree")]
GRAFICAS = [f"{MUSEOS}/{n}.JPG" for n in ("squares", "tests", "golden2")]
HUESOS = [f"{MUSEOS}/{n}.JPG" for n in ("sabertooth", "mamooth", "teeth")]

# Texturas sueltas que sirven de fondo o de material de mosaico.
ROCAS = f"{COOL}/rocks*.jpg"

# Tratamientos reutilizables para las radiografías, según la polaridad de la
# receta. En tinta hay que invertirlas: vienen claras sobre negro y sobre papel
# blanco se necesita lo contrario.
XRAY_CLARO = {"normalize": True, "gamma": 1.6}
XRAY_OSCURO = {"normalize": True, "invert": True, "cutoff": 1}

# --- Cianotipos de Higgsfield -------------------------------------------
# Ya vienen como fotograma: sujeto aislado, alto contraste, borde de papel
# real. Con dominant "light" el papel desaparece limpio y el sujeto queda
# de tinta sólida, igual que las radiografías. Entran al pipeline normal y
# se recolorean al color del lote, no conservan su azul nativo.
CYANOTIPOS = [
    "fuentes2/Bio/snail_cyanotype.png",
    "fuentes2/Mascotas/billz1_cyanotype.png",
    "fuentes2/Cool pics/fridge_cyanotype.png",
]
CYANOTIPO_TONES = {"normalize": True, "cutoff": 2, "dominant": "light"}
# El papel del cianotipo es más irregular que una foto de museo ya duotono, y
# necesita más margen para despejarse del todo.
CYANOTIPO_TRANSPARENT = {"color": "light", "tolerance": 0.06, "softness": 0.55}

# Multicolor de verdad: mapa térmico y salpicadura de tinta. Rompen a
# propósito la unidad de paleta, así que van sin recolor y con opacidad baja,
# como acento suelto. No se usan en tinta/vitrina/alineada, que dependen de
# que todo comparta un color.
ACENTOS_COLOR = [
    "fuentes2/Cool pics/fridge_heat.png",
    "fuentes2/Cool pics/fridge_inkbloom.png",
]

# Piezas de "Cool pics" que se comportan como objeto (fondo relativamente
# plano) y no como paisaje. Es una conjetura por nombre, ajústala cuando
# veas cómo se portan de verdad.
COOL_OBJETOS = [f"{COOL}/{n}.jpg" for n in
                ("hand", "glasses", "stick", "bug_clips", "rooster", "drawing",
                 "homework", "makeup")]

# Una pieza que se sale del tamaño normal y ancla la composición. En modo
# align sigue empaquetándose con las demás, solo que ocupa más sitio.
PROTAGONISTA = f"{BIO}/smalltoothsawfish.png"