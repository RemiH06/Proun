type Props = {
  imageUrl: string | null
  loading: boolean
  error: string | null
  emptyMessage?: string
}

export function PreviewPane({
  imageUrl,
  loading,
  error,
  emptyMessage = 'elige una carpeta con imágenes para empezar',
}: Props) {
  return (
    <section className="panel preview">
      <h2>Vista previa</h2>
      <div className="preview-frame">
        {imageUrl && <img src={imageUrl} alt="vista previa del collage" />}
        {loading && <p className="muted">generando...</p>}
        {error && <p className="error">{error}</p>}
        {!imageUrl && !loading && !error && <p className="muted">{emptyMessage}</p>}
      </div>
    </section>
  )
}
