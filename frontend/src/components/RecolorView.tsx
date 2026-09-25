import { useEffect, useRef, useState } from 'react'
import {
  fetchOptions,
  recolorExport,
  recolorExportAll,
  recolorPreview,
  RESOLUTIONS,
  type Options,
  type RecolorMode,
} from '../api/client'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { PreviewPane } from './PreviewPane'
import { WallpaperPicker } from './WallpaperPicker'

const ANGLES = [0, 90, 180, 270] as const

const GRUPOS: Array<{ label: string; group: 'escritorio' | 'celular' }> = [
  { label: 'escritorio', group: 'escritorio' },
  { label: 'celular', group: 'celular' },
]

// Pestaña separada del editor de capas: no compone nada nuevo, toma un
// wallpaper YA exportado (elegido con WallpaperPicker), opcionalmente lo
// rota/voltea/encaja en otra resolución, y lo repinta con un colormap
// (api/routes_recolor.py, misma función que recolorear.py).
export function RecolorView() {
  const [folderPath, setFolderPath] = useState('wallpapers')
  const [options, setOptions] = useState<Options | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [name, setName] = useState('inferno')
  const [mode, setMode] = useState<RecolorMode>('colormap')
  const [angle, setAngle] = useState<0 | 90 | 180 | 270>(0)
  const [flipH, setFlipH] = useState(false)
  const [flipV, setFlipV] = useState(false)
  const [resolution, setResolution] = useState('')
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [busyAll, setBusyAll] = useState(false)
  const lastUrl = useRef<string | null>(null)

  useEffect(() => {
    fetchOptions()
      .then(setOptions)
      .catch(() => {
        // Sin backend todavía no hay mucho que mostrar; el selector de
        // escalas queda con la que ya está elegida como única opción.
      })
  }, [])

  const debounced = useDebouncedValue({ selected, mode, name, angle, flipH, flipV, resolution }, 300)

  useEffect(() => {
    if (!debounced.selected) {
      setImageUrl(null)
      return
    }
    let vigente = true
    setLoading(true)
    setError(null)
    recolorPreview({
      path: debounced.selected,
      mode: debounced.mode,
      name: debounced.name,
      angle: debounced.angle,
      flipH: debounced.flipH,
      flipV: debounced.flipV,
      resolution: debounced.resolution || null,
    })
      .then((blob) => {
        if (!vigente) return
        const url = URL.createObjectURL(blob)
        if (lastUrl.current) URL.revokeObjectURL(lastUrl.current)
        lastUrl.current = url
        setImageUrl(url)
      })
      .catch((e) => {
        if (vigente) {
          setError(e instanceof Error ? e.message : 'no se pudo generar la vista previa')
        }
      })
      .finally(() => {
        if (vigente) setLoading(false)
      })
    return () => {
      vigente = false
    }
  }, [debounced])

  async function exportar() {
    if (!selected) return
    setBusy(true)
    setStatus(null)
    try {
      const { path } = await recolorExport({
        path: selected, mode, name, angle, flipH, flipV, resolution: resolution || null,
      })
      setStatus(path ? `guardado en ${path}` : 'exportado')
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'no se pudo exportar')
    } finally {
      setBusy(false)
    }
  }

  async function exportarTodas() {
    if (!selected) return
    setBusyAll(true)
    setStatus(null)
    try {
      const { folder, paths } = await recolorExportAll({
        path: selected, angle, flipH, flipV, resolution: resolution || null,
      })
      setStatus(`guardadas ${paths.length} variantes en ${folder}`)
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'no se pudo generar las variantes')
    } finally {
      setBusyAll(false)
    }
  }

  const colormaps = options?.colormaps ?? [name]

  return (
    <main className="layout-2col">
      <div className="column">
        <WallpaperPicker
          value={folderPath}
          onChange={setFolderPath}
          selected={selected}
          onSelect={setSelected}
        />

        <section className="panel">
          <h2>Escala de color</h2>
          <div className="button-row wrap">
            {colormaps.map((m) => (
              <button
                key={m}
                type="button"
                className={mode === 'colormap' && name === m ? 'active' : ''}
                onClick={() => {
                  setMode('colormap')
                  setName(m)
                }}
              >
                {m}
              </button>
            ))}
            <button
              type="button"
              className={mode === 'invert' ? 'active' : ''}
              onClick={() => setMode('invert')}
            >
              negativo
            </button>
          </div>
        </section>

        <section className="panel">
          <h2>Geometría</h2>
          <div className="control-group">
            <span className="control-label">Rotar</span>
            <div className="button-row">
              {ANGLES.map((a) => (
                <button
                  key={a}
                  type="button"
                  className={angle === a ? 'active' : ''}
                  onClick={() => setAngle(a)}
                >
                  {a}°
                </button>
              ))}
            </div>
          </div>
          <div className="control-group">
            <span className="control-label">Voltear</span>
            <div className="button-row">
              <button
                type="button"
                className={flipH ? 'active' : ''}
                onClick={() => setFlipH(!flipH)}
                title="voltear horizontal"
              >
                ↔
              </button>
              <button
                type="button"
                className={flipV ? 'active' : ''}
                onClick={() => setFlipV(!flipV)}
                title="voltear vertical"
              >
                ↕
              </button>
            </div>
          </div>
          <div className="control-group">
            <span className="control-label">Redimensionar</span>
            <select value={resolution} onChange={(e) => setResolution(e.target.value)}>
              <option value="">tamaño original</option>
              {GRUPOS.map(({ label, group }) => (
                <optgroup key={group} label={label}>
                  {RESOLUTIONS.filter((r) => r.group === group).map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
        </section>

        <section className="panel">
          <h2>Exportar</h2>
          <button className="primary" onClick={exportar} disabled={!selected || busy}>
            {busy ? 'exportando...' : 'exportar'}
          </button>
          <button onClick={exportarTodas} disabled={!selected || busyAll}>
            {busyAll ? 'generando...' : 'descargar todas las variantes'}
          </button>
          {status && <p className="muted">{status}</p>}
        </section>
      </div>

      <div className="column">
        <PreviewPane
          imageUrl={imageUrl}
          loading={loading}
          error={error}
          emptyMessage="elige un wallpaper ya exportado para empezar"
        />
      </div>
    </main>
  )
}
