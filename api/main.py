"""App FastAPI de Proun: envuelve proun.spec/proun.compose para el GUI.

Sin login propio y sin CORS. En desarrollo, el frontend de Vite llega acá
por proxy (`uvicorn api.main:app --reload --port 8030`). Publicado, esta
misma app sirve todo desde un solo origen: la API en `/api`, la landing en
`/docs` y el build del frontend en `/`; el login lo pide Cloudflare Access
delante, y esta app solo revisa el token que Access le pasa (`access.py`).
"""

from __future__ import annotations

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from proun import layout
from proun.errors import SpecError
from proun.ops import blend, iso, recolor, shapes

from . import access, routes_recolor, routes_render, routes_sources
from .paths import PROJECT_ROOT

# Sin Swagger/ReDoc/OpenAPI: `/docs` es la landing en el sitio publicado, y
# el esquema de la API no tiene por qué quedar a la vista de quien entre.
app = FastAPI(title="Proun API", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(routes_sources.router, prefix="/api")
app.include_router(routes_render.router, prefix="/api")
app.include_router(routes_recolor.router, prefix="/api")


@app.get("/api/options")
def options() -> dict:
    """Los controles del frontend leen sus opciones de acá en vez de tener
    una lista aparte que se pueda desincronizar de `proun.layout`/`recolor`/
    `proun.ops.blend`/`proun.ops.shapes`."""
    return {
        "layout_modes": list(layout.MODES),
        "recolor_modes": list(recolor.MODES),
        "blend_modes": list(blend.MODES),
        "shape_kinds": list(shapes.KINDS),
        # Figura iso -> [mínimo, por defecto, máximo] de su `size`.
        "iso_figures": {nombre: list(rango) for nombre, rango in iso.FIGURAS.items()},
        "colormaps": list(recolor.COLORMAPS),
    }


@app.exception_handler(SpecError)
async def _spec_error_handler(request: Request, exc: SpecError) -> JSONResponse:
    # SourceError es subclase de SpecError: un solo manejador cubre las dos,
    # y el mensaje ya viene en español desde el motor, no se reescribe.
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# Un spec real del editor pesa unos KB: 1 MB sobra y corta cuerpos gigantes
# antes de que Pydantic los parsee. Solo mira Content-Length (Cloudflare lo
# manda); un cuerpo por chunks sin ese encabezado no se frena aquí.
MAX_CUERPO = 1_000_000


@app.middleware("http")
async def _tope_de_cuerpo(request: Request, call_next):
    largo = request.headers.get("content-length", "")
    if largo.isdigit() and int(largo) > MAX_CUERPO:
        return JSONResponse(status_code=413, content={"detail": "la petición pesa más de 1 MB"})
    return await call_next(request)


VERIFICADOR = access.desde_entorno()


# Va después del tope de cuerpo y antes de las cabeceras: el último
# middleware declarado es el de más afuera, así que el token se revisa antes
# que nada y un 403 también lleva las cabeceras de seguridad.
@app.middleware("http")
async def _token_de_access(request: Request, call_next):
    if VERIFICADOR is None or access.es_publica(request.url.path):
        return await call_next(request)
    token = request.headers.get(access.ENCABEZADO)
    if not token:
        return JSONResponse(status_code=403, content={"detail": "falta el token de Cloudflare Access"})
    try:
        # En un hilo: pedir las llaves a Cloudflare es una llamada de red
        # bloqueante y no debe frenar las demás peticiones.
        await run_in_threadpool(VERIFICADOR, token)
    except jwt.PyJWKClientConnectionError:
        return JSONResponse(status_code=503, content={"detail": "no se pudieron consultar las llaves de Access"})
    except (jwt.InvalidTokenError, jwt.PyJWKClientError):
        return JSONResponse(status_code=403, content={"detail": "token de Cloudflare Access inválido"})
    return await call_next(request)


# Cabeceras en toda respuesta: `nosniff` para que el navegador no adivine
# tipos (una imagen tratada como script), y nadie de otro origen puede meter
# la app en un iframe (clickjacking). HSTS lo pone Cloudflare, que es quien
# termina el TLS. Sin CSP completa: la landing carga Motion de jsdelivr.
CABECERAS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Content-Security-Policy": "frame-ancestors 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@app.middleware("http")
async def _cabeceras(request: Request, call_next):
    respuesta = await call_next(request)
    respuesta.headers.update(CABECERAS)
    return respuesta


@app.get("/docs", include_in_schema=False)
def _docs_con_diagonal() -> RedirectResponse:
    # La landing usa rutas relativas (`images/...`): sin la diagonal final se
    # resolverían contra `/`. Redirección relativa, para no armar una URL
    # `http://` detrás del túnel, que llega en HTTP plano.
    return RedirectResponse("/docs/", status_code=308)


# Montajes al final: `/` atrapa todo lo que no sea una ruta de arriba. El
# build del frontend solo existe después de `npm run build` (en desarrollo
# lo sirve Vite), así que se monta solo si está.
app.mount("/docs", StaticFiles(directory=PROJECT_ROOT / "docs", html=True), name="docs")
FRONTEND = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
