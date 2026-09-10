import type { ShapeKind } from '../api/client'

type Props = {
  onAddShape: (kind: ShapeKind) => void
  onAddText: () => void
}

const SHAPES: Array<{ label: string; kind: ShapeKind }> = [
  { label: 'rectángulo', kind: 'rect' },
  { label: 'círculo', kind: 'circle' },
  { label: 'triángulo', kind: 'triangle' },
  { label: 'rombo', kind: 'diamond' },
  { label: 'polígono', kind: 'polygon' },
]

export function AddLayerButtons({ onAddShape, onAddText }: Props) {
  return (
    <section className="panel">
      <h2>Agregar capa</h2>
      <div className="control-group">
        <span className="control-label">Figura</span>
        <div className="button-row wrap">
          {SHAPES.map(({ label, kind }) => (
            <button key={kind} type="button" onClick={() => onAddShape(kind)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="control-group">
        <button type="button" onClick={onAddText}>
          + texto
        </button>
      </div>
    </section>
  )
}
