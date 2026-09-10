import type { ImageConfig, Options } from '../api/client'
import { ImageConfigPanel } from './ImageConfigPanel'

type Props = {
  images: ImageConfig[]
  options: Options | null
  onUpdate: (path: string, patch: Partial<ImageConfig>) => void
  onRemove: (path: string) => void
}

export function ImageConfigList({ images, options, onUpdate, onRemove }: Props) {
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
          key={img.path}
          config={img}
          options={options}
          onUpdate={(patch) => onUpdate(img.path, patch)}
          onRemove={() => onRemove(img.path)}
        />
      ))}
    </div>
  )
}
