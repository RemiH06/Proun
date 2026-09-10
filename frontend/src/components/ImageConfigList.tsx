import type { ImageConfig, Options } from '../api/client'
import { ImageConfigPanel } from './ImageConfigPanel'

type Props = {
  images: ImageConfig[]
  options: Options | null
  onUpdate: (id: string, patch: Partial<ImageConfig>) => void
  onRemove: (id: string) => void
  onDuplicate: (id: string) => void
}

export function ImageConfigList({ images, options, onUpdate, onRemove, onDuplicate }: Props) {
  if (images.length === 0) {
    return (
      <div className="column config-column">
        <p className="muted">selecciona miniaturas de la izquierda para configurarlas aquí</p>
      </div>
    )
  }

  return (
    <div className="column config-column">
      {images.map((img) => (
        <ImageConfigPanel
          key={img.id}
          config={img}
          options={options}
          onUpdate={(patch) => onUpdate(img.id, patch)}
          onRemove={() => onRemove(img.id)}
          onDuplicate={() => onDuplicate(img.id)}
        />
      ))}
    </div>
  )
}
