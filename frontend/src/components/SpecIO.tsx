import { useRef, useState } from 'react'
import { fetchSpec, parseSpecJson, type PreviewParams } from '../api/client'

type Props = {
  state: PreviewParams
  disabled: boolean
  onImport: (spec: PreviewParams) => void
}

// Exporta la spec actual del GUI como el mismo JSON que acepta `--spec` en
// la CLI, y permite volver a importarla para seguir editándola acá: ver
// api/routes_render.py::spec_as_json y api/client.ts::parseSpecJson.
export function SpecIO({ state, disabled, onImport }: Props) {
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  async function exportar() {
    setBusy(true)
    setStatus(null)
    try {
      const data = await fetchSpec(state)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `proun_${state.seed}.json`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'no se pudo exportar el json')
    } finally {
      setBusy(false)
    }
  }

  async function importar(archivo: File) {
    setStatus(null)
    setWarnings([])
    try {
      const texto = await archivo.text()
      const data = JSON.parse(texto)
      const { spec, warnings: avisos } = parseSpecJson(data)
      onImport(spec)
      setWarnings(avisos)
      setStatus('json importado')
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'no se pudo importar el json')
    }
  }

  return (
    <section className="panel">
      <h2>JSON</h2>
      <div className="button-row wrap">
        <button type="button" onClick={exportar} disabled={disabled || busy}>
          {busy ? 'exportando...' : 'exportar json'}
        </button>
        <button type="button" onClick={() => inputRef.current?.click()}>
          importar json
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={(e) => {
            const archivo = e.target.files?.[0]
            if (archivo) importar(archivo)
            e.target.value = ''
          }}
        />
      </div>
      {status && <p className="muted">{status}</p>}
      {warnings.length > 0 && (
        <ul className="muted">
          {warnings.map((aviso, indice) => (
            <li key={indice}>{aviso}</li>
          ))}
        </ul>
      )}
    </section>
  )
}
