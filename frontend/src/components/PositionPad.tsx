import { useRef } from 'react'

type Point = { x: number; y: number }

type Props = {
  value: Point | null
  onChange: (value: Point | null) => void
}

// Cuadrito que representa el lienzo entero: arrastrar adentro fija dónde cae
// el centro de la imagen (fracción 0-1, lo mismo que ya acepta `position`
// por capa en el motor). Sin marcador = "auto", el layout la ubica solo.
export function PositionPad({ value, onChange }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  function moveTo(clientX: number, clientY: number) {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    const x = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
    const y = Math.min(1, Math.max(0, (clientY - rect.top) / rect.height))
    onChange({ x, y })
  }

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    e.currentTarget.setPointerCapture(e.pointerId)
    moveTo(e.clientX, e.clientY)
  }

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (e.buttons !== 1) return
    moveTo(e.clientX, e.clientY)
  }

  return (
    <div className="row">
      <div
        ref={ref}
        className="position-pad"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
      >
        {value && (
          <div
            className="position-pad-marker"
            style={{ left: `${value.x * 100}%`, top: `${value.y * 100}%` }}
          />
        )}
      </div>
      <button type="button" className={value === null ? 'active' : ''} onClick={() => onChange(null)}>
        auto
      </button>
    </div>
  )
}
