// Cliente delgado sobre /api. No revalida nada: si el backend rechaza algo,
// devuelve el mensaje de error en español tal cual llegó (viene de
// proun.errors.SpecError, ver api/main.py).

export type SourceImage = { path: string; name: string }
export type SourceList = { path: string; count: number; images: SourceImage[] }
export type Options = { layout_modes: string[]; recolor_modes: string[]; blend_modes: string[] }

export type FlipMode = 'none' | 'horizontal' | 'vertical' | 'both'

export type RepeatConfig =
  | null
  // dirX/dirY: dirección (-1/0/1 por eje, del compás). spacing: qué tan
  // separada sale cada copia (1 = pegada sin solapar, menos = se solapan,
  // más = deja hueco); es lo que multiplica a la dirección para dar el
  // `step` real que espera el motor.
  | { kind: 'linear'; dirX: -1 | 0 | 1; dirY: -1 | 0 | 1; spacing: number; times: number; mirror: boolean }
  | { kind: 'kaleidoscope'; pivotX: number; pivotY: number; sectors: number }

export type MosaicConfig = null | { cols: number; rows: number; mirror: boolean }

// Una imagen elegida a mano, con sus propios ajustes de capa. Los valores
// "por defecto" (0°, sin voltear, opacidad 1, blend normal, sin color
// propio, sin repeat, sin mosaico) no viajan al backend: toLayerDict() solo
// manda las claves que de verdad cambian algo.
export type ImageConfig = {
  path: string
  name: string
  angle: 0 | 90 | 180 | 270
  flipH: boolean
  flipV: boolean
  opacity: number
  blend: string
  color: string | null
  repeat: RepeatConfig
  mosaic: MosaicConfig
}

export function newImageConfig(path: string, name: string): ImageConfig {
  return {
    path,
    name,
    angle: 0,
    flipH: false,
    flipV: false,
    opacity: 1,
    blend: 'normal',
    color: null,
    repeat: null,
    mosaic: null,
  }
}

function flipMode(cfg: ImageConfig): FlipMode {
  if (cfg.flipH && cfg.flipV) return 'both'
  if (cfg.flipH) return 'horizontal'
  if (cfg.flipV) return 'vertical'
  return 'none'
}

export function toLayerDict(cfg: ImageConfig): Record<string, unknown> {
  const layer: Record<string, unknown> = { src: cfg.path }
  if (cfg.angle !== 0 || cfg.flipH || cfg.flipV) {
    layer.rotate = { angles: [cfg.angle], flip: flipMode(cfg) }
  }
  if (cfg.opacity !== 1) layer.opacity = cfg.opacity
  if (cfg.blend !== 'normal') layer.blend = cfg.blend
  if (cfg.color) layer.color = cfg.color
  if (cfg.repeat) {
    layer.repeat =
      cfg.repeat.kind === 'linear'
        ? {
            step: [cfg.repeat.dirX * cfg.repeat.spacing, cfg.repeat.dirY * cfg.repeat.spacing],
            times: cfg.repeat.times,
            mirror: cfg.repeat.mirror,
          }
        : { pivot: [cfg.repeat.pivotX, cfg.repeat.pivotY], sectors: cfg.repeat.sectors }
  }
  if (cfg.mosaic) {
    layer.mosaic = { grid: [cfg.mosaic.cols, cfg.mosaic.rows], mirror: cfg.mosaic.mirror }
  }
  return layer
}

export type PreviewParams = {
  images: ImageConfig[]
  layoutMode: string
  color: string
  recolorMode: string
  seed: number
}

export type ExportParams = PreviewParams & { resolution: string }

export const SEED_MIN = 100_000
export const SEED_MAX = 999_999_999

export function randomSeed(): number {
  return Math.floor(Math.random() * (SEED_MAX - SEED_MIN)) + SEED_MIN
}

async function readError(res: Response): Promise<string> {
  try {
    const datos = await res.json()
    return datos.detail ?? `error ${res.status}`
  } catch {
    return `error ${res.status}`
  }
}

function toBody(p: PreviewParams) {
  return {
    images: p.images.map(toLayerDict),
    layout_mode: p.layoutMode,
    color: p.color,
    recolor_mode: p.recolorMode,
    seed: p.seed,
  }
}

export async function fetchOptions(): Promise<Options> {
  const res = await fetch('/api/options')
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function listSources(path: string): Promise<SourceList> {
  const res = await fetch(`/api/sources?path=${encodeURIComponent(path)}`)
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export function thumbnailUrl(path: string, size = 160): string {
  return `/api/sources/thumbnail?path=${encodeURIComponent(path)}&size=${size}`
}

export async function preview(params: PreviewParams): Promise<Blob> {
  const res = await fetch('/api/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toBody(params)),
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.blob()
}

export async function exportImage(
  params: ExportParams,
): Promise<{ blob: Blob; path: string | null }> {
  const res = await fetch('/api/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...toBody(params), resolution: params.resolution }),
  })
  if (!res.ok) throw new Error(await readError(res))
  const blob = await res.blob()
  return { blob, path: res.headers.get('X-Export-Path') }
}
