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
- **Hecho, despliegue (sin commit):**
  - `api/main.py` sirve `docs/` en `/docs/` (`/docs` redirige con 308
    relativo) y `frontend/dist` en `/` si existe; cabeceras `nosniff`,
    `X-Frame-Options`, `frame-ancestors`, `Referrer-Policy`. Pruebas en
    `tests/test_api.py::SitioPublicado`.
  - `Dockerfile` (dos etapas, `node:24.22.1-alpine` y
    `python:3.13.17-slim-trixie`, usuario sin privilegios),
    `.dockerignore` en lista blanca, `compose.yml` (`127.0.0.1:8031`,
    `read_only`, `cap_drop`, 2 CPU, 2 GB, `fuentes/` de solo lectura,
    volumen `wallpapers`). Puerto 8031 en `PORTS.md` de SkillShot.
  - `pip-audit`: Pillow 10.4.0 tenía 69 CVE; con 13.0.0 ninguno y las 979
    pruebas pasan igual. `requirements.txt` pide `>=13.0`. En Aerilate
    sigue la 10.4: `pip install -U "Pillow>=13"`.
  - `npm audit --omit=dev`: 0.
- **Siguiente:**
  1. Hecho: auditoría de repo completo. Arreglados A1 a A4 (caché con
     tope, miniatura sin caché, `src` solo archivo, topes de píxeles,
     octavas en `clouds`, 64 capas, cuerpo de 1 MB), M3 (cuota), B1 (sufijo
     saneado), B5 (`tmpfs` y `pids_limit`), B6 (`obras.py` fuera de la
     imagen), `uvicorn` sin `[standard]`. Ver `CLAUDE.md`. Pendientes:
     - M2: validar el JWT de Access en el origen (defensa en profundidad
       si el túnel o Access se configuran mal). Hacerlo cuando exista la
       app de Access (hace falta su AUD y el team domain).
     - M1: sin semáforo de concurrencia: `cpus: 2` ya topa el CPU y los
       topes por operación acotan cada petición.
     - B2 (rutas `/app/...` en respuestas) y B4 (lock con hashes, digest
       de imágenes): bajos, sin hacer.
     - B3: `steps.md` está versionado pese al `.gitignore` (revela el
       esquema de despliegue): `git rm --cached steps.md`.
  2. Hecho (2026-11-14): clon en `~/srv/proun` del WSL de Pixilate
     (`7878783`), `fuentes/` copiada (165 archivos), `docker compose up -d
     --build`. Verificado sin publicar: escucha solo `127.0.0.1:8031`,
     healthy, uid 10001, ~117 MB tras un render, `/docs` 308 a `/docs/`,
     Swagger y `obras.py` en 404, cabeceras puestas, `/etc` da 400,
     preview y export reales en ~0.5 s, `fuentes/` de solo lectura.
     Capturas por túnel SSH: GUI y landing cargan sin errores.
     Desplegar cambios: `cd ~/srv/proun && git pull && docker compose up
     -d --build`.
  3. Hecho (2026-11-14): publicado en `proun.remlam.dev`. Access en todo
     el hostname, Bypass en `/docs`. El 1033 inicial era un CNAME `proun`
     que apuntaba a un túnel creado por error y luego borrado.
  4. Hecho: verificado desde fuera. `/docs/` 200 sin login; `/` y
     `/api/*` 302 al login; `/docs/../api` también al login; `/DOCS/`
     pasa el Bypass pero el origen da 404. Anotado en `29.Bakery/steps.md`.
     Sin HSTS en la respuesta: `.dev` ya está precargado en los
     navegadores.
  4b. Worker de `/docs` (opción A, 2026-11-14): `worker/docs.js` sirve la
     landing desde GitHub Pages bajo `proun.remlam.dev/docs`. 9 pruebas
     con `node --test worker/docs.test.mjs` y probado contra Pages en
     vivo. Falta: Remi lo crea en el panel (Workers, pegar `docs.js`,
     ruta `proun.remlam.dev/docs*`) y se verifica desde fuera.
  4c. Portada: el hero vuelve a la imagen de antes (`proun_ss1.png`,
     recuperada de `ff3f305`) como `docs/images/portada-{800,1600}.webp`,
     encuadre `50% 30%`. Se queda el velo de 0.64 (contraste del
     subtítulo). La Penrose sigue en la primera sala.
  5. Texto de ayuda de `SourceFolderPicker`: dice "relativa o absoluta";
     publicado solo valen `fuentes/` y `wallpapers/`.
  6. Canonical y `og:` (con `images/obras/penrose-1600.webp`) en la
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
