import { useEffect, useRef, useState } from 'react'
import './App.css'
import { fetchOptions, preview, type Options } from './api/client'
import { ExportButton } from './components/ExportButton'
import { ImageConfigList } from './components/ImageConfigList'
import { ParamControls } from './components/ParamControls'
import { PreviewPane } from './components/PreviewPane'
import { SourceFolderPicker } from './components/SourceFolderPicker'
import { useDebouncedValue } from './hooks/useDebouncedValue'
import { useSpecState } from './hooks/useSpecState'

export default function App() {
  const { state, update, reroll, toggleImage, updateImage, removeImage, duplicateImage } = useSpecState()
  const [folderPath, setFolderPath] = useState('')
  const [options, setOptions] = useState<Options | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const lastUrl = useRef<string | null>(null)

  useEffect(() => {
    fetchOptions()
      .then(setOptions)
      .catch(() => {
        // Sin backend todavía no hay mucho que mostrar; los controles quedan
        // con el valor actual como única opción hasta que responda.
      })
  }, [])

  const debounced = useDebouncedValue(state, 300)

  useEffect(() => {
    if (debounced.images.length === 0) {
      setImageUrl(null)
      return
    }
    let vigente = true
    setLoading(true)
    setError(null)
    preview(debounced)
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

  const selectedPaths = new Set(state.images.map((img) => img.path))

  return (
    <div className="app">
      <header className="masthead">
        <h1>Proun</h1>
        <p className="muted">generador de wallpapers tipo collage</p>
      </header>
      <main className="layout">
        <div className="column">
          <SourceFolderPicker
            value={folderPath}
            onChange={setFolderPath}
            selectedPaths={selectedPaths}
            onToggle={toggleImage}
          />
          <ParamControls state={state} options={options} onUpdate={update} onReroll={reroll} />
          <ExportButton params={state} disabled={state.images.length === 0} />
        </div>
        <ImageConfigList
          images={state.images}
          options={options}
          onUpdate={updateImage}
          onRemove={removeImage}
          onDuplicate={duplicateImage}
        />
        <div className="column">
          <PreviewPane imageUrl={imageUrl} loading={loading} error={error} />
        </div>
      </main>
    </div>
  )
}
