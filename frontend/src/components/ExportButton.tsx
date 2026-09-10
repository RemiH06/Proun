import { useState } from 'react'
import { exportImage, type ExportParams } from '../api/client'

type Props = {
  params: ExportParams
  disabled: boolean
}

export function ExportButton({ params, disabled }: Props) {
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function exportar() {
    setBusy(true)
    setStatus(null)
    try {
      const { path } = await exportImage(params)
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
      <p className="muted">{params.resolution}</p>
      <button className="primary" onClick={exportar} disabled={disabled || busy}>
        {busy ? 'exportando...' : 'exportar'}
      </button>
      {status && <p className="muted">{status}</p>}
    </section>
  )
}
