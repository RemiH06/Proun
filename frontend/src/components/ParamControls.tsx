import type { Options } from '../api/client'
import type { SpecState } from '../hooks/useSpecState'

type Props = {
  state: SpecState
  options: Options | null
  onUpdate: <K extends keyof SpecState>(key: K, value: SpecState[K]) => void
  onReroll: () => void
}

export function ParamControls({ state, options, onUpdate, onReroll }: Props) {
  return (
    <section className="panel">
      <h2>Parámetros</h2>

      <label>
        Layout
        <select value={state.layoutMode} onChange={(e) => onUpdate('layoutMode', e.target.value)}>
          {(options?.layout_modes ?? [state.layoutMode]).map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>

      <label>
        Color principal
        <div className="row">
          <input
            type="color"
            value={state.color}
            onChange={(e) => onUpdate('color', e.target.value)}
          />
          <input
            type="text"
            value={state.color}
            onChange={(e) => onUpdate('color', e.target.value)}
          />
        </div>
      </label>

      <label>
        Recoloreado
        <select
          value={state.recolorMode}
          onChange={(e) => onUpdate('recolorMode', e.target.value)}
        >
          {(options?.recolor_modes ?? [state.recolorMode]).map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>

      <label>
        Semilla
        <div className="row">
          <input type="text" readOnly value={state.seed} />
          <button onClick={onReroll}>rehacer</button>
        </div>
      </label>
    </section>
  )
}
