# Pendientes

Cosas acordadas pero no implementadas. Cada una debería entrar como un módulo
nuevo en `proun/ops/`, siguiendo el mismo contrato que los demás: recibe una
especificación validada, devuelve una capa RGBA y no toca el generador aleatorio
fuera de `plan`.

No queda ningún pendiente de los originales. El 7 (composición alineada), el
1 (figuras geométricas) y el 2 (textos) ya están.

Ya hechos:

- **6, comando de limpieza.** `--clean` con filtros opcionales de
  `--resolutions`, `--colors` y `--seeds`.
- **3, repetición por proporciones.** `ops/repeat.py`, con lista de pasos,
  espejado alterno, giro acumulado por copia, desvanecido y modo de fusión.
- **4, manchas y humedad.** `ops/stain.py`, ruido de nubes por octavas que come
  el canal alfa, con umbral, sesgo hacia los bordes e inversión. Pendiente
  menor: existe solo como operación de capa, no como acabado del lienzo entero.
- **7, composición alineada.** `layout.pack` empaqueta con skyline bottom-left:
  cada pieza cae en el hueco más alto disponible dentro de un ancho fijo, sin
  solaparse, tocando a sus vecinas. La posición se calcula en `compose.prepare`
  y no en `plan`, porque depende del tamaño real en píxeles de cada capa, que
  ahí todavía no se conoce. Limitaciones que quedaron documentadas y no se
  resolvieron: el algoritmo puede dejar huecos entre grupos de piezas (no
  reordena para llenar espacio sobrante), no recorta piezas para que encajen
  exacto, y reproduce la composición solo entre resoluciones del mismo
  aspecto; una vertical y una horizontal con la misma semilla dan collages
  distintos, porque el ancho real del bloque cambia con la forma del lienzo.
  Las capas con `cover`, `position` o `region` quedan fuera del bloque.
- **1, figuras geométricas.** `ops/shapes.py`. Entran en `sources` con
  `"shape"` en vez de `"src"`, y comparten toda la maquinaria de una capa
  normal: `resize`, `rotate`, `repeat`, `mosaic`, `stain`, `blend`, `opacity`,
  `position`, `region`, `bleed`, `copies`. La decisión clave fue que no
  hornean color: se generan en escala de grises (relleno blanco, contorno en
  un gris intermedio) y pasan por el mismo `recolor` que las fotos, así que
  heredan el color del lote o su propia lista de colores sin código aparte, y
  siguen siendo reutilizables entre los colores de un mismo wallpaper. Cinco
  formas: rect, circle, triangle, diamond, polygon (3 a 12 lados). El
  contorno se traza sobre una copia de la silueta encogida hacia el centro
  por `inset`, así que vive hacia adentro del borde real y no en el borde.
  Dos parámetros nuevos que quedaron generales, no solo de figuras: `rate`
  (probabilidad de que la capa aparezca en un wallpaper dado; sin declararlo
  vale 1 y no consume el generador aleatorio, así que ninguna especificación
  existente cambió) y `overlap` (rechazo de posiciones por aproximación de
  tamaño; sin declararlo, cero cambios de comportamiento). `overlap` es una
  aproximación documentada: compara contra el tamaño de respaldo que sortea
  `layout.sizes`, así que una capa con `resize`/`crop`/`mosaic` propio, cuyo
  tamaño real no se conoce hasta `prepare`, no se mide con precisión contra
  las demás.

  Quedó pendiente el caleidoscopio (repetición con giro alrededor de un
  punto, no del propio centro) que se había anotado como parte de este ítem;
  se puede retomar extendiendo `ops/repeat.py` con `pivot` y `sectors` cuando
  haga falta, y serviría igual para figuras que para fotos.
- **2, textos.** `ops/text.py`, con el mismo mecanismo que las figuras: sale
  en escala de grises (relleno blanco, contorno en un gris intermedio si se
  pide) y pasa por el mismo `recolor` que fotos y figuras. Entra en `sources`
  con `"text"` en vez de `"src"` o `"shape"`; los tres tipos son excluyentes
  entre sí. `text` puede ser una lista, y se sortea una frase por wallpaper
  igual que `color`, incluso anidada dentro de un objeto de configuración
  (`{"text": [...], "weight": "bold"}`). `wrap` corta en varios renglones;
  sin declararlo, todo sale en una sola línea sin importar la longitud.

  Se resolvió la pregunta de dónde salen las fuentes empaquetando una:
  **Big Shoulders** (licencia OFL, en `proun/assets/fonts/`), así que
  funciona igual en Windows, macOS y Linux sin depender de qué haya
  instalado el sistema. Se probó que cubre acentos, diéresis, ñ y los signos
  de apertura del español; no hay verificación automática de que una fuente
  propia (vía `font`) cubra un alfabeto no latino, así que si faltan glifos,
  Pillow los va a dibujar como un cuadro vacío en silencio.

  El contorno de texto se traza en el borde real del glifo (con el trazo
  nativo de Pillow), a diferencia del contorno de las figuras, que vive hacia
  adentro: un glifo no es convexo, y encogerlo de forma confiable pediría
  morfología de imagen que no valía la pena para este alcance.
- **8, selección ponderada por proporción.** Cuando una capa toma su fuente de
  un pool (glob o lista), sortear con más probabilidad las imágenes cuya
  proporción calce mejor con el hueco de destino (el `crop.aspect` o
  `resize.size` de la capa), en vez de un sorteo parejo entre todas. No puede
  ser "siempre la que mejor calza": eso mataría la variedad entre semillas del
  mismo lote. Tiene que ser una elección aleatoria ponderada, con `auto_rotate`
  (ya resuelto en `crop.py`) como una entrada más: cada candidata compite con
  su mejor orientación antes de pesarse, no solo la que trae de fábrica.
  Preguntas abiertas: cómo se define "qué tan bien calza" (¿área retenida
  tras el crop? ¿distancia de aspecto?), si el peso es lineal o exponencial
  (para que un mal calce casi nunca salga, o para que siga teniendo una
  oportunidad), y si esto reemplaza o convive con el sorteo uniforme que ya
  existe cuando no se declara ningún hueco de destino explícito.
- **Colocación por capa.** `region` acota dónde puede caer una capa al azar,
  `bleed` cuánto puede salirse del lienzo en fracción de su propio tamaño, y
  `color` acepta una lista de la que se sortea uno por wallpaper.
- **5, polaridad y color transparente.** `ops/transparency.py`. Cualquier color
  puede volverse transparente, con tolerancia y suavidad, y de ahí sale la
  polaridad. No hay preset: la combinación de tinta sobre papel son cuatro
  claves documentadas en `main.py`.

Cuando estén el 4 y el 5, el examen final es reproducir el fondo de referencia
del amigo: fondo claro, imágenes en escala de grises acumulándose por multiply,
piezas repetidas y espejadas sobre sí mismas, y manchas de humedad en los
bordes.

---

## Sueltos

- **README serio** con la nota sobre Lissitzky y el Proun, siguiendo el formato
  de la plantilla con encabezado ASCII y badges.
- **`--overwrite` compara solo por nombre.** Como el nombre lleva índice, color
  y semilla, un cambio en las fuentes o en cualquier parámetro que no viaje en
  el nombre (modo de recoloreado, layout, fondo) deja el archivo viejo como
  vigente y lo omite. Se resolvería con un hash de la configuración en el
  nombre, a costa de que el nombre deje de ser legible.
- **Orden explícito entre capas.** Hoy el orden lo decide la semilla y solo se
  puede influir con `blend` y `opacity`. Un `z` por capa daría control, pero
  hay que pensar cómo convive con el revuelto aleatorio.