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
export type ImageLayer = CommonLayer & { kind: 'image'; path: string; name: string }
export type ShapeLayer = CommonLayer & {
  kind: 'shape'
  shapeKind: ShapeKind
  sides: number
  outlineWidth: number
  outlineInset: number
}
export type TextLayer = CommonLayer & {
  kind: 'text'
  text: string
  weight: 'regular' | 'bold'
  align: 'left' | 'center' | 'right'
}

export type LayerConfig = ImageLayer | ShapeLayer | TextLayer

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

export function newImageLayer(path: string, name: string): ImageLayer {
  return { ...commonDefaults(), kind: 'image', path, name }
}

export function newShapeLayer(shapeKind: ShapeKind = 'circle'): ShapeLayer {
  return { ...commonDefaults(), kind: 'shape', shapeKind, sides: 6, outlineWidth: 0, outlineInset: 0.12 }
}

export function newTextLayer(): TextLayer {
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
  { label: '1080x2400 (Nothing Phone 1)', value: '1080x2400', group: 'celular' },
  { label: '1080x2412 (Nothing Phone 2 / 2a)', value: '1080x2412', group: 'celular' },
  { label: '1080x2392 (Nothing Phone 3a / 3a Pro)', value: '1080x2392', group: 'celular' },
  { label: '1260x2800 (Nothing Phone 3)', value: '1260x2800', group: 'celular' },
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

// El nombre da su carpeta y sus archivos dentro de wallpapers/<resolución>/
// (imagen, spec, recoloreados): ver api/routes_render.py::_wallpaper_paths.
// Vacío u omitido, el backend arma uno con el color y la semilla.
export type ExportParams = PreviewParams & { name?: string }

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
    body: JSON.stringify({ ...toBody(params), name: params.name }),
  })
  if (!res.ok) throw new Error(await readError(res))
  const blob = await res.blob()
  return { blob, path: res.headers.get('X-Export-Path') }
}

// Repinta un wallpaper YA exportado (por ruta) con un colormap o como
// negativo, sin pasar por layers/compose: ver api/routes_recolor.py y
// recolorear.py. angle/flipH/flipV/resolution son opcionales: rotan/
// voltean y encajan en otra resolución antes de recolorear.
export type RecolorMode = 'colormap' | 'invert'

export type RecolorParams = {
  path: string
  mode?: RecolorMode
  name: string
  stops?: string[]
  angle?: 0 | 90 | 180 | 270
  flipH?: boolean
  flipV?: boolean
  resolution?: string | null
}

function recolorBody(p: RecolorParams) {
  const geometria: Record<string, unknown> = {
    path: p.path,
    angle: p.angle ?? 0,
    flip_h: p.flipH ?? false,
    flip_v: p.flipV ?? false,
  }
  if (p.resolution) geometria.resolution = p.resolution
  if (p.mode === 'invert') return { ...geometria, mode: 'invert' }
  return p.stops ? { ...geometria, stops: p.stops } : { ...geometria, name: p.name }
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

// Genera los colormaps con nombre más el negativo de una sola vez y los
// guarda junto al original, en su misma carpeta (sin comprimir en zip: ver
// api/routes_recolor.py::export_all).
export type RecolorAllParams = {
  path: string
  angle?: 0 | 90 | 180 | 270
  flipH?: boolean
  flipV?: boolean
  resolution?: string | null
}

export async function recolorExportAll(
  params: RecolorAllParams,
): Promise<{ folder: string; paths: string[] }> {
  const res = await fetch('/api/recolor/export-all', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      path: params.path,
      angle: params.angle ?? 0,
      flip_h: params.flipH ?? false,
      flip_v: params.flipV ?? false,
      ...(params.resolution ? { resolution: params.resolution } : {}),
    }),
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

// La spec actual, tal cual la entendería la CLI con --spec: para guardarla
// a un archivo, o para reconstruir el wallpaper fuera del editor.
export async function fetchSpec(params: PreviewParams): Promise<Record<string, unknown>> {
  const res = await fetch('/api/spec', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toBody(params)),
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

// --- Camino de vuelta: un JSON de spec (recién exportado, o escrito a mano
// como los de json/) hacia el estado del editor. Es el espejo de toBody()/
// toLayerDict(), pero nunca puede ser perfecto: la spec completa del motor
// admite cosas que el editor no tiene control para mostrar (pool, cover,
// region, bleed, resize.scale, varias resoluciones/colores/semillas a la
// vez...). Donde eso pasa, se hace lo mejor posible y se junta un aviso en
// vez de fallar en silencio.

type Unknown = Record<string, unknown>

function esObjeto(v: unknown): v is Unknown {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function parseAngleFlip(rotate: unknown): { angle: 0 | 90 | 180 | 270; flipH: boolean; flipV: boolean } {
  let angle: 0 | 90 | 180 | 270 = 0
  let flipH = false
  let flipV = false
  if (esObjeto(rotate)) {
    const angulos = rotate.angles
    if (Array.isArray(angulos) && angulos.length > 0) {
      const primero = Number(angulos[0])
      if (primero === 90 || primero === 180 || primero === 270) angle = primero
    }
    const flip = rotate.flip
    if (flip === 'horizontal' || flip === 'both') flipH = true
    if (flip === 'vertical' || flip === 'both') flipV = true
  }
  return { angle, flipH, flipV }
}

function parseRepeatDict(raw: unknown): RepeatConfig {
  if (!esObjeto(raw)) return null
  if (Array.isArray(raw.step) && raw.step.length === 2) {
    const sx = Number(raw.step[0])
    const sy = Number(raw.step[1])
    const spacing = Math.max(Math.abs(sx), Math.abs(sy)) || 1
    return {
      kind: 'linear',
      dirX: Math.sign(sx) as -1 | 0 | 1,
      dirY: Math.sign(sy) as -1 | 0 | 1,
      spacing,
      times: typeof raw.times === 'number' ? raw.times : 1,
      mirror: Boolean(raw.mirror),
    }
  }
  if (Array.isArray(raw.pivot) && raw.pivot.length === 2) {
    const px = Number(raw.pivot[0])
    const py = Number(raw.pivot[1])
    const spacing = Math.max(Math.abs(px), Math.abs(py)) || 0.5
    return {
      kind: 'kaleidoscope',
      pivotDirX: Math.sign(px),
      pivotDirY: Math.sign(py),
      spacing,
      sectors: typeof raw.sectors === 'number' ? raw.sectors : 6,
    }
  }
  return null
}

function parseMosaicDict(raw: unknown): MosaicConfig {
  if (!esObjeto(raw) || !Array.isArray(raw.grid) || raw.grid.length !== 2) return null
  return { cols: Number(raw.grid[0]), rows: Number(raw.grid[1]), mirror: Boolean(raw.mirror) }
}

function parseFinishDict(raw: unknown): FinishConfig {
  const f = defaultFinish()
  if (!esObjeto(raw)) return f
  if (typeof raw.vignette === 'number') f.vignette = raw.vignette
  if (typeof raw.grain === 'number') f.grain = raw.grain
  if (typeof raw.blur === 'number') f.blur = raw.blur
  if (typeof raw.contrast === 'number') f.contrast = raw.contrast
  if (typeof raw.brightness === 'number') f.brightness = raw.brightness
  if (typeof raw.saturation === 'number') f.saturation = raw.saturation
  if (esObjeto(raw.overlay)) {
    f.overlay = {
      on: true,
      color: typeof raw.overlay.color === 'string' && raw.overlay.color !== 'auto'
        ? raw.overlay.color
        : f.overlay.color,
      opacity: typeof raw.overlay.opacity === 'number' ? raw.overlay.opacity : f.overlay.opacity,
      mode: typeof raw.overlay.mode === 'string' ? raw.overlay.mode : f.overlay.mode,
    }
  }
  if (esObjeto(raw.stain) && typeof raw.stain.amount === 'number') f.stainAmount = raw.stain.amount
  return f
}

function parseBackgroundDict(raw: unknown): BackgroundConfig {
  const bg = defaultBackground()
  if (raw === undefined || raw === null || raw === 'auto') return bg
  if (typeof raw === 'string') {
    bg.mode = 'solid'
    bg.solidColor = raw
    return bg
  }
  if (!esObjeto(raw)) return bg
  if (typeof raw.solid === 'string') {
    if (raw.solid === 'auto') {
      bg.mode = 'auto'
    } else {
      bg.mode = 'solid'
      bg.solidColor = raw.solid
    }
  } else if (Array.isArray(raw.gradient) && raw.gradient.length === 2) {
    bg.mode = 'gradient'
    bg.gradientFrom = String(raw.gradient[0])
    bg.gradientTo = String(raw.gradient[1])
    if (typeof raw.direction === 'string') bg.direction = raw.direction as BackgroundDirection
  }
  if (esObjeto(raw.stain) && typeof raw.stain.amount === 'number') bg.stainAmount = raw.stain.amount
  return bg
}

const SHAPE_KINDS: ShapeKind[] = ['rect', 'circle', 'triangle', 'diamond', 'polygon']

function parseLayerDict(raw: Unknown, warnings: string[], indice: number): LayerConfig | null {
  let base: LayerConfig

  if (typeof raw.src === 'string') {
    const path = raw.src
    const nombre = path.split(/[\\/]/).pop() || path
    base = newImageLayer(path, nombre)
  } else if (raw.shape !== undefined) {
    let shapeKind: ShapeKind = 'circle'
    let sides = 6
    if (typeof raw.shape === 'string' && (SHAPE_KINDS as string[]).includes(raw.shape)) {
      shapeKind = raw.shape as ShapeKind
    } else if (esObjeto(raw.shape) && raw.shape.kind === 'polygon') {
      shapeKind = 'polygon'
      if (typeof raw.shape.sides === 'number') sides = raw.shape.sides
    }
    let outlineWidth: number | undefined
    let outlineInset: number | undefined
    if (esObjeto(raw.outline)) {
      if (typeof raw.outline.width === 'number') outlineWidth = raw.outline.width
      if (typeof raw.outline.inset === 'number') outlineInset = raw.outline.inset
    }
    const plantillaFigura = newShapeLayer(shapeKind)
    base = {
      ...plantillaFigura,
      sides,
      outlineWidth: outlineWidth ?? plantillaFigura.outlineWidth,
      outlineInset: outlineInset ?? plantillaFigura.outlineInset,
    }
  } else if (raw.text !== undefined) {
    const plantillaTexto = newTextLayer()
    if (typeof raw.text === 'string') {
      base = { ...plantillaTexto, text: raw.text }
    } else if (esObjeto(raw.text)) {
      base = {
        ...plantillaTexto,
        text: typeof raw.text.text === 'string' ? raw.text.text : '',
        weight: raw.text.weight === 'regular' ? 'regular' : 'bold',
        align: raw.text.align === 'center' || raw.text.align === 'right' ? raw.text.align : 'left',
      }
    } else {
      base = plantillaTexto
    }
  } else {
    warnings.push(`capa ${indice + 1}: es "pool" (o no tiene src/shape/text), el editor no la representa, se omitió`)
    return null
  }

  const { angle, flipH, flipV } = parseAngleFlip(raw.rotate)
  base.angle = angle
  base.flipH = flipH
  base.flipV = flipV
  if (typeof raw.opacity === 'number') base.opacity = raw.opacity
  if (typeof raw.blend === 'string') base.blend = raw.blend
  if (typeof raw.color === 'string') base.color = raw.color
  base.repeat = parseRepeatDict(raw.repeat)
  base.mosaic = parseMosaicDict(raw.mosaic)
  if (Array.isArray(raw.position) && raw.position.length === 2) {
    base.position = { x: Number(raw.position[0]), y: Number(raw.position[1]) }
  }
  if (typeof raw.z === 'number') base.z = raw.z
  base.finish = parseFinishDict(raw.finish)

  if (esObjeto(raw.crop) && typeof raw.crop.aspect === 'string') {
    base.cropAspect = raw.crop.aspect
  } else if (raw.crop) {
    warnings.push(`capa ${indice + 1}: crop con una forma que el editor no soporta (solo "aspect"), se ignoró`)
  }

  if (typeof raw.stain === 'number') {
    base.stainAmount = raw.stain
  } else if (esObjeto(raw.stain)) {
    if (typeof raw.stain.amount === 'number') base.stainAmount = raw.stain.amount
    const extra = Object.keys(raw.stain).filter((k) => k !== 'amount')
    if (extra.length > 0) {
      warnings.push(`capa ${indice + 1}: stain con ajustes que el editor no expone (${extra.join(', ')}), se usó solo "amount"`)
    }
  }

  if (esObjeto(raw.resize)) {
    if (Array.isArray(raw.resize.size) && raw.resize.size.length === 2
        && Number(raw.resize.size[0]) === Number(raw.resize.size[1])) {
      base.resizeScale = Number(raw.resize.size[0])
      base.resizeMode = raw.resize.mode === 'fill' ? 'fill' : 'fit'
    } else {
      warnings.push(`capa ${indice + 1}: resize con una forma que el editor no soporta (scale, max_side, o tamaño no cuadrado), se ignoró`)
    }
  }

  return base
}

export function parseSpecJson(data: Unknown): { spec: PreviewParams; warnings: string[] } {
  const warnings: string[] = []

  const resoluciones = Array.isArray(data.resolutions) ? data.resolutions : []
  if (resoluciones.length > 1) {
    warnings.push(`la spec tiene ${resoluciones.length} resoluciones, el editor trabaja con una sola a la vez: se usó la primera`)
  }
  const primeraResolucion = resoluciones[0]
  const resolution = typeof primeraResolucion === 'string'
    ? primeraResolucion
    : Array.isArray(primeraResolucion) && primeraResolucion.length === 2
      ? `${primeraResolucion[0]}x${primeraResolucion[1]}`
      : DEFAULT_RESOLUTION

  const coloresSpec = Array.isArray(data.colors) ? data.colors : []
  if (coloresSpec.length > 1) {
    warnings.push(`la spec tiene ${coloresSpec.length} colores, el editor trabaja con uno a la vez: se usó el primero`)
  }
  const color = typeof coloresSpec[0] === 'string' ? coloresSpec[0] : '#3ba7ff'

  const semillas = Array.isArray(data.seeds) ? data.seeds : []
  if (semillas.length > 1) {
    warnings.push(`la spec tiene ${semillas.length} semillas, el editor trabaja con una a la vez: se usó la primera`)
  }
  const seed = typeof semillas[0] === 'number' ? semillas[0] : randomSeed()

  const layoutMode = esObjeto(data.layout) && typeof data.layout.mode === 'string'
    ? data.layout.mode
    : 'scatter'

  const recolorDefaults = esObjeto(data.defaults) ? data.defaults.recolor : undefined
  const recolorMode = esObjeto(recolorDefaults) && typeof recolorDefaults.mode === 'string'
    ? recolorDefaults.mode
    : 'duotone'

  const fuentes = Array.isArray(data.sources) ? data.sources : []
  const layers: LayerConfig[] = []
  fuentes.forEach((cruda, indice) => {
    if (!esObjeto(cruda)) return
    const layer = parseLayerDict(cruda, warnings, indice)
    if (layer) layers.push(layer)
  })

  return {
    spec: {
      layers,
      layoutMode,
      color,
      recolorMode,
      seed,
      background: parseBackgroundDict(data.background),
      finish: parseFinishDict(data.finish),
      resolution,
    },
    warnings,
  }
}
