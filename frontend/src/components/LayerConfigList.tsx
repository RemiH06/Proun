import type { LayerConfig, Options } from '../api/client'
import { LayerConfigPanel } from './LayerConfigPanel'

type Props = {
  layers: LayerConfig[]
  options: Options | null
  onUpdate: (id: string, patch: Partial<LayerConfig>) => void
  onRemove: (id: string) => void
  onDuplicate: (id: string) => void
}

export function LayerConfigList({ layers, options, onUpdate, onRemove, onDuplicate }: Props) {
  if (layers.length === 0) {
    return (
      <div className="column config-column">
        <p className="muted">selecciona miniaturas o agrega una figura/texto para configurarlas aquí</p>
      </div>
    )
  }

  return (
    <div className="column config-column">
      {layers.map((capa) => (
        <LayerConfigPanel
          key={capa.id}
          config={capa}
          options={options}
          onUpdate={(patch) => onUpdate(capa.id, patch)}
          onRemove={() => onRemove(capa.id)}
          onDuplicate={() => onDuplicate(capa.id)}
        />
      ))}
    </div>
  )
}
