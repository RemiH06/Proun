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

  function toggleImage(path: string, name: string) {
    setState((s) => {
      if (s.images.some((img) => img.path === path)) {
        return { ...s, images: s.images.filter((img) => img.path !== path) }
      }
      return { ...s, images: [...s.images, newImageConfig(path, name)] }
    })
  }

  function updateImage(path: string, patch: Partial<ImageConfig>) {
    setState((s) => ({
      ...s,
      images: s.images.map((img) => (img.path === path ? { ...img, ...patch } : img)),
    }))
  }

  function removeImage(path: string) {
    setState((s) => ({ ...s, images: s.images.filter((img) => img.path !== path) }))
  }

  return { state, update, reroll, toggleImage, updateImage, removeImage }
}
