# Recetas

Cada archivo es una configuración completa que se corre sola:

```bash
python -m recetas.tinta
python -m recetas.vitrina
python -m recetas.reticula
python -m recetas.mezcla
python -m recetas.alineada
```

Las banderas siguen funcionando encima, que es la manera de iterar rápido:

```bash
python -m recetas.tinta --resolutions 800x450 --count 2 --quiet
python -m recetas.tinta --seeds 424462866 --overwrite
python -m recetas.tinta --clean --yes
```

Cuatro recetas por cuatro semillas por sus colores dan bastante más de 16
archivos; con `--count 1` sale uno por color de cada receta.

## Qué hace cada una

**tinta** es el registro del fondo de referencia. Papel claro, el extremo claro
de cada foto desaparece y solo lo oscuro se acumula al solaparse. Pide fotos de
sujeto aislado sobre fondo claro; con fotos de fondo cargado se ensucia.

**vitrina** es la polaridad contraria: fondo oscuro, desaparece lo oscuro y lo
que brilla se acumula con `screen`. Es la receta para las piezas densas y para
el material de archivo. Los esqueletos van espejados sobre sí mismos.

**reticula** es la constructivista. Cuadrícula, giros de un cuarto de vuelta,
color fuerte y un acento que no sigue al color del lote. Es la que mejor aguanta
fotos con fondo, porque no depende de aislar el sujeto.

**alineada** trae cuatro cosas para que no se sienta uniforme: `PROTAGONISTA`
(una radiografía específica, más grande que el resto), `GRAFICAS` repetidas
sobre sí mismas antes de entrar al bloque, una textura por `mosaic`, y bastante
`stain` con `threshold` en el fondo para que se lea como mancha y no como
desvanecido parejo.

Un aviso sobre `align` en general: castiga a las fotos con mucho fondo vacío.
`transparent` se come ese fondo, y como el empaquetador reserva la caja
completa de la imagen, una foto con poco sujeto deja mucho hueco visible
alrededor de una mancha chica, aunque las cajas se toquen sin solaparse. Cuanto
más llena su encuadre la foto, mejor se ve empaquetada.

Es el registro más cercano al fondo de referencia: piezas que se
tocan entre sí formando una banda irregular, con papel vacío arriba y abajo.
Usa `layout.mode = "align"`. La clave para que se vea como banda y no como
pared es un `layout.size` bajo (aquí 0.14 a 0.24); con piezas grandes el bloque
crece más alto que el lienzo y se recorta arriba y abajo.

**mezcla** es la pensada para cuando estén todas las carpetas. Cada origen entra
con un tratamiento distinto para que se distingan sin dejar de compartir paleta.
Las líneas de las otras temáticas están comentadas: descoméntalas conforme
tengas las carpetas.

## Los cianotipos

Tres imágenes pasadas por el filtro Cyanotype de Higgsfield: `snail_cyanotype`,
`billz1_cyanotype` y `fridge_cyanotype`. Ya vienen como fotograma, sujeto
aislado sobre papel con borde real, así que entran al pipeline como cualquier
fuente: `tones` con `dominant: "light"` despeja el papel, `transparent` lo hace
desaparecer del todo. No conservan su azul nativo, se recolorean al color del
lote como todo lo demás, para mantener la paleta unificada.

`fridge_cyanotype` trae una viñeta negra de foto instantánea que `light` no
toca, porque no es claro. No es un error: se lee como una polaroid con marco,
distinta de las otras dos.

Las constantes están en `_comun.py`: `CYANOTIPOS`, `CYANOTIPO_TONES` y
`CYANOTIPO_TRANSPARENT`, este último con más margen que el resto porque el
papel del cianotipo es menos parejo que una foto de museo ya duotono.

`fridge_heat` y `fridge_inkbloom` son otra cosa: multicolor de verdad (mapa
térmico, salpicadura de tinta), no duotono. Van en `ACENTOS_COLOR` sin usar
todavía; rompen a propósito la unidad de paleta, así que no entran en
tinta/vitrina/alineada. Son candidatas para cuando existan las figuras
geométricas de colores (pendiente 1).

## Las radiografías

Las nueve del Smithsonian son los únicos `.png` de `Bio/`, así que el glob
`fuentes/Bio/*.png` ya significa "radiografías" sin listarlas a mano. Vienen
claras sobre negro, y por eso llevan trato distinto según la polaridad de cada
receta:

- en **vitrina** entran tal cual, que ya es claro sobre oscuro
- en **tinta** y **mezcla** van invertidas con `tones`, para que el esqueleto
  quede oscuro sobre el papel y el fondo desaparezca

Las dos constantes están en `_comun.py` como `XRAY_CLARO` y `XRAY_OSCURO`.
Además van siempre espejadas sobre sí mismas con `repeat`, que es de donde salen
las figuras de mariposa.

## Rutas

Todo apunta a `_comun.py`. Ajusta ahí las carpetas y las listas de piezas.
`CLARAS`, `OSCURAS`, `GRAFICAS` y `HUESOS` son subconjuntos de museos elegidos
por cómo se comportan en el pipeline, no por tema.