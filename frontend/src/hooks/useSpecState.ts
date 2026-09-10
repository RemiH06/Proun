import { useState } from 'react'
import { newImageConfig, randomSeed, type ImageConfig } from '../api/client'

export type SpecState = {
  images: ImageConfig[]
  layoutMode: string
  color: string
  recolorMode: string
  seed: number
}

export function useSpecState() {
  const [state, setState] = useState<SpecState>({
    images: [],
    layoutMode: 'scatter',
    color: '#3ba7ff',
    recolorMode: 'duotone',
    seed: randomSeed(),
  })

  function update<K extends keyof SpecState>(key: K, value: SpecState[K]) {
    setState((s) => ({ ...s, [key]: value }))
  }

  function reroll() {
    update('seed', randomSeed())
  }

  // Del clic en una miniatura: si esa imagen no está en el lienzo, agrega
  // una capa nueva; si ya está (una o más veces, ver duplicateImage), las
  // saca todas. Para agregar la misma imagen otra vez sin sacar la
  // primera, se usa el botón "duplicar" del propio submenú, no el clic en
  // la miniatura.
  function toggleImage(path: string, name: string) {
    setState((s) => {
      if (s.images.some((img) => img.path === path)) {
        return { ...s, images: s.images.filter((img) => img.path !== path) }
      }
      return { ...s, images: [...s.images, newImageConfig(path, name)] }
    })
  }

  // A partir de acá se identifica la capa por `id`, no por `path`: puede
  // haber dos capas de la misma imagen con ajustes independientes.
  function updateImage(id: string, patch: Partial<ImageConfig>) {
    setState((s) => ({
      ...s,
      images: s.images.map((img) => (img.id === id ? { ...img, ...patch } : img)),
    }))
  }

  function removeImage(id: string) {
    setState((s) => ({ ...s, images: s.images.filter((img) => img.id !== id) }))
  }

  // Copia la capa (imagen + sus ajustes actuales) con un id nuevo, justo
  // después del original, para que la misma foto entre dos veces al
  // collage como dos capas que se pueden tocar por separado.
  function duplicateImage(id: string) {
    setState((s) => {
      const indice = s.images.findIndex((img) => img.id === id)
      if (indice === -1) return s
      const copia = { ...s.images[indice], id: crypto.randomUUID() }
      const images = [...s.images]
      images.splice(indice + 1, 0, copia)
      return { ...s, images }
    })
  }

  return { state, update, reroll, toggleImage, updateImage, removeImage, duplicateImage }
}
