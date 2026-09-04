# Proun

Generador de wallpapers tipo collage con paleta normalizada, inspirado en el
fotomontaje constructivista de El Lissitzky, Klutsis y Ródchenko. La v1.0 es
una herramienta de línea de comandos en Python puro (solo depende de
Pillow). Esta v2.0 le da interfaz gráfica en React, convirtiendo el motor
actual en algo parecido a una API: la lógica de Python no se reescribe, se
envuelve.

Sesión previa completa (diseño del motor, la documentación, y todo el
recorrido de decisiones) vivió en una conversación de chat larga que ya no
está disponible aquí. Este archivo es el resumen de lo que hace falta saber
para seguir sin releer nada de eso.

## Filosofía del proyecto (no negociable)

- **Ponytail**: antes de escribir código nuevo, en orden: ¿esto necesita
  existir? ¿lo resuelve la librería estándar? ¿una función nativa? ¿una
  dependencia ya instalada? ¿se puede en una línea? Recién ahí escribe lo
  mínimo necesario. Nunca sacrifiques validación, manejo de errores,
  seguridad o accesibilidad por brevedad.
- **Nunca uses guión largo "—"**, en ningún archivo, ni como carácter
  literal ni como entidad HTML `&mdash;`/`&ndash;`. Usa coma, dos puntos,
  paréntesis, o restructura la frase. Esto se aplica a código, comentarios,
  documentación y cualquier texto de cara al usuario. Barrido recomendado
  antes de cada entrega: `grep -rn "—\|&mdash;\|&ndash;" .`
- **Español** en comentarios, docstrings, mensajes de commit y toda la
  prosa. Los nombres de variables y funciones en el motor Python también
  están en español (`fuentes`, `capas`, `mancha`, etc.); mantén esa
  convención en el código nuevo del motor. El código de infraestructura
  (React, API) puede usar inglés si es más natural para esas librerías,
  pero comentarios y mensajes de UI siguen en español.
- **Checkpoints**: commits en formato conventional commits, tan breves como
  sea posible, sin saltos de línea innecesarios.
- Nada de código sin probar. Cada cambio de comportamiento va acompañado de
  su prueba, y `python -m unittest discover -s tests` debe quedar en verde
  antes de dar algo por terminado.

## Qué es Proun (el motor, v1.0)

```
main.py                    punto de entrada CLI, CONFIG editable
diagnosticar.py            mide % de píxeles oscuros por archivo real,
                            con las dos polaridades (light/dark)
inspeccionar.py            lista fuentes con tamaño y proporción
requirements.txt           solo Pillow

recetas/                   configuraciones Python de ejemplo
  _comun.py                 rutas y constantes compartidas (MUSEOS,
                             GRAFICAS, clasificación CLARAS/OSCURAS)
  tinta.py                   papel claro, tinta por multiply
  vitrina.py                  fondo oscuro, screen (luz sobre oscuridad)
  reticula.py                  cuadrícula constructivista, giros en 90°
  mezcla.py                     todas las carpetas
  alineada.py                    empaquetado tipo estantería
  examen.py                       reconstrucción de una imagen de referencia

json/                      specs completas en JSON, alternativa a CONFIG
  exp.json                  playground con varios parámetros activados
  examen.json                receta completa del fondo de referencia
  proun_ss4.json              semilla fija, reproduce un wallpaper exacto
  (rutas internas "src"/"pool" se resuelven relativas a la ubicación del
  propio archivo JSON, no al cwd: ver proun/spec.py::_relative_sources)

proun/
  spec.py            Layer, Spec, build(), load(): valida y normaliza la
                      configuración. Cuatro tipos de capa mutuamente
                      excluyentes: src | shape | text | pool
  compose.py          plan() → prepare() → render(): plan() solo sortea con
                      la semilla (no toca píxeles, salvo si pool_dark_bias
                      está activo), prepare() hace geometría, render()
                      recolorea. prepare()+render() se reusan entre colores
                      del mismo lote
  pool.py             selección ponderada de un archivo entre varios
                      candidatos: por qué tan bien calza la proporción
                      (siempre) y, opcionalmente, por qué tan oscuro
                      saldría el recorte (pool_dark_bias, apagado por
                      defecto)
  layout.py           posiciones (scatter/grid/align), tamaños
  loading.py           expand(), load(), peek_size() (sin decodificar
                        píxeles, para no pagar el costo en plan())
  geometry.py, colors.py, naming.py, cleanup.py, cli.py, errors.py
  ops/                 una operación por archivo, aplicadas en este orden
                        exacto sobre cada capa:
    crop → resize → mosaic → repeat → stain → rotate → tones →
    transparency → recolor
                        __init__.py debe quedar VACÍO (imports ahí generan
                        falsos circulares en Windows)

tests/                     572 pruebas, unittest estándar
fuentes/                    archivo personal de imágenes del usuario, NO
                             se versiona
docs/                       sitio de documentación (ver sección aparte)
```

### Cómo pensar el motor

- **Paleta normalizada**: cualquier color puede volverse transparente
  (`transparent.tolerance`/`softness`), y de ahí sale la polaridad completa
  del proyecto: tinta oscura sobre papel o luz sobre oscuridad son el mismo
  mecanismo con el color invertido.
- **`tones.dominant`**: decide qué extremo tonal se lleva al blanco/negro.
  `"auto"` decide por el tono más frecuente de la imagen; para fotografía
  real (paredes oscuras de museo, por ejemplo) casi siempre conviene forzar
  `"light"` en vez de confiar en `"auto"`.
- **Selección por pool sí distingue por recorte, no solo por archivo**: la
  misma foto puede dar un resultado bien iluminado en un hueco y un
  resultado oscuro en otro, según qué región termine recortada ahí.
  `pool_dark_bias` mide esto procesando cada candidata en miniatura antes
  de sortear (por eso es la única parte de `plan()` que decodifica
  píxeles).
- **Reproducibilidad**: cada archivo lleva su semilla en el nombre.
  `plan()` es puramente determinista dada la semilla; regenerar el mismo
  wallpaper es correr con la misma semilla, sin importar cuánto tiempo
  pasó.

## v2.0: interfaz gráfica en React

Objetivo: convertir el motor de Python en un servicio con el que una
webapp React pueda trabajar interactivamente (subir imágenes, ajustar
parámetros, ver previsualización, exportar), sin reescribir la lógica de
generación. El motor Python sigue siendo la fuente de verdad.

Piezas que probablemente hagan falta (a decidir/construir en Claude Code,
no asumidas de antemano):

- **Capa de API** sobre `proun/spec.py` + `proun/compose.py` (candidatos
  razonables: FastAPI o Flask). Debe aceptar algo estructuralmente
  equivalente a los JSON de `json/` y devolver la imagen generada o una
  referencia a ella.
- **Frontend React** para edición interactiva: parámetros de capa,
  previsualización, y probablemente un editor visual de la especificación
  en vez de JSON a mano.
- Pensar temprano en **previsualización de bajo costo**: renderizar a
  resolución completa en cada ajuste de parámetro va a ser lento; vale la
  pena decidir una estrategia de preview (resolución reducida, debounce,
  cache de la etapa `prepare()` reutilizada entre ediciones de color) antes
  de construir mucho encima.
- El manejo de `fuentes/` (el archivo de imágenes del usuario) necesita una
  historia de subida/almacenamiento que hoy no existe: v1.0 asume que ya
  están en disco.

No hay código de v2.0 todavía. Este documento es el punto de partida, no
una arquitectura ya decidida: confirma con el usuario antes de comprometerte
a FastAPI vs Flask, a dónde vive el almacenamiento de imágenes, etc.

## docs/index.html: sitio de documentación (GitHub Pages)

Página única, autocontenida (HTML/CSS/JS inline), estética constructivista:
papel `#f2efe8`, tinta `#141210`, rojo `#d94f3d`. Tipografía Big Shoulders
(empaquetada en `proun/assets/fonts/`, la misma que usa `ops/text.py`) para
títulos, serif del sistema para cuerpo. Se publica desde `/docs` en la
rama principal.

Usa **Motion** (motion.dev, build vanilla para DOM, no la versión de
React) vía CDN de jsdelivr como módulo ES. Efectos:

- **Hero**: imagen a pantalla completa con título gigante centrado.
  Al hacer scroll, usa un patrón de `position: sticky` de varias pantallas
  para que el desenfoque de fondo se sostenga un buen tramo antes de que
  la imagen se aleje ligeramente y la página avance.
- **Intro de carga**: al abrir la página, dos puertas naranjas ya cerradas
  desde el arranque, con una línea negra que crece desde el centro de
  forma errante (crece, pausa, crece) hasta casi tocar los bordes. Ahí se
  abren dos puertas auxiliares chicas (arriba/abajo) al mismo tiempo que
  las puertas grandes se separan hacia los lados, todas sincronizadas para
  terminar juntas.
- **Tabs** ("Lo que trae" / "Instalación" / "Cómo usarlo"): cambian con una
  cortina (blades que se cierran, cambian el panel, se abren) y un
  indicador rojo que se desliza suave hasta la tab activa.
- **Galería**: las cuatro capturas se ensamblan con un solo momento de
  animación al entrar en pantalla, no una entrada genérica por sección.

### Patrón de seguridad, repetido en cada efecto: léelo antes de tocar el JS

Todo en esta página parte de un estado **inerte y seguro por CSS** (oculto,
fuera de pantalla, o en su posición de reposo normal). Las clases que
activan cualquier cobertura o efecto (`js-intro`, `js-pin`) **solo se
agregan dentro del script, después de que el `import` de Motion ya tuvo
éxito**, nunca antes. Si el CDN falla por cualquier razón (red, bloqueador,
caída del servicio), el script entero no corre, esas clases nunca se
agregan, y la página se ve y funciona con normalidad, solo sin animar.

Esto no es un detalle cosmético: durante la construcción de esta página se
introdujo dos veces un bug real donde una versión anterior del código dejaba
la pantalla cubierta de forma permanente si el JS fallaba a mitad de
camino. Cualquier efecto nuevo que agregues a este archivo tiene que
mantener esta garantía: **el estado por defecto sin JavaScript nunca debe
cubrir ni ocultar contenido**.

### Gotchas de este entorno, si vuelves a tocar la animación

- El CDN de jsdelivr está bloqueado en el sandbox de desarrollo de Claude
  (no en producción). Para probar JS real: `npm pack motion@11` o
  `npm install motion@11 esbuild`, empaquetar con esbuild a un archivo
  único, y sustituir temporalmente la URL del import por ese bundle local
  al probar con Playwright.
- `animate()` de Motion no respeta un `transform` puesto solo en CSS: si
  animas `scaleY` sin mencionar `scaleX`, Motion asume `scaleX: 1` por su
  cuenta. Hay que pasar explícitamente todos los ejes relevantes.
- Un valor estático único en `animate()` (`{ scaleX: 0.5 }`) no significa
  "quieto en ese valor": Motion lo trata como destino y anima *hacia* él
  desde el valor actual. Para mantener algo fijo, pasa el mismo valor dos
  veces: `{ scaleX: [0.5, 0.5] }`.
- `wkhtmltoimage` (motor QtWebKit viejo) no soporta CSS Grid como debería;
  no sirve para revisar layouts modernos. Usa Playwright con Chromium real.
- Los screenshots `full_page=True` de Playwright redimensionan el viewport
  al alto total del documento antes de capturar, lo cual rompe cualquier
  medida en `vh` (como el hero a pantalla completa). Para revisar secciones
  con `100vh`, usa capturas de viewport fijo en puntos de scroll específicos,
  no `full_page`.
- Nunca uses un bucle de espera activa (`while ...: pass`) en Python para
  cronometrar algo en Playwright: le roba CPU al proceso del navegador y
  distorsiona su reloj interno de animación. Usa `page.wait_for_timeout()`.
- Los procesos en segundo plano (`python3 -m http.server &`) no persisten
  entre llamadas de herramienta separadas en este entorno: el servidor y el
  script que lo consume tienen que ir en la misma invocación.
- Para verificar el timing real de una animación, mide con
  `time.time()` anclado justo antes de `page.goto()` y lee valores
  computados (`getComputedStyle(...).transform`) en varios puntos, en vez
  de adivinar milisegundos de espera antes de una captura: la demora real
  entre `goto()` y que el script empiece a correr varía de corrida a
  corrida.

## Convenciones adicionales

- Sin `#000`/`#fff` puros en CSS.
- Sin mayúsculas completas para etiquetas de sección (`text-transform:
  uppercase` en textos chicos es una señal reconocible de diseño genérico
  hecho por IA; usar minúsculas con tracking en su lugar). Mayúsculas sí se
  justifican en títulos grandes deliberados, como el wordmark del hero.
- Antes de dar por buena cualquier página o componente visual nuevo,
  revisar contra el checklist anti-genérico del proyecto (sin bento grids
  sin razón, sin gradientes decorativos, sin iconos Lucide sin curar, sin
  paleta morado/negro por defecto).