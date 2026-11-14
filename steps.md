# Traspaso (2026-11-14)

Lista de Remi para Proun, en orden. Detalle técnico de lo hecho en
`CLAUDE.md` (secciones de `kmeans`, `channels` con tintas y figuras iso).

## Hecho (2026-11-14, segunda sesión; sin commit, Remi commitea)

Landing rehecha como sala de exposición (pendiente A). Detalle en la
sección de `docs/index.html` de `CLAUDE.md`.
- Tres salas en vertical y una colección en carrusel, con señalética en
  cirílico (Unbounded) y fichas de sala con receta y semilla.
- Obras reales generadas por `docs/obras.py` a `docs/images/obras/`.
- Specs nuevos `json/penrose.json`, `cuatricromia.json` y `campus.json`.
- `json/ss4.json` estaba roto desde que se movió a `json/` (rutas
  `fuentes/` en vez de `../fuentes/`): corregido.
- La galería vieja y el README apuntaban a `proun_ss2..4.png`, que nunca
  se subieron: ahora usan las obras. `proun_ss1.png` quedó sin uso y se
  borró.
- `tests/test_docs.py`: rutas locales de la landing, obras de `obras.py`,
  specs de `json/`. 961 pruebas en verde.
- Verificado con Playwright: escritorio, 390x844, 360x740, 844x390, sin
  CDN y con movimiento reducido.

Commit sugerido:
`feat(docs): landing como sala de exposición con obras generadas por el motor`

## Pendiente

### A. Hostear landing + GUI en Bakery
- Pedido: ambos, la landing (que son los docs) y la herramienta GUI, en
  algo como `proun.remlam.dev` con los docs en `/docs`.
- Decisión abierta: el GUI hoy lee y escribe carpetas del disco
  (`fuentes/`, `wallpapers/`) sin auth. Publicarlo abierto es lo que se
  había movido a v3.0 (subida de imágenes, auth, almacenamiento, cuotas).
  Opciones: detrás de Tailscale (sin exponer), o público con auth y
  subida real. Preguntar a Remi antes de construir.
- Skills: `hosteo`, `ciberseguridad` (antes de exponer nada),
  `port-registry` (8030 API, 5183 frontend), `bakery`, `hardware`.
- Al final: revisar enlaces, agregar canonical y `og:` (con
  `images/obras/penrose-1600.webp`) según la URL definitiva.

### B. Ideas de retro-art-studio (solo inspiración: sin licencia clara)
- Halftone CMYK con ángulo de trama por tinta (ellos no aplican ángulos y
  aproximan K; nosotros ya tenemos `_cmyk` con negro real).
- Tramado Floyd-Steinberg nativo de Pillow (ellos solo Bayer 4x4).
- Desfase real por canal (aberración cromática, glitch) con
  `ImageChops.offset`.
- Tilt-shift; cuadrícula de figuras por luminancia (combina con `shapes`).
- Filtros focales tipo ArcGIS (mediana, bordes) además del k-means.
- Otras imposibles para `iso`: escalera de Penrose, cubo imposible.
