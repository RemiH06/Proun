type Props = {
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
}

// Número que solo se mueve a botonazos, nunca tecleado.
export function Stepper({ value, min, max, step = 1, onChange }: Props) {
  return (
    <div className="stepper">
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - step))}
        disabled={value <= min}
      >
        −
      </button>
      <span className="stepper-value">{value}</span>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + step))}
        disabled={value >= max}
      >
        +
      </button>
    </div>
  )
}
