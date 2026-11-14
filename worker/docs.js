// Worker de Cloudflare en proun.remlam.dev/docs*: sirve la landing desde
// GitHub Pages bajo el dominio propio. Así hay una sola copia (Pages, que se
// actualiza sola con cada push a main) y la landing sigue arriba aunque
// Pixilate, donde corre el GUI, esté apagada. Access deja pasar /docs sin
// login (app en Bypass); el resto del hostname no pasa por aquí.

export const ORIGEN = 'https://remih06.github.io/Proun'

// Las mismas que pone api/main.py en el GUI.
const CABECERAS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'SAMEORIGIN',
  'Content-Security-Policy': "frame-ancestors 'self'",
  'Referrer-Policy': 'strict-origin-when-cross-origin',
}

export default {
  async fetch(request) {
    const url = new URL(request.url)
    // La landing usa rutas relativas (images/...): sin la diagonal final se
    // resolverían contra la raíz, que es el GUI.
    if (url.pathname === '/docs') {
      return Response.redirect(new URL('/docs/' + url.search, url), 308)
    }
    // La ruta del Worker (/docs*) también atrapa cosas como /docsx.
    if (!url.pathname.startsWith('/docs/')) {
      return new Response('no encontrado', { status: 404 })
    }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response(null, { status: 405, headers: { Allow: 'GET, HEAD' } })
    }

    // `URL` ya resolvió cualquier `..`: el destino no sale de /Proun/.
    const destino = ORIGEN + url.pathname.slice('/docs'.length) + url.search
    const respuesta = await fetch(destino, { method: request.method, redirect: 'manual' })
    const salida = new Response(respuesta.body, respuesta)

    // Pages redirige con URL absoluta (/Proun/ariadne -> .../Proun/ariadne/):
    // sin esto, el navegador terminaría en github.io.
    const location = salida.headers.get('Location')
    if (location?.startsWith(ORIGEN + '/')) {
      salida.headers.set('Location', '/docs' + location.slice(ORIGEN.length))
    }
    for (const [nombre, valor] of Object.entries(CABECERAS)) salida.headers.set(nombre, valor)
    return salida
  },
}
