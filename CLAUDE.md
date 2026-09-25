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
recolorear.py              repinta un wallpaper YA exportado con un
                            colormap (recolor.py, modo "colormap"), sin
                            reconstruirlo desde sus capas originales
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
    transparency → recolor → finish (opcional, por capa)
                        __init__.py debe quedar VACÍO (imports ahí generan
                        falsos circulares en Windows)

tests/                     895 pruebas, unittest estándar
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
- **`finish` es tanto global (`Spec.finish`) como por capa (`Layer.finish`)**:
  la misma función `ops/finish.py::apply` sirve para las dos cosas, pero
  está pensada para un lienzo opaco. Aplicada tal cual sobre el tile de una
  capa (que suele tener bordes transparentes: el recuadro alrededor de una
  figura, o de una foto girada) pintaría esos bordes de negro/ruido opaco,
  porque viñeta/grano/veladura no miran el alfa de lo que reciben. Por eso
  `compose.render` guarda el alfa original de la capa antes de llamar a
  `finish.apply` y lo restaura después (ver el comentario ahí): así el
  acabado queda adentro de la silueta de la capa, no en todo su recuadro.
  Si algún día se agrega un nuevo sub-efecto a `ops/finish.py`, hay que
  revisar si también ensucia el alfa fuera del contenido real antes de
  darlo por seguro para uso por capa (probalo como
  `tests/test_compose.py::AcabadoPorCapa` lo hace con vignette/grain).
- **`recolor.mode = "colormap"`**: a diferencia de duotone/tint/screen/hue
  (todos derivados de un color principal), mapea el tono a un degradado de
  varios colores con nombre (`name`, ver `recolor.COLORMAPS`: inferno,
  viridis, plasma, magma, cividis, turbo, la familia perceptualmente
  uniforme de matplotlib/ArcGIS Pro) o propio (`stops`, una lista de
  colores). No usa `main` para nada; sirve tanto para componer de cero
  como para volver a colorear un wallpaper YA exportado (`recolorear.py`
  y la pestaña "recolorear" del GUI, ver más abajo), porque solo le
  importa el brillo de cada píxel, no de dónde salió.
- **`recolor.mode = "invert"`**: negativo fotográfico llano
  (`PIL.ImageOps.invert`, 255 menos cada canal), tampoco usa `main`.
  Reusa toda la infraestructura de alfa/`strength`/`saturation` que ya
  tiene `recolor.apply` en vez de resolverlo aparte: por eso vive como un
  modo más ahí y no como una función suelta.
- **`geometry.measure()` distingue fracción de píxeles por el tipo de
  Python, no por el valor**: `0.5` (float) es "mitad del lienzo", pero
  `1` (int) es "1 píxel", aunque numéricamente ambos podrían representar
  "el 100%". JSON no tiene esa distinción (`1` y `1.0` se serializan
  igual), así que cualquier control del GUI que mande una fracción del
  lienzo como número (como el tamaño manual por capa) tiene que evitar
  mandar un valor entero exacto, o el motor lo va a leer como píxeles
  absolutos. `frontend/src/api/client.ts::toLayerDict` ya tiene el
  parche para `resize.size` (le suma un épsilon si el valor es un entero);
  cualquier control nuevo que mande otra fracción numérica necesita el
  mismo cuidado.

## v2.0: interfaz gráfica en React

Objetivo: convertir el motor de Python en un servicio con el que una
webapp React pueda trabajar interactivamente (elegir imágenes, ajustar
parámetros, ver previsualización, exportar), sin reescribir la lógica de
generación. El motor Python sigue siendo la fuente de verdad.

Decidido y construido (MVP local, un solo usuario, sin auth ni hosting):

- `api/`: FastAPI sobre `proun/spec.py` + `proun/compose.py`. Cada ruta arma
  el mismo tipo de dict que ya acepta `spec.build`, nada de validación
  propia. `POST /api/preview` (baja resolución) y `POST /api/export`
  (resolución real) comparten `_render()` en `api/routes_render.py`;
  `api/cache.py` guarda la salida de `compose.prepare()` para no rehacer
  geometría cuando solo cambia color o recoloreado (ver el comentario ahí
  sobre por qué ese hash es distinto de `naming.content_hash`). Corre con
  `uvicorn api.main:app --reload --port 8030` (puerto fijado a propósito,
  no el 8000 default: varios proyectos de esta máquina ya lo usan, ver
  `PORTS.md` en `48.SkillShot`).
- `frontend/`: React + Vite + TypeScript. El dev server (`npm run dev`)
  llega a la API por proxy (`vite.config.ts`), no por CORS: es local, no
  hace falta esa superficie. Paleta y tipografía son las mismas de
  `docs/index.html` (`frontend/src/styles/tokens.css`), siguiendo el
  criterio de la skill `site-launch-checklist` instalada en
  `.claude/skills/`.
- Modelo: ya no es "carpeta entera, el motor elige cuántas capas al azar",
  y ya no es solo imágenes: el lienzo es una lista de **capas**
  (`LayerConfig`, unión discriminada por `kind`: `image` | `shape` |
  `text`). Las imágenes se buscan en una carpeta (`SourceFolderPicker`) y
  se eligen a mano por clic (selección múltiple, cada clic agrega o
  saca); figuras y texto se agregan con `AddLayerButtons`. Cada capa
  entra con su propio submenú de ajustes (`LayerConfigPanel`, columna del
  medio, scrolleable): rotar/voltear, opacidad, modo de fusión, color
  propio, tamaño manual (`resize.size` como fracción del lienzo, botón
  "auto" vuelve al tamaño que sortea el layout, mismo mecanismo que ya usa
  `layout.sizes()` internamente; botón "llenar marco" pone escala 1 +
  modo "llenar" + posición centrada, para que una capa cubra el lienzo
  entero sin dejar huecos; el modo "ajustar"/"llenar" alterna entre
  `resize.mode` "fit" (conserva proporción, puede dejar espacio) y "fill"
  (recorta el sobrante, sin espacio)), recorte por proporción (`crop.aspect`,
  botones libre/1:1/4:3/3:4/16:9/9:16), manchas propias (`stain`), acabado
  propio (`finish`:
  viñeta, grano, desenfoque, contraste, brillo, saturación, veladura,
  mismos controles que el acabado global, componente compartido
  `FinishControls`), repetición lineal (con espaciado) o caleidoscopio
  (`pivot`/`sectors`, con espaciado), mosaico, posición manual (arrastrar
  en un cuadrito que representa el lienzo) y orden de apilado (`z`, atrás/
  adelante); las capas de figura suman tipo (`shape`, botones) y contorno,
  las de texto suman el input de texto (el único texto libre del editor,
  fuera de la ruta de carpeta) y peso/alineación. Todo con botones/
  sliders. Un botón "duplicar" por capa permite que la misma imagen/
  figura/texto entre dos veces al collage como dos capas independientes
  (identificadas por `id`, no por ruta). Cada submenú es compactable
  (flechita ▾/▸ en el encabezado, estado local del componente, no viaja al
  spec) para que una lista larga de capas no vuelva la columna del medio
  inmanejable.
- Parámetros globales que quedan en `ParamControls`: `layout.mode`, color
  principal del lote, `recolor.mode`, semilla con "rehacer". Los ajustes
  globales de `background` (auto/sólido/degradado + dirección + manchas)
  y `finish` (viñeta, grano, desenfoque, contraste, brillo, saturación,
  veladura, manchas) viven en `CanvasControls`, debajo de esos.
- **Dimensiones del canvas**: también en `CanvasControls`, arriba de todo.
  Un único `resolution` (`RESOLUTIONS` en `client.ts`, agrupado en
  `optgroup` "escritorio"/"celular") maneja tanto la vista previa como el
  export: la vista previa reusa ese mismo aspecto, solo que achicada al
  lado mayor `api/routes_render.py::PREVIEW_LADO_MAYOR` (480px), así que
  elegir un tamaño de celular (vertical) ya se ve vertical en la vista
  previa, no solo al exportar.
- **Gotcha de `uvicorn --reload` en sesiones largas**: el watcher (WatchFiles)
  puede dejar de recargar después del primer reload y quedarse serviendo
  código viejo el resto de la sesión, sin avisar (no tira error, el proceso
  sigue vivo y respondiendo 200). Encima Pydantic ignora en silencio
  cualquier clave que el modelo viejo no conozca, así que un campo nuevo en
  `api/schemas.py` (como pasó con `resize` en un layer) se manda desde el
  frontend, el servidor responde 200, y el resultado sale igual que sin ese
  campo, sin ningún error visible. Si un cambio de comportamiento en `api/`
  o `proun/` no se nota al probar contra el `uvicorn` que ya estaba
  corriendo, no asumas que el código está mal: primero confirma el cambio
  con una llamada directa a `compose`/`spec` en Python (sin HTTP), y si eso
  sí funciona, mata el proceso entero (`taskkill //PID <reloader> //F //T`,
  el PID del *reloader*, no del worker) y arranca `uvicorn` de nuevo antes
  de seguir depurando.
- El mosaico tiene una compensación en `api/routes_render.py`
  (`_sin_explosion_de_mosaico`): el motor salta el resize automático al
  hueco del layout cuando hay `mosaic` sin `resize` propio, así que sin
  esto una foto real (miles de px) más una grilla de 3x3 terminaba en una
  capa de decenas de miles de px. Ver el docstring ahí si vuelve a pasar
  algo raro con mosaico.
- **Segunda pestaña, "recolorear"** (`App.tsx`, switch `vista` en el
  masthead, `.view-switch`): no compone nada nuevo, repinta un wallpaper
  YA exportado con un colormap o como negativo (`recolor.mode`
  "colormap"/"invert"). `WallpaperPicker` es como `SourceFolderPicker`
  pero de selección única (mira `wallpapers/` por default, no
  `fuentes/`), sin tocar ese componente para no mezclarle semántica de
  selección múltiple. `RecolorView.tsx` junta ambos modos en un mismo
  `button-row` (los colormaps de `options.colormaps` más un botón
  "negativo" al final); elegir un colormap pone `mode: 'colormap'`,
  "negativo" pone `mode: 'invert'`, mutuamente excluyentes.
  `api/routes_recolor.py` (`/api/recolor/preview` y `/api/recolor/export`)
  reusa `recolorear.recolorear` tal cual, la misma función que el script
  de línea de comandos (`recolorear.py foto.png --invert`): la GUI y la
  CLI comparten la lógica entera, ninguna reimplementa nada de la otra.

- **JSON: exportar/importar la spec desde el propio GUI** (`SpecIO.tsx`,
  columna izquierda del editor, debajo de `ExportButton`): `POST /api/spec`
  (`api/routes_render.py::spec_as_json`) devuelve el mismo dict que ya arma
  `_spec_dict` para preview/export (antes de `spec.build` normalizarlo), o
  sea el formato exacto que acepta la CLI con `--spec`; valida con
  `spec.build` antes de devolverlo, así que un spec inválido da 400 en vez
  de un archivo roto. "exportar json" descarga ese dict como archivo
  (`proun_<seed>.json`). "importar json" lee un archivo elegido, lo
  parsea con `client.ts::parseSpecJson` (el camino inverso de `toBody`/
  `toLayerDict`) y reemplaza el estado entero del editor con
  `useSpecState::loadState`. Este camino de vuelta es necesariamente con
  pérdida: la spec completa del motor admite cosas que el editor no tiene
  control para mostrar (capas `pool`, `cover`, `region`/`bleed`,
  `resize.scale`/`max_side`, o varias resoluciones/colores/semillas a la
  vez en un solo spec). Donde pasa eso, `parseSpecJson` no falla ni
  descarta en silencio: hace lo mejor posible (por ejemplo, usa la primera
  resolución/color/semilla de una lista) y junta un `warnings: string[]`
  que `SpecIO` muestra en pantalla, para que quede claro qué se aproximó o
  se omitió al importar un JSON escrito a mano o generado por la CLI.
- **Cada export del GUI arma su propia carpeta** dentro de
  `wallpapers/<resolución>/` (`api/routes_render.py::_wallpaper_paths`,
  solo para este flujo, el batch del CLI con `recetas/`/`main.py` sigue
  igual que siempre, con su numeración plana): adentro va la imagen
  (`<nombre>.png`), el mismo JSON que devuelve `/api/spec`
  (`<nombre>.json`) y, si se recolorea desde la pestaña "recolorear",
  todas sus variantes (`<nombre>_inferno.png`, `<nombre>_invertido.png`,
  etc.), porque quedan en la carpeta de la imagen que las originó. El
  nombre sale de un campo "Nombre (opcional)" en `ExportButton.tsx`:
  vacío, usa `wp_<color>_<semilla>` como antes; con texto, se sanea
  (minúsculas, símbolos a guión bajo, tope 60 caracteres). Exportar dos
  veces con el mismo nombre pisa esa carpeta a propósito, es la misma
  composición vuelta a guardar, no un duplicado.
- **`WallpaperPicker` lista todo lo que haya en la carpeta, sin filtrar**:
  la imagen principal y sus variantes recoloreadas aparecen todas como
  miniaturas elegibles, a propósito. Se probó esconder las variantes
  (detectando `<carpeta>_<sufijo>` por nombre) para que la lista no se
  llenara de una entrada por colormap, pero eso bloqueaba un caso de uso
  real: recolorear una variante YA recoloreada (por ejemplo, invertir una
  que ya está en inferno). `recolor.apply` no le importa de dónde salió
  el píxel, solo su brillo, así que cualquier archivo de la carpeta es un
  punto de partida válido.
- **La pestaña "recolorear" también rota/voltea/redimensiona**, además de
  elegir colormap o negativo: controles "Rotar" (0/90/180/270, igual que
  `LayerConfigPanel`) y "Voltear" (↔/↕) aplican `proun.ops.rotate` antes
  de recolorear; "Redimensionar" (la lista de `RESOLUTIONS`, con
  "tamaño original" como default) aplica `proun.ops.resize` en modo
  "fill" (encaja y recorta el sobrante, no deforma) después de rotar,
  para que primero se corrija la orientación y después se encaje a la
  resolución de destino. Todo vive en `api/routes_recolor.py::_preparar`,
  compartido por preview, export y export-all. `RESOLUTIONS` en
  `client.ts` suma pantallas de Nothing Phone (1, 2/2a, 3a/3a Pro, 3)
  junto a las de iPhone que ya había.
- **Botón "descargar todas las variantes"** (`/api/recolor/export-all`):
  genera los colormaps con nombre más el negativo de una sola vez y los
  guarda sin comprimir junto al original, en su misma carpeta, en vez de
  exportarlos uno por uno a mano. No arma un zip, ver `RecolorAllRequest`
  en `api/schemas.py`.
Esta v2.0 local ya cubre todo el editor visual de specs. Movido a v3.0 (hosteada, no ahora): subida/almacenamiento real de imágenes
(sigue siendo una carpeta local en disco por ahora, decidido a propósito:
un upload de verdad implica una historia de storage que no tiene sentido
resolver para una herramienta de un solo usuario en su propia máquina),
auth, storage que no sea disco local, límites de cuota.

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
- **Tabs** ("Lo que trae" / "Instalación" / "Cómo usarlo" / "Mapa del
  código"): cambian con una cortina (blades que se cierran, cambian el
  panel, se abren) y un indicador rojo que se desliza suave hasta la tab
  activa. El indicador es `position:absolute; bottom:0` del contenedor
  `.tabs`, así que si las tabs envuelven a más de una fila queda pegado al
  fondo de TODAS las filas, no de la fila de la tab activa (se ve
  flotando, desconectado). Por eso en `max-width:640px` las tabs no
  envuelven: la fila se vuelve de una sola línea con scroll horizontal
  (`flex-wrap:nowrap` + `overflow-x:auto`). Si se agrega una quinta tab,
  revisar que siga entrando cómoda en ese scroll, no hace falta tocar el
  indicador.
- **Mapa del código** (4ta tab): un `<iframe>` a `docs/ariadne/proun.html`,
  el diagrama interactivo que genera la skill `ariadne` (`ariadne generate
  . --out docs/ariadne --title "Proun" --formats html --theme light
  --max-depth 2 --hide-generated`, corrido desde la raíz del repo).
  `--max-depth 2` es a propósito: sin eso la vista inicial explota en los
  ~1060 nodos de `tests/` (uno por clase/método) y tapa el resto del
  árbol; con profundidad 2 arranca mostrando archivos, y de ahí se puede
  expandir a mano. Ese HTML es generado, no se edita a mano, y hay que
  volver a correr el comando (y commitear el archivo de nuevo) si la
  estructura del proyecto cambia bastante; no hace falta por cada commit
  chico. La UI del propio Ariadne (panel de filtros, colores) no sigue la
  paleta constructivista del sitio a propósito: es una herramienta
  embebida, no una sección de contenido del sitio.
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

## Marca (logo)

Homenaje geométrico directo a "Beat the Whites with the Red Wedge" de El
Lissitzky (sin texto ni las marcas propias del cartel, solo su geometría),
afinado junto con el usuario en varias rondas (arrancó como plano+cuña,
pasó por dos triángulos, después círculo+cuña con campo diagonal, hasta
llegar a esta versión, simétrica, a partir de un boceto que el propio
usuario dibujó): fondo de tinta (`#141210`) con dos esquinas de papel
opuestas (arriba-izquierda y abajo-derecha), un círculo de papel centrado,
y un triángulo rojo (`#d94f3d`) grande e irregular (escaleno) centrado
adentro del círculo y recortado con `<clipPath>` a la forma del círculo,
así sus esquinas quedan ocultas en vez de asomar por fuera. Un solo SVG
(`viewBox 0 0 64 64`, pensado para leerse bien hasta en 16px de favicon),
copiado igual en dos rutas porque son raíces de despliegue distintas:
- `frontend/public/favicon.svg` (favicon del GUI, y también referenciado
  desde el masthead de `App.tsx` junto al wordmark).
- `docs/images/logo.svg` (favicon de `docs/index.html` y su footer).

El wordmark gigante del hero de `docs/index.html` se queda sin el símbolo
a propósito: es un momento tipográfico deliberado, sumarle el ícono ahí
lo recargaría. Si hace falta regenerar o ajustar la geometría, las
coordenadas de los dos polígonos ya están centradas por bounding box
dentro del viewBox; no son arbitrarias, se calcularon rotando cada forma
alrededor de su propio centro y recentrando el conjunto.

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