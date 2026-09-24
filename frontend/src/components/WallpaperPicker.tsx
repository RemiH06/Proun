import { useState } from 'react'
import { listSources, thumbnailUrl, type SourceImage } from '../api/client'

type Props = {
  value: string
  onChange: (path: string) => void
  selected: string | null
  onSelect: (path: string) => void
}

// Como SourceFolderPicker, pero de selección única: acá no se arma una lista
// de capas para componer, se elige UN wallpaper ya exportado para volver a
// colorearlo.
export function WallpaperPicker({ value, onChange, selected, onSelect }: Props) {
  const [draft, setDraft] = useState(value)
  const [images, setImages] = useState<SourceImage[]>([])
  const [resolvedPath, setResolvedPath] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function buscar() {
    setLoading(true)
    setError(null)
    try {
      const resultado = await listSources(draft)
      onChange(draft)
      setImages(resultado.images)
      setResolvedPath(resultado.path)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'no se pudo leer la carpeta')
      setImages([])
      setResolvedPath(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel">
      <h2>Wallpaper</h2>
      <div className="row">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && buscar()}
          placeholder="ruta a una carpeta de wallpapers, ej. wallpapers"
        />
        <button onClick={buscar} disabled={loading}>
          {loading ? 'buscando...' : 'buscar'}
        </button>
      </div>
      <p className="muted">
        Escribe la ruta de la carpeta donde ya exportaste wallpapers y presiona "buscar". Haz clic
        en uno para elegirlo, es el que se va a volver a colorear.
      </p>
      {error && <p className="error">{error}</p>}
      {resolvedPath !== null && (
        <p className="muted">
          buscando en: <code>{resolvedPath}</code>
        </p>
      )}
      {resolvedPath !== null && images.length === 0 && !error && (
        <p className="error">no se encontró ningún wallpaper ahí</p>
      )}
      {images.length > 0 && (
        <div className="thumbs">
          {images.map((img) => (
            <button
              key={img.path}
              type="button"
              className={`thumb ${selected === img.path ? 'selected' : ''}`}
              onClick={() => onSelect(img.path)}
              title={img.name}
            >
              <img src={thumbnailUrl(img.path)} alt={img.name} />
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
