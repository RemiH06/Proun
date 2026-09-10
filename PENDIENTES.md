# Pendientes

Lo que falta. Los siete pendientes originales (limpieza, repetición por
proporciones, manchas, composición alineada, figuras, textos, polaridad y
color transparente) ya están hechos; su historia de diseño quedó en el
historial de commits, no aquí.

---

## Interfaz gráfica en React (v2.0)

Completa para uso local. El editor visual ya cubre todo el modelo de
capas del motor: elegir imágenes a mano (selección múltiple por clic) o
agregar figuras/texto, submenú de ajustes por capa (rotar/voltear,
opacidad, fusión, color propio, recorte por proporción, manchas, repeat
lineal y caleidoscopio con espaciado, mosaico, posición arrastrable,
orden de capas, duplicar), ajustes globales de fondo (auto/sólido/
degradado + manchas) y acabado (viñeta, grano, desenfoque, contraste,
brillo, saturación, veladura, manchas), parámetros del lote (layout,
color, recoloreado, semilla) y exportar. Detalle en `CLAUDE.md`, sección
"v2.0: interfaz gráfica en React".

La subida real de imágenes se movió a v3.0 (hosteada): mientras sea local
de un solo usuario, una carpeta en disco alcanza, no hace falta resolver
storage.

## Logo de Proun

Todavía no existe una marca propia, solo el wordmark en Big Shoulders que
ya usa `docs/index.html`. Falta decidir si el logo es puramente tipográfico
o si suma una marca geométrica (ver la conversación del 2026-09-10 para la
propuesta: dos o tres planos geométricos simples superpuestos y rotados,
en tinta y rojo sobre papel, a la manera de las composiciones axonométricas
reales de El Lissitzky y del mecanismo de capas con rotación/overlap que ya
usa el motor).