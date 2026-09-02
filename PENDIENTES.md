# Pendientes

Lo que falta. Los siete pendientes originales (limpieza, repetición por
proporciones, manchas, composición alineada, figuras, textos, polaridad y
color transparente) ya están hechos; su historia de diseño quedó en el
historial de commits, no aquí.

---

## 8. Selección ponderada por proporción

Cuando una capa toma su fuente de un pool (glob o lista), sortear con más
probabilidad las imágenes cuya proporción calce mejor con el hueco de
destino (el `crop.aspect` de la capa), en vez de un sorteo parejo entre
todas. No puede ser "siempre la que mejor calza": eso mataría la variedad
entre semillas del mismo lote. Tiene que ser una elección aleatoria
ponderada, con `auto_rotate` (ya resuelto en `crop.py`) como una entrada
más: cada candidata compite con su mejor orientación antes de pesarse, no
solo la que trae de fábrica.

## Caleidoscopio en repeat

Las figuras (y las fotos) deberían poder repetirse en simetría radial: la
misma pieza girando alrededor de un punto, no sobre su propio centro.
`ops/repeat.py` ya hace giro acumulado por copia; falta que el giro sea
alrededor de un `pivot` declarado y que se pueda pedir por `sectors` en vez
de por `times`. Se puede resolver dentro del mismo módulo.

## Sueltos

- **`--overwrite` compara solo por nombre.** Como el nombre lleva índice,
  color y semilla, un cambio en las fuentes o en cualquier parámetro que no
  viaje en el nombre (modo de recoloreado, layout, fondo) deja el archivo
  viejo como vigente y lo omite. Se resolvería con un hash de la
  configuración en el nombre, a costa de que el nombre deje de ser legible.
- **Orden explícito entre capas.** Hoy el orden lo decide la semilla y solo
  se puede influir con `blend` y `opacity`. Un `z` por capa daría control,
  pero hay que pensar cómo convive con el revuelto aleatorio.
- **`stain` solo existe como operación de capa**, no como acabado del
  lienzo entero (aunque `background.stain` ya cubre el caso de manchar el
  fondo, que era el uso real que necesitábamos).