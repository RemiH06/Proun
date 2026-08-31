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