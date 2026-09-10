import { useState } from 'react'
import { exportImage, type ExportParams } from '../api/client'

const RESOLUTIONS = ['1280x720', '1920x1080', '2560x1440', '3840x2160']

type Props = {
  params: Omit<ExportParams, 'resolution'>
  disabled: boolean
}

export function ExportButton({ params, disabled }: Props) {
  const [resolution, setResolution] = useState('1920x1080')
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function exportar() {
    setBusy(true)
    setStatus(null)
    try {
      const { path } = await exportImage({ ...params, resolution })
      setStatus(path ? `guardado en ${path}` : 'exportado')
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'no se pudo exportar')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2>Exportar</h2>
      <div className="row">
        <select value={resolution} onChange={(e) => setResolution(e.target.value)}>
          {RESOLUTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <button className="primary" onClick={exportar} disabled={disabled || busy}>
          {busy ? 'exportando...' : 'exportar'}
        </button>
      </div>
      {status && <p className="muted">{status}</p>}
    </section>
  )
}
