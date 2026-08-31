# Recetas

Cada archivo es una configuración completa que se corre sola:

```bash
python -m recetas.tinta
python -m recetas.vitrina
python -m recetas.reticula
python -m recetas.mezcla
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

**mezcla** es la pensada para cuando estén todas las carpetas. Cada origen entra
con un tratamiento distinto para que se distingan sin dejar de compartir paleta.
Las líneas de las otras temáticas están comentadas: descoméntalas conforme
tengas las carpetas.

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
por cómo se comportan en el pipeline, no por tema. Cuando veas cómo se portan
las de `Ceti` y `Cool pics`, conviene agruparlas igual.