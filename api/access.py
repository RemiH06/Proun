"""Valida en el origen el token que pone Cloudflare Access.

Access ya pide login delante de `proun.remlam.dev`, pero si el túnel o la app
de Access se configuran mal, cualquiera llegaría a la API sin pasar por ahí.
Por eso el origen revisa por su cuenta el JWT que Access agrega a cada
petición (`Cf-Access-Jwt-Assertion`): firma con las llaves públicas del
equipo, audiencia (el AUD de la app), emisor y vencimiento.

Se prende con `PROUN_ACCESS_EQUIPO` y `PROUN_ACCESS_AUD` (ver compose.yml).
Sin ninguna de las dos, apagado: es el modo local. Con una sola, la app no
arranca, para que una configuración a medias no deje todo abierto.
"""

from __future__ import annotations

import os

import jwt

ENCABEZADO = "cf-access-jwt-assertion"


class Verificador:
    def __init__(self, equipo: str, aud: str):
        self.emisor = f"https://{equipo}"
        self.aud = aud
        # PyJWKClient guarda el juego de llaves una hora y lo vuelve a pedir
        # si llega un `kid` desconocido (Access rota sus llaves).
        self.claves = jwt.PyJWKClient(f"{self.emisor}/cdn-cgi/access/certs", lifespan=3600, timeout=5)

    def __call__(self, token: str) -> dict:
        """Devuelve los claims o levanta `jwt.InvalidTokenError` /
        `jwt.PyJWKClientError` (esta última, también si no hay red)."""
        clave = self.claves.get_signing_key_from_jwt(token)
        # `algorithms` fijo: nunca se cree el `alg` que trae el propio token.
        return jwt.decode(
            token,
            clave.key,
            algorithms=["RS256"],
            audience=self.aud,
            issuer=self.emisor,
            options={"require": ["exp", "iat", "aud", "iss"]},
        )


def desde_entorno() -> Verificador | None:
    equipo = os.environ.get("PROUN_ACCESS_EQUIPO", "").strip()
    aud = os.environ.get("PROUN_ACCESS_AUD", "").strip()
    if not equipo and not aud:
        return None
    if not (equipo and aud):
        raise RuntimeError("PROUN_ACCESS_EQUIPO y PROUN_ACCESS_AUD van juntas: falta una")
    return Verificador(equipo, aud)


def es_publica(ruta: str) -> bool:
    """La landing queda abierta (Bypass en Access). Todo lo que empieza con
    `/docs/` lo sirve el montaje de `docs/`, así que un `/docs/../api` no
    llega a la API. Distingue mayúsculas: `/DOCS/` sí pide token."""
    return ruta == "/docs" or ruta.startswith("/docs/")
