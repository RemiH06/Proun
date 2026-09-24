import { useEffect, useRef, useState } from 'react'
import { fetchOptions, recolorExport, recolorPreview, type Options } from '../api/client'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { PreviewPane } from './PreviewPane'
import { WallpaperPicker } from './WallpaperPicker'

// Pestaña separada del editor de capas: no compone nada nuevo, toma un
// wallpaper YA exportado (elegido con WallpaperPicker) y lo repinta con un
// colormap (api/routes_recolor.py, misma función que recolorear.py).
export function RecolorView() {
  const [folderPath, setFolderPath] = useState('wallpapers')
  const [options, setOptions] = useState<Options | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [name, setName] = useState('inferno')
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const lastUrl = useRef<string | null>(null)

  useEffect(() => {
    fetchOptions()
      .then(setOptions)
      .catch(() => {
        // Sin backend todavía no hay mucho que mostrar; el selector de
        // escalas queda con la que ya está elegida como única opción.
      })
  }, [])

  const debounced = useDebouncedValue({ selected, name }, 300)

  useEffect(() => {
    if (!debounced.selected) {
      setImageUrl(null)
      return
    }
    let vigente = true
    setLoading(true)
    setError(null)
    recolorPreview({ path: debounced.selected, name: debounced.name })
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
      const { path } = await recolorExport({ path: selected, name })
      setStatus(path ? `guardado en ${path}` : 'exportado')
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'no se pudo exportar')
    } finally {
      setBusy(false)
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
                className={name === m ? 'active' : ''}
                onClick={() => setName(m)}
              >
                {m}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Exportar</h2>
          <button className="primary" onClick={exportar} disabled={!selected || busy}>
            {busy ? 'exportando...' : 'exportar'}
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
