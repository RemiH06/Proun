// Pruebas del Worker de /docs con fetch simulado (sin red): node --test worker/
import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'

import worker, { ORIGEN } from './docs.js'

const fetchReal = globalThis.fetch
let pedidas = []

function simularPages(respuesta) {
  globalThis.fetch = async (url, opciones) => {
    pedidas.push({ url, opciones })
    return respuesta
  }
}

afterEach(() => {
  globalThis.fetch = fetchReal
  pedidas = []
})

const pedir = (ruta, metodo = 'GET') =>
  worker.fetch(new Request('https://proun.remlam.dev' + ruta, { method: metodo }))

test('/docs redirige a /docs/ sin ir a Pages', async () => {
  simularPages(new Response('no'))
  const r = await pedir('/docs?x=1')
  assert.equal(r.status, 308)
  assert.equal(r.headers.get('Location'), 'https://proun.remlam.dev/docs/?x=1')
  assert.equal(pedidas.length, 0)
})

test('/docs/ pide la raíz de Pages y conserva el cuerpo', async () => {
  simularPages(new Response('<h1>Proun</h1>', { headers: { 'Content-Type': 'text/html' } }))
  const r = await pedir('/docs/')
  assert.equal(pedidas[0].url, ORIGEN + '/')
  assert.equal(pedidas[0].opciones.redirect, 'manual')
  assert.equal(r.status, 200)
  assert.equal(await r.text(), '<h1>Proun</h1>')
  assert.equal(r.headers.get('Content-Type'), 'text/html')
})

test('subrutas y query llegan tal cual', async () => {
  simularPages(new Response('svg'))
  await pedir('/docs/images/logo.svg?v=2')
  assert.equal(pedidas[0].url, ORIGEN + '/images/logo.svg?v=2')
})

test('las redirecciones de Pages se reescriben a /docs', async () => {
  simularPages(new Response(null, { status: 301, headers: { Location: ORIGEN + '/ariadne/' } }))
  const r = await pedir('/docs/ariadne')
  assert.equal(r.status, 301)
  assert.equal(r.headers.get('Location'), '/docs/ariadne/')
})

test('una redirección a otro sitio no se toca', async () => {
  simularPages(new Response(null, { status: 302, headers: { Location: 'https://github.com/' } }))
  const r = await pedir('/docs/algo')
  assert.equal(r.headers.get('Location'), 'https://github.com/')
})

test('dos puntos no salen de /Proun/', async () => {
  simularPages(new Response('x'))
  await pedir('/docs/../../otro-repo/')
  // URL resuelve /docs/../../otro-repo/ a /otro-repo/, que no es /docs/.
  assert.equal(pedidas.length, 0)
  await pedir('/docs/a/../../docs/b')
  assert.equal(pedidas[0].url, ORIGEN + '/b')
})

test('lo que no es /docs/ da 404', async () => {
  simularPages(new Response('x'))
  assert.equal((await pedir('/docsx')).status, 404)
  assert.equal(pedidas.length, 0)
})

test('solo GET y HEAD', async () => {
  simularPages(new Response('x'))
  const r = await pedir('/docs/', 'POST')
  assert.equal(r.status, 405)
  assert.equal(r.headers.get('Allow'), 'GET, HEAD')
  assert.equal(pedidas.length, 0)
})

test('cabeceras de seguridad en toda respuesta de Pages', async () => {
  simularPages(new Response('x', { status: 404 }))
  const r = await pedir('/docs/no-existe')
  assert.equal(r.status, 404)
  assert.equal(r.headers.get('X-Content-Type-Options'), 'nosniff')
  assert.equal(r.headers.get('Content-Security-Policy'), "frame-ancestors 'self'")
  assert.equal(r.headers.get('X-Frame-Options'), 'SAMEORIGIN')
})
