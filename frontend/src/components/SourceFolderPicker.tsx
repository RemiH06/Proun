import { useState } from 'react'
import { listSources, thumbnailUrl, type SourceImage } from '../api/client'

type Props = {
  value: string
  onChange: (path: string) => void
  selectedPaths: Set<string>
  onToggle: (path: string, name: string) => void
}

export function SourceFolderPicker({ value, onChange, selectedPaths, onToggle }: Props) {
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
      <h2>Fuentes</h2>
      <div className="row">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && buscar()}
          placeholder="ruta a una carpeta de imágenes, ej. fuentes"
        />
        <button onClick={buscar} disabled={loading}>
          {loading ? 'buscando...' : 'buscar'}
        </button>
      </div>
      <p className="muted">
        Escribe una ruta (relativa a la carpeta del proyecto, o absoluta) y presiona "buscar". No
        hay explorador de carpetas nativo del sistema operativo todavía, es una ruta de texto. Haz
        clic en una miniatura para agregarla o quitarla del collage.
      </p>
      {error && <p className="error">{error}</p>}
      {resolvedPath !== null && (
        <p className="muted">
          buscando en: <code>{resolvedPath}</code>
        </p>
      )}
      {resolvedPath !== null && images.length === 0 && !error && (
        <p className="error">no se encontró ninguna imagen ahí</p>
      )}
      {images.length > 0 && (
        <>
          <p className="muted">
            {images.length} imágenes encontradas, {selectedPaths.size} seleccionadas
          </p>
          <div className="thumbs">
            {images.map((img) => (
              <button
                key={img.path}
                type="button"
                className={`thumb ${selectedPaths.has(img.path) ? 'selected' : ''}`}
                onClick={() => onToggle(img.path, img.name)}
                title={img.name}
              >
                <img src={thumbnailUrl(img.path)} alt={img.name} />
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
