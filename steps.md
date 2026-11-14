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

### A. Hostear landing + GUI en Bakery (decidido 2026-11-14)
- **Decisión de Remi:** GUI público en `proun.remlam.dev` detrás de
  Cloudflare Access (lista de correos, como Tabularium); `/docs` (landing)
  abierto con una app de Access aparte en modo Bypass para esa ruta. Corre
  en **Pixilate** (WSL), por el túnel de `29.Bakery/publicacion/` (red del
  host, destino `http://localhost:<puerto>` configurado en el panel).
  Consecuencia aceptada: la landing también se cae cuando Pixilate se
  apaga o reinicia. Subida de imágenes: opcional, después del despliegue.
- **Hecho, endurecimiento de la API (sin commit):**
  - `api/paths.py`: toda ruta del cliente (carpeta, `src` de capa, `font`
    de texto, `output`, wallpaper a recolorear, miniatura) tiene que caer
    en `fuentes/` o `wallpapers/`, o en las de `PROUN_RAICES`
    (`os.pathsep`). Antes la API leía cualquier imagen del disco y
    escribía PNG junto a cualquier ruta. Ojo en local: otra carpeta
    necesita `PROUN_RAICES`.
  - `api/main.py`: sin Swagger/ReDoc/OpenAPI (chocaba con `/docs`).
  - `routes_render.LADO_MAXIMO = 4096` en preview, export, spec y
    recolor; miniaturas de 16 a 512 px.
  - 12 pruebas nuevas en `tests/test_api.py`; 973 en verde.
  - Commit sugerido: `fix(api): encierra rutas del cliente, quita Swagger y topa la resolución`
- **Siguiente:**
  1. FastAPI sirve `frontend/dist` en `/` y `docs/` en `/docs`
     (`StaticFiles`, sin Caddy), con cabeceras `X-Content-Type-Options`,
     `frame-ancestors`; HSTS desde Cloudflare.
  2. Dockerfile + compose con versión fija, sin `--reload`, usuario no
     root, `fuentes/` de solo lectura y `wallpapers/` en volumen con
     nombre, `127.0.0.1:<puerto>` en el WSL. Registrar el puerto con
     `port-registry`.
  3. Checklist de `ciberseguridad` completo: `pip-audit`, `npm audit
     --omit=dev`, auditoría de repo completo por subagente. Pendientes de
     riesgo bajo detrás de Access: `mosaic.grid` y `recolor.smooth` sin
     tope (CPU).
  4. Copiar `fuentes/` (220 MB) a Pixilate (`bakery`), levantar sin
     publicar y probar por túnel SSH.
  5. Remi en el panel: hostname en el túnel, app de Access en
     `proun.remlam.dev` y app Bypass en `proun.remlam.dev/docs`.
  6. Verificar desde datos móviles: `/docs` abre sin login, `/` y `/api/*`
     piden login. Anotar en `29.Bakery/steps.md`.
  7. Canonical y `og:` (con `images/obras/penrose-1600.webp`) en la
     landing, `launch-checklist`.

### B. Ideas de retro-art-studio (solo inspiración: sin licencia clara)
- Halftone CMYK con ángulo de trama por tinta (ellos no aplican ángulos y
  aproximan K; nosotros ya tenemos `_cmyk` con negro real).
- Tramado Floyd-Steinberg nativo de Pillow (ellos solo Bayer 4x4).
- Desfase real por canal (aberración cromática, glitch) con
  `ImageChops.offset`.
- Tilt-shift; cuadrícula de figuras por luminancia (combina con `shapes`).
- Filtros focales tipo ArcGIS (mediana, bordes) además del k-means.
- Otras imposibles para `iso`: escalera de Penrose, cubo imposible.
