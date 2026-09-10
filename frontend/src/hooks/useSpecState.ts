import { useState } from 'react'
import {
  defaultBackground,
  defaultFinish,
  newImageLayer,
  newShapeLayer,
  newTextLayer,
  randomSeed,
  type BackgroundConfig,
  type FinishConfig,
  type LayerConfig,
  type ShapeKind,
} from '../api/client'

export type SpecState = {
  layers: LayerConfig[]
  layoutMode: string
  color: string
  recolorMode: string
  seed: number
  background: BackgroundConfig
  finish: FinishConfig
}

export function useSpecState() {
  const [state, setState] = useState<SpecState>({
    layers: [],
    layoutMode: 'scatter',
    color: '#3ba7ff',
    recolorMode: 'duotone',
    seed: randomSeed(),
    background: defaultBackground(),
    finish: defaultFinish(),
  })

  function update<K extends keyof SpecState>(key: K, value: SpecState[K]) {
    setState((s) => ({ ...s, [key]: value }))
  }

  function reroll() {
    update('seed', randomSeed())
  }

  // Del clic en una miniatura: si esa imagen no está en el lienzo, agrega
  // una capa nueva; si ya está (una o más veces, ver duplicateLayer), las
  // saca todas. Para agregar la misma imagen otra vez sin sacar la
  // primera, se usa el botón "duplicar" del propio submenú, no el clic en
  // la miniatura.
  function toggleImage(path: string, name: string) {
    setState((s) => {
      const yaEsta = s.layers.some((capa) => capa.kind === 'image' && capa.path === path)
      if (yaEsta) {
        return { ...s, layers: s.layers.filter((capa) => !(capa.kind === 'image' && capa.path === path)) }
      }
      return { ...s, layers: [...s.layers, newImageLayer(path, name)] }
    })
  }

  function addShape(kind: ShapeKind) {
    setState((s) => ({ ...s, layers: [...s.layers, newShapeLayer(kind)] }))
  }

  function addText() {
    setState((s) => ({ ...s, layers: [...s.layers, newTextLayer()] }))
  }

  // A partir de acá se identifica la capa por `id`, no por `path`: puede
  // haber dos capas de la misma imagen (u otras del mismo tipo) con
  // ajustes independientes.
  function updateLayer(id: string, patch: Partial<LayerConfig>) {
    setState((s) => ({
      ...s,
      layers: s.layers.map((capa) => (capa.id === id ? ({ ...capa, ...patch } as LayerConfig) : capa)),
    }))
  }

  function removeLayer(id: string) {
    setState((s) => ({ ...s, layers: s.layers.filter((capa) => capa.id !== id) }))
  }

  // Copia la capa (con sus ajustes actuales) con un id nuevo, justo
  // después del original, para que la misma imagen/figura/texto entre dos
  // veces al collage como dos capas que se pueden tocar por separado.
  function duplicateLayer(id: string) {
    setState((s) => {
      const indice = s.layers.findIndex((capa) => capa.id === id)
      if (indice === -1) return s
      const copia = { ...s.layers[indice], id: crypto.randomUUID() }
      const layers = [...s.layers]
      layers.splice(indice + 1, 0, copia)
      return { ...s, layers }
    })
  }

  function updateBackground(patch: Partial<BackgroundConfig>) {
    setState((s) => ({ ...s, background: { ...s.background, ...patch } }))
  }

  function updateFinish(patch: Partial<FinishConfig>) {
    setState((s) => ({ ...s, finish: { ...s.finish, ...patch } }))
  }

  return {
    state,
    update,
    reroll,
    toggleImage,
    addShape,
    addText,
    updateLayer,
    removeLayer,
    duplicateLayer,
    updateBackground,
    updateFinish,
  }
}
