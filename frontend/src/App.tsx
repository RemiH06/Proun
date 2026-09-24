import { useEffect, useRef, useState } from 'react'
import './App.css'
import { fetchOptions, preview, type Options } from './api/client'
import { AddLayerButtons } from './components/AddLayerButtons'
import { CanvasControls } from './components/CanvasControls'
import { ExportButton } from './components/ExportButton'
import { LayerConfigList } from './components/LayerConfigList'
import { ParamControls } from './components/ParamControls'
import { PreviewPane } from './components/PreviewPane'
import { RecolorView } from './components/RecolorView'
import { SourceFolderPicker } from './components/SourceFolderPicker'
import { useDebouncedValue } from './hooks/useDebouncedValue'
import { useSpecState } from './hooks/useSpecState'

type Vista = 'editor' | 'recolorear'

export default function App() {
  const [vista, setVista] = useState<Vista>('editor')
  const {
    state,
    update,
    reroll,
    toggleImage,
    addShape,
    addText,
    updateLayer,
    removeLayer,
    duplicateLayer,
    updateBackground,
    updateFinish,
  } = useSpecState()
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
    if (debounced.layers.length === 0) {
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

  const selectedPaths = new Set(
    state.layers.filter((capa) => capa.kind === 'image').map((capa) => capa.path),
  )

  return (
    <div className="app">
      <header className="masthead">
        <img src="/favicon.svg" alt="" className="masthead-mark" />
        <h1>Proun</h1>
        <p className="muted">generador de wallpapers tipo collage</p>
        <div className="view-switch">
          <button
            type="button"
            className={vista === 'editor' ? 'active' : ''}
            onClick={() => setVista('editor')}
          >
            editor
          </button>
          <button
            type="button"
            className={vista === 'recolorear' ? 'active' : ''}
            onClick={() => setVista('recolorear')}
          >
            recolorear
          </button>
        </div>
      </header>
      {vista === 'editor' ? (
        <main className="layout">
          <div className="column">
            <SourceFolderPicker
              value={folderPath}
              onChange={setFolderPath}
              selectedPaths={selectedPaths}
              onToggle={toggleImage}
            />
            <AddLayerButtons onAddShape={addShape} onAddText={addText} />
            <ParamControls state={state} options={options} onUpdate={update} onReroll={reroll} />
            <CanvasControls
              resolution={state.resolution}
              background={state.background}
              finish={state.finish}
              onResolutionChange={(resolution) => update('resolution', resolution)}
              onUpdateBackground={updateBackground}
              onUpdateFinish={updateFinish}
            />
            <ExportButton params={state} disabled={state.layers.length === 0} />
          </div>
          <LayerConfigList
            layers={state.layers}
            options={options}
            onUpdate={updateLayer}
            onRemove={removeLayer}
            onDuplicate={duplicateLayer}
          />
          <div className="column">
            <PreviewPane imageUrl={imageUrl} loading={loading} error={error} />
          </div>
        </main>
      ) : (
        <RecolorView />
      )}
    </div>
  )
}
