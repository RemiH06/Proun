import { RESOLUTIONS } from '../api/client'
import type { BackgroundConfig, BackgroundDirection, BackgroundMode, FinishConfig } from '../api/client'
import { FinishControls } from './FinishControls'

type Props = {
  resolution: string
  background: BackgroundConfig
  finish: FinishConfig
  onResolutionChange: (resolution: string) => void
  onUpdateBackground: (patch: Partial<BackgroundConfig>) => void
  onUpdateFinish: (patch: Partial<FinishConfig>) => void
}

const GRUPOS: Array<{ label: string; group: 'escritorio' | 'celular' }> = [
  { label: 'escritorio', group: 'escritorio' },
  { label: 'celular', group: 'celular' },
]

const MODOS: Array<{ label: string; value: BackgroundMode }> = [
  { label: 'auto', value: 'auto' },
  { label: 'sólido', value: 'solid' },
  { label: 'degradado', value: 'gradient' },
]

const DIRECCIONES: Array<{ label: string; value: BackgroundDirection }> = [
  { label: 'vertical', value: 'vertical' },
  { label: 'horizontal', value: 'horizontal' },
  { label: 'diagonal', value: 'diagonal' },
  { label: 'radial', value: 'radial' },
]

export function CanvasControls({
  resolution,
  background,
  finish,
  onResolutionChange,
  onUpdateBackground,
  onUpdateFinish,
}: Props) {
  return (
    <section className="panel">
      <h2>Fondo y acabado</h2>

      <div className="control-group">
        <span className="control-label">Dimensiones del canvas</span>
        <select value={resolution} onChange={(e) => onResolutionChange(e.target.value)}>
          {GRUPOS.map(({ label, group }) => (
            <optgroup key={group} label={label}>
              {RESOLUTIONS.filter((r) => r.group === group).map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      <div className="control-group">
        <span className="control-label">Fondo</span>
        <div className="button-row">
          {MODOS.map(({ label, value }) => (
            <button
              key={value}
              type="button"
              className={background.mode === value ? 'active' : ''}
              onClick={() => onUpdateBackground({ mode: value })}
            >
              {label}
            </button>
          ))}
        </div>
        {background.mode === 'solid' && (
          <input
            type="color"
            value={background.solidColor}
            onChange={(e) => onUpdateBackground({ solidColor: e.target.value })}
          />
        )}
        {background.mode === 'gradient' && (
          <div className="sub-controls">
            <div className="row">
              <input
                type="color"
                value={background.gradientFrom}
                onChange={(e) => onUpdateBackground({ gradientFrom: e.target.value })}
              />
              <input
                type="color"
                value={background.gradientTo}
                onChange={(e) => onUpdateBackground({ gradientTo: e.target.value })}
              />
            </div>
            <div className="button-row wrap">
              {DIRECCIONES.map(({ label, value }) => (
                <button
                  key={value}
                  type="button"
                  className={background.direction === value ? 'active' : ''}
                  onClick={() => onUpdateBackground({ direction: value })}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}
        <span className="control-label">manchas de fondo</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={background.stainAmount}
          onChange={(e) => onUpdateBackground({ stainAmount: Number(e.target.value) })}
        />
      </div>

      <FinishControls finish={finish} onUpdate={onUpdateFinish} />

      <div className="control-group">
        <span className="control-label">Manchas del acabado</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={finish.stainAmount}
          onChange={(e) => onUpdateFinish({ stainAmount: Number(e.target.value) })}
        />
      </div>
    </section>
  )
}
