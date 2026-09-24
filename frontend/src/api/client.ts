// Cliente delgado sobre /api. No revalida nada: si el backend rechaza algo,
// devuelve el mensaje de error en español tal cual llegó (viene de
// proun.errors.SpecError, ver api/main.py).

export type SourceImage = { path: string; name: string }
export type SourceList = { path: string; count: number; images: SourceImage[] }
export type Options = {
  layout_modes: string[]
  recolor_modes: string[]
  blend_modes: string[]
  shape_kinds: string[]
  colormaps: string[]
}

export type FlipMode = 'none' | 'horizontal' | 'vertical' | 'both'

export type RepeatConfig =
  | null
  // dirX/dirY: dirección (-1/0/1 por eje, del compás). spacing: qué tan
  // separada sale cada copia (1 = pegada sin solapar, menos se solapan,
  // más deja hueco); es lo que multiplica a la dirección para dar el
  // `step` real que espera el motor.
  | { kind: 'linear'; dirX: -1 | 0 | 1; dirY: -1 | 0 | 1; spacing: number; times: number; mirror: boolean }
  // pivotDirX/pivotDirY: de qué lado queda el pivote (mismo compás que el
  // lineal, sin el centro). spacing acá es qué tan lejos del centro de la
  // imagen queda ese pivote: más lejos, el abanico de copias se abre más.
  | { kind: 'kaleidoscope'; pivotDirX: number; pivotDirY: number; spacing: number; sectors: number }

export type MosaicConfig = null | { cols: number; rows: number; mirror: boolean }

// Fracción [0,1] del lienzo; null = el layout la ubica solo, como siempre.
export type PositionConfig = null | { x: number; y: number }

export type ShapeKind = 'rect' | 'circle' | 'triangle' | 'diamond' | 'polygon'

// Ajustes que comparten las tres clases de capa (imagen, figura, texto).
// Los valores "por defecto" no viajan al backend: toLayerDict() solo manda
// las claves que de verdad cambian algo.
type CommonLayer = {
  id: string
  angle: 0 | 90 | 180 | 270
  flipH: boolean
  flipV: boolean
  opacity: number
  blend: string
  color: string | null
  repeat: RepeatConfig
  mosaic: MosaicConfig
  position: PositionConfig
  // Orden de apilado: 0 = donde caiga por sorteo (igual que no declararlo).
  // Más alto pinta más arriba (adelante), más bajo pinta más abajo (atrás).
  z: number
  // null = sin recortar. Si no, algo como "1:1" o "16:9".
  cropAspect: string | null
  // null = tamaño automático del layout (como hasta ahora). Si no, fracción
  // del lienzo (0-1.5) que ocupa el lado mayor de la capa: mismo mecanismo
  // que ya usa el layout para su propio sorteo de tamaño, solo que fijado a
  // mano en vez de aleatorio.
  resizeScale: number | null
  // "fit" conserva la proporción y puede dejar franjas del hueco sin
  // cubrir; "fill" recorta el sobrante para llenarlo por completo, sin
  // dejar espacios. Solo importa mientras resizeScale no sea null.
  resizeMode: 'fit' | 'fill'
  // 0 = sin manchar.
  stainAmount: number
  // Mismo acabado que el global (viñeta, grano, desenfoque...), pero
  // aplicado solo a esta capa antes de pegarla al lienzo. `stainAmount` de
  // acá adentro no se manda (esta capa ya tiene su propio `stain` arriba).
  finish: FinishConfig
}

// `id` identifica esta capa en particular, no el archivo/figura/texto: la
// misma imagen puede entrar dos veces al collage como dos capas
// independientes, cada una con su propio `id`.
export type LayerConfig =
  | (CommonLayer & { kind: 'image'; path: string; name: string })
  | (CommonLayer & {
      kind: 'shape'
      shapeKind: ShapeKind
      sides: number
      outlineWidth: number
      outlineInset: number
    })
  | (CommonLayer & {
      kind: 'text'
      text: string
      weight: 'regular' | 'bold'
      align: 'left' | 'center' | 'right'
    })

function commonDefaults(): CommonLayer {
  return {
    id: crypto.randomUUID(),
    angle: 0,
    flipH: false,
    flipV: false,
    opacity: 1,
    blend: 'normal',
    color: null,
    repeat: null,
    mosaic: null,
    position: null,
    z: 0,
    cropAspect: null,
    resizeScale: null,
    resizeMode: 'fit',
    stainAmount: 0,
    finish: defaultFinish(),
  }
}

export function newImageLayer(path: string, name: string): LayerConfig {
  return { ...commonDefaults(), kind: 'image', path, name }
}

export function newShapeLayer(shapeKind: ShapeKind = 'circle'): LayerConfig {
  return { ...commonDefaults(), kind: 'shape', shapeKind, sides: 6, outlineWidth: 0, outlineInset: 0.12 }
}

export function newTextLayer(): LayerConfig {
  return { ...commonDefaults(), kind: 'text', text: '', weight: 'bold', align: 'left' }
}

function flipMode(cfg: CommonLayer): FlipMode {
  if (cfg.flipH && cfg.flipV) return 'both'
  if (cfg.flipH) return 'horizontal'
  if (cfg.flipV) return 'vertical'
  return 'none'
}

export function toLayerDict(cfg: LayerConfig): Record<string, unknown> {
  const layer: Record<string, unknown> = {}

  if (cfg.kind === 'image') {
    layer.src = cfg.path
  } else if (cfg.kind === 'shape') {
    layer.shape = cfg.shapeKind === 'polygon' ? { kind: 'polygon', sides: cfg.sides } : cfg.shapeKind
    if (cfg.outlineWidth > 0) {
      layer.outline = { width: cfg.outlineWidth, inset: cfg.outlineInset }
    }
  } else {
    layer.text = { text: cfg.text, weight: cfg.weight, align: cfg.align }
  }

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
        : {
            pivot: [cfg.repeat.pivotDirX * cfg.repeat.spacing, cfg.repeat.pivotDirY * cfg.repeat.spacing],
            sectors: cfg.repeat.sectors,
          }
  }
  if (cfg.mosaic) {
    layer.mosaic = { grid: [cfg.mosaic.cols, cfg.mosaic.rows], mirror: cfg.mosaic.mirror }
  }
  if (cfg.position) {
    layer.position = [cfg.position.x, cfg.position.y]
  }
  if (cfg.z !== 0) layer.z = cfg.z
  if (cfg.cropAspect) layer.crop = { aspect: cfg.cropAspect }
  if (cfg.resizeScale !== null) {
    // JSON no distingue 1 de 1.0: un valor entero exacto viajaría como
    // "size": [1, 1] y el motor lee ese 1 como 1 PIXEL, no 100% del
    // lienzo (proun/geometry.py::measure trata int = px, float =
    // fracción). "llenar marco" manda justo ese 1, así que hay que
    // empujarlo un poquito para que siempre viaje con parte decimal.
    const valor = Number.isInteger(cfg.resizeScale) ? cfg.resizeScale + 0.0001 : cfg.resizeScale
    layer.resize = { size: [valor, valor], mode: cfg.resizeMode }
  }
  if (cfg.stainAmount > 0) layer.stain = { amount: cfg.stainAmount }
  const finishDict = toFinishDict(cfg.finish)
  if (finishDict) layer.finish = finishDict

  return layer
}

export type BackgroundMode = 'auto' | 'solid' | 'gradient'
export type BackgroundDirection = 'vertical' | 'horizontal' | 'diagonal' | 'radial'

export type BackgroundConfig = {
  mode: BackgroundMode
  solidColor: string
  gradientFrom: string
  gradientTo: string
  direction: BackgroundDirection
  stainAmount: number
}

export function defaultBackground(): BackgroundConfig {
  return {
    mode: 'auto',
    solidColor: '#f2efe8',
    gradientFrom: '#f2efe8',
    gradientTo: '#101018',
    direction: 'vertical',
    stainAmount: 0,
  }
}

function toBackgroundDict(bg: BackgroundConfig): Record<string, unknown> | string | undefined {
  if (bg.mode === 'auto' && bg.stainAmount === 0) return undefined
  if (bg.mode === 'auto') return { solid: 'auto', stain: { amount: bg.stainAmount } }
  const base: Record<string, unknown> =
    bg.mode === 'solid'
      ? { solid: bg.solidColor }
      : { gradient: [bg.gradientFrom, bg.gradientTo], direction: bg.direction }
  if (bg.stainAmount > 0) base.stain = { amount: bg.stainAmount }
  return base
}

export type OverlayConfig = { on: boolean; color: string; opacity: number; mode: string }

export type FinishConfig = {
  vignette: number
  grain: number
  blur: number
  contrast: number
  brightness: number
  saturation: number
  overlay: OverlayConfig
  stainAmount: number
}

export function defaultFinish(): FinishConfig {
  return {
    vignette: 0,
    grain: 0,
    blur: 0,
    contrast: 1,
    brightness: 1,
    saturation: 1,
    overlay: { on: false, color: '#d94f3d', opacity: 0.15, mode: 'soft_light' },
    stainAmount: 0,
  }
}

function toFinishDict(f: FinishConfig): Record<string, unknown> | undefined {
  const out: Record<string, unknown> = {}
  if (f.vignette > 0) out.vignette = f.vignette
  if (f.grain > 0) out.grain = f.grain
  if (f.blur > 0) out.blur = f.blur
  if (f.contrast !== 1) out.contrast = f.contrast
  if (f.brightness !== 1) out.brightness = f.brightness
  if (f.saturation !== 1) out.saturation = f.saturation
  if (f.overlay.on) out.overlay = { color: f.overlay.color, opacity: f.overlay.opacity, mode: f.overlay.mode }
  if (f.stainAmount > 0) out.stain = { amount: f.stainAmount }
  return Object.keys(out).length > 0 ? out : undefined
}

// Dimensiones del canvas. La vista previa usa el mismo aspecto, solo que
// achicado (ver api/routes_render.py::_resolucion_de_vista_previa), así que
// elegir un tamaño de celular ya se ve vertical desde la vista previa.
export type ResolutionGroup = 'escritorio' | 'celular'

export const RESOLUTIONS: Array<{ label: string; value: string; group: ResolutionGroup }> = [
  { label: '1280x720 (HD)', value: '1280x720', group: 'escritorio' },
  { label: '1920x1080 (Full HD)', value: '1920x1080', group: 'escritorio' },
  { label: '2560x1440 (2K)', value: '2560x1440', group: 'escritorio' },
  { label: '3840x2160 (4K)', value: '3840x2160', group: 'escritorio' },
  { label: '1080x1920 (celular)', value: '1080x1920', group: 'celular' },
  { label: '1170x2532 (iPhone)', value: '1170x2532', group: 'celular' },
  { label: '1290x2796 (iPhone Pro Max)', value: '1290x2796', group: 'celular' },
]

export const DEFAULT_RESOLUTION = '1920x1080'

export type PreviewParams = {
  layers: LayerConfig[]
  layoutMode: string
  color: string
  recolorMode: string
  seed: number
  background: BackgroundConfig
  finish: FinishConfig
  resolution: string
}

export type ExportParams = PreviewParams

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
    layers: p.layers.map(toLayerDict),
    layout_mode: p.layoutMode,
    color: p.color,
    recolor_mode: p.recolorMode,
    seed: p.seed,
    background: toBackgroundDict(p.background),
    finish: toFinishDict(p.finish),
    resolution: p.resolution,
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
    body: JSON.stringify(toBody(params)),
  })
  if (!res.ok) throw new Error(await readError(res))
  const blob = await res.blob()
  return { blob, path: res.headers.get('X-Export-Path') }
}

// Repinta un wallpaper YA exportado (por ruta) con un colormap, sin pasar
// por layers/compose: ver api/routes_recolor.py y recolorear.py.
export type RecolorParams = {
  path: string
  name: string
  stops?: string[]
}

function recolorBody(p: RecolorParams) {
  return p.stops ? { path: p.path, stops: p.stops } : { path: p.path, name: p.name }
}

export async function recolorPreview(params: RecolorParams): Promise<Blob> {
  const res = await fetch('/api/recolor/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(recolorBody(params)),
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.blob()
}

export async function recolorExport(
  params: RecolorParams,
): Promise<{ blob: Blob; path: string | null }> {
  const res = await fetch('/api/recolor/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(recolorBody(params)),
  })
  if (!res.ok) throw new Error(await readError(res))
  const blob = await res.blob()
  return { blob, path: res.headers.get('X-Export-Path') }
}
