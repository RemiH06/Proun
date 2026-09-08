# Pendientes

Lo que falta. Los siete pendientes originales (limpieza, repetición por
proporciones, manchas, composición alineada, figuras, textos, polaridad y
color transparente) ya están hechos; su historia de diseño quedó en el
historial de commits, no aquí.

---

## Calendario para imprimir

Un procedimiento nuevo (script propio, al estilo de `diagnosticar.py` o
`inspeccionar.py`, no una operación de capa) que arme un calendario en
formato de impresión: doce imágenes, una por mes, tomadas de `fuentes/` o
de wallpapers ya generados. Falta decidir el layout (una hoja por mes con
grilla de días superpuesta, o una sola lámina con las doce), el tamaño de
papel y márgenes de impresión, y si la grilla de fechas se dibuja con
Pillow directo o se apoya en algo de `ops/text.py` para los números.

## Interfaz gráfica en React (v2.0)

No urgente: se hace después de terminar todo lo demás en este documento.
Muchas decisiones siguen abiertas (FastAPI vs Flask, almacenamiento de
`fuentes/`, estrategia de previsualización). El detalle de qué implica está
en `CLAUDE.md`, sección "v2.0: interfaz gráfica en React"; esta entrada es
solo el marcador de prioridad.