# Pendientes

Cosas acordadas pero no implementadas. Cada una debería entrar como un módulo
nuevo en `wpgen/ops/`, siguiendo el mismo contrato que los demás: recibe una
especificación validada, devuelve una capa RGBA y no toca el generador aleatorio
fuera de `plan`.

Orden sugerido: 3, 4, 5, 1, 2. Los tres primeros son los que hacen falta para
reproducir el fondo de referencia; las figuras y los textos son features nuevas.

---

## 1. Figuras geométricas

Generar figuras como capas propias, sin imagen de origen, para lograr el efecto
de vidrios de color sobre un fondo en blanco y negro.

### Parámetros pedidos

| parámetro | qué controla |
|---|---|
| `size` | tamaño, con la misma convención px/fracción del resto |
| `shape` | forma: rectángulo, círculo, triángulo, polígono de n lados, quizá formas libres |
| `color` | color propio, independiente del color del lote |
| `opacity` | transparencia, la clave del efecto de vidrio |
| `rate` | ratio de aparición: probabilidad o cantidad de figuras por wallpaper |
| `overlap` | cuánto se permite que se solapen entre ellas y con las imágenes |
| `outline` | contorno delineado sólido |

### El contorno

Detalle importante: no es un borde en el perímetro real de la figura, sino un
perímetro que vive un poco hacia adentro. Hay que parametrizar al menos:

- `inset`: qué tanto se mete hacia adentro respecto del borde real
- `width`: grosor de la línea
- `color`: color del contorno, que puede diferir del relleno
- `opacity`: si el contorno participa o no de la transparencia del relleno

Ojo con el orden de composición: si el relleno es semitransparente y el contorno
también, donde se solapan van a sumar opacidad. Probablemente convenga dibujar
figura y contorno en una capa aparte y aplicar la opacidad al conjunto.

### Efecto vidrio de color

Para que se lea como vidrio sobre blanco y negro hacen falta dos cosas que ya
existen y una que no:

- las imágenes van con `recolor.mode = "grayscale"` (ya existe)
- las figuras van con `blend` `multiply` o `screen` y opacidad media (ya existe)
- falta que las figuras ignoren el color del lote o lo deriven de otra manera,
  por ejemplo un desfase de matiz respecto del color principal

### Preguntas abiertas

- ¿Las figuras entran en `sources` como un tipo de capa más, o van en una clave
  aparte tipo `shapes`? Lo primero reusa todo el pipeline pero obliga a que
  `src` sea opcional.
- ¿El sorteo de cuántas figuras aparecen va en `plan`? Debería, para que la
  semilla las reproduzca.
- ¿`overlap` se resuelve rechazando posiciones que chocan, o empujando? Lo
  primero es más simple pero puede no converger con muchas figuras.

---

## 2. Textos

Mensajes que aparezcan en el collage de la misma manera que las imágenes y las
figuras: misma posición, rotación, escala, recoloreado y fusión.

### Lo que ya está decidido

- El texto se rasteriza a una capa RGBA y de ahí en adelante pasa por el mismo
  pipeline que cualquier otra capa.
- Hereda `position`, `rotate`, `opacity`, `blend`, `color` y `recolor`.

### Lo que falta decidir

- Cómo se ve el texto: fuente, tamaño relativo al lienzo, interlineado, si se
  ajusta a un ancho máximo o se escribe en una sola línea.
- De dónde salen las fuentes. Pillow necesita una ruta a un `.ttf`. ¿Se declara
  en la especificación, se busca en el sistema, o se empaqueta una por defecto?
- Si un texto puede traer contorno como las figuras, y si comparte código con
  ellas.
- Si `sources` puede tener una lista de frases de las que se sortea una, con la
  semilla, igual que se sortea qué imágenes entran.
- Qué pasa si la fuente no tiene los glifos: acentos, ñ, cualquier alfabeto no
  latino. Hay que fallar con un mensaje claro, no dibujar cuadritos.

---

## 3. Repetición por proporciones

Distinto de `mosaic`. El mosaico llena un área con piezas pegadas borde con
borde; esto estampa una secuencia de copias con un paso fraccionario, de modo
que la imagen se solape consigo misma.

### El paso

El desplazamiento entre copia y copia se expresa como proporción de la propia
imagen, no en píxeles:

- `1` deja la copia justo donde termina la anterior, pegadas sin solaparse
- `0.5` la corre media imagen, así que se solapan a la mitad
- `-0.33` la corre un tercio de imagen en dirección contraria

Al ser proporcional, funciona igual con una imagen de 300 px que con una de 4000.

### Forma tentativa

```json
{
  "repeat": {
    "step": [0.5, 0],
    "times": 4,
    "mirror": "alternate",
    "blend": "multiply",
    "fade": 0.2
  }
}
```

- `step`: paso en x e y. `[0.5, 0]` repite a la derecha, `[0, 0.4]` hacia abajo,
  `[-0.33, -0.33]` en diagonal hacia arriba a la izquierda.
- `times`: cuántas copias además de la original.
- `mirror`: `none`, `alternate` (espeja copias impares, que es lo que da la
  simetría del fondo de referencia), o quizá `all`.
- `blend`: cómo se fusionan las copias entre sí, antes de pegar el conjunto al
  lienzo. Con `multiply` sobre blanco es donde aparece el efecto de veladura.
- `fade`: opcional, bajar opacidad progresivamente en cada copia.

### Preguntas abiertas

- ¿Se puede pedir más de una dirección a la vez, por ejemplo una secuencia hacia
  la derecha y otra hacia abajo formando una cruz? Podría ser `step` como lista
  de pasos en vez de un solo par.
- La simetría del fondo de referencia parece ser espejo respecto del eje, no
  solo copia desplazada. Hay que distinguir "copia corrida" de "copia espejada
  y corrida", que es lo que genera esas formas de mariposa.
- ¿Va antes o después de `rotate` en el pipeline? Repetir y luego girar el
  conjunto no es lo mismo que girar y luego repetir.
- Interacción con `mosaic`: probablemente sean excluyentes en una misma capa, y
  conviene validarlo y decirlo con un mensaje claro.

---

## 4. Manchas, humedad y suciedad

En el fondo de referencia varias piezas se ven manchadas o comidas por los
bordes, como papel con humedad. No hay un nombre único: en papel eso se llama
**foxing**, en impresión y diseño se le dice **grunge** o **distress**, y el velo
lechoso encima de una imagen es una **veladura**. En el código lo llamaríamos
`stain`.

### Cómo se haría

Modulando el canal alfa de la capa con ruido en varias escalas. Pillow lo hace
barato: `Image.effect_noise` a distintos tamaños, desenfocado y escalado, da un
ruido de nubes; ese mapa se multiplica contra el alfa existente.

Parámetros probables:

- `amount`: qué tan agresiva es la mancha
- `scale`: tamaño de las manchas, de moteado fino a nubes grandes
- `edges`: si el efecto se concentra en los bordes de la pieza o se reparte
- `threshold`: para que sea mancha con borde definido y no un degradado suave

### Preguntas abiertas

- ¿Es una operación de capa (`ops/stain.py`) o un acabado global que va en
  `finish`? Creo que ambas: una capa manchada y un lienzo manchado son efectos
  distintos y se pueden querer juntos.
- El ruido tiene que salir de la semilla del plan para que sea reproducible, o
  el mismo wallpaper saldría distinto en cada corrida.

---

## 5. Polaridad y color transparente

El fondo de referencia no funciona como nuestro `duotone` actual. Ahí el lienzo
es claro, el blanco de cada imagen actúa como transparente y solo lo oscuro se
acumula al solaparse. Es tinta sobre papel, no luz sobre negro.

Generalización acordada: no es blanco y negro. **Cualquier color puede volverse
el transparente** con la configuración correcta, y el fondo puede ser cualquier
color. Lo que hay que parametrizar no es "modo papel" sino la polaridad: qué
extremo del rango tonal desaparece y cuál se acumula. `tones.invert` más
`blend: multiply` ya lo consiguen a mano; falta decidir si eso merece un
parámetro propio.

Ya se puede armar con lo que existe:

```json
{
  "background": "#ffffff",
  "defaults": {
    "recolor": { "mode": "grayscale", "normalize": true },
    "blend": "multiply"
  }
}
```

Pero conviene dejarlo como preajuste con nombre, porque es un modo de trabajo
completo y no un parámetro suelto. Falta decidir:

- Si se llama `preset` y hay varios (`tinta`, `duotono`, `vidrio`), o si es solo
  un ejemplo documentado en el README.
- Si el color principal del lote debería teñir la tinta en vez de ir en escala de
  grises, para que el nombre del archivo siga significando algo. Un wallpaper
  totalmente gris con `_3ba7ff` en el nombre es engañoso.
- Qué color hace de transparente y cómo se declara: puede ser el color
  principal, uno fijo por capa, o el tono extremo que resulte de `tones`.
- Cómo interactúa con `finish.vignette`, que hoy oscurece las esquinas y sobre
  blanco se vería mal.