# Pendientes

Lo que falta. Los siete pendientes originales (limpieza, repetición por
proporciones, manchas, composición alineada, figuras, textos, polaridad y
color transparente) ya están hechos; su historia de diseño quedó en el
historial de commits, no aquí.

---

## Interfaz gráfica en React (v2.0)

Completa para uso local. El editor visual ya cubre todo el modelo de
capas del motor: elegir imágenes a mano (selección múltiple por clic) o
agregar figuras/texto, submenú compactable/expandible de ajustes por capa
(rotar/voltear, opacidad, fusión, color propio, tamaño manual, recorte por
proporción, manchas, acabado propio, repeat lineal y caleidoscopio con
espaciado, mosaico, posición arrastrable, orden de capas, duplicar),
dimensiones del canvas (incluye presets de celular), ajustes globales de
fondo (auto/sólido/degradado + manchas) y acabado (viñeta, grano,
desenfoque, contraste, brillo, saturación, veladura, manchas), parámetros
del lote (layout, color, recoloreado, semilla) y exportar. Detalle en
`CLAUDE.md`, sección "v2.0: interfaz gráfica en React".

La subida real de imágenes se movió a v3.0 (hosteada): mientras sea local
de un solo usuario, una carpeta en disco alcanza, no hace falta resolver
storage.

## Logo de Proun

Hecho. Homenaje geométrico directo a "Beat the Whites with the Red Wedge"
de El Lissitzky, afinado en varias rondas junto con el usuario (incluido
un boceto suyo a mano): fondo de tinta con dos esquinas de papel opuestas,
un círculo de papel centrado, y un triángulo rojo grande e irregular
centrado adentro del círculo y recortado a su forma con `<clipPath>`, así
sus esquinas quedan ocultas en vez de asomar. Un solo SVG (`docs/images/logo.svg` y
`frontend/public/favicon.svg`, mismo contenido, copiado en los dos porque
son raíces de despliegue distintas): favicon del GUI y de `docs/`,
encabezado del GUI (`App.tsx`, junto al wordmark) y footer de
`docs/index.html`. El wordmark grande del hero se queda como está, sin el
símbolo, a propósito (es un momento tipográfico deliberado, sumarle el
ícono ahí lo recargaría).