"""App FastAPI de Proun: envuelve proun.spec/proun.compose para una GUI local.

Local, un solo usuario: sin auth, sin CORS (el frontend de Vite llega acá por
proxy, no por origen cruzado). Corre con `uvicorn api.main:app --reload`.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from proun import layout
from proun.errors import SpecError
from proun.ops import blend, iso, recolor, shapes

from . import routes_recolor, routes_render, routes_sources

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
