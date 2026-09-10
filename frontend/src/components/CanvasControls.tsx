import type { BackgroundConfig, BackgroundDirection, BackgroundMode, FinishConfig } from '../api/client'

type Props = {
  background: BackgroundConfig
  finish: FinishConfig
  onUpdateBackground: (patch: Partial<BackgroundConfig>) => void
  onUpdateFinish: (patch: Partial<FinishConfig>) => void
}

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

export function CanvasControls({ background, finish, onUpdateBackground, onUpdateFinish }: Props) {
  return (
    <section className="panel">
      <h2>Fondo y acabado</h2>

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

      <div className="control-group">
        <span className="control-label">Viñeta</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={finish.vignette}
          onChange={(e) => onUpdateFinish({ vignette: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Grano</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={finish.grain}
          onChange={(e) => onUpdateFinish({ grain: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Desenfoque</span>
        <input
          type="range"
          min={0}
          max={20}
          step={0.5}
          value={finish.blur}
          onChange={(e) => onUpdateFinish({ blur: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Contraste</span>
        <input
          type="range"
          min={0.5}
          max={2}
          step={0.05}
          value={finish.contrast}
          onChange={(e) => onUpdateFinish({ contrast: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Brillo</span>
        <input
          type="range"
          min={0.5}
          max={2}
          step={0.05}
          value={finish.brightness}
          onChange={(e) => onUpdateFinish({ brightness: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Saturación</span>
        <input
          type="range"
          min={0.5}
          max={2}
          step={0.05}
          value={finish.saturation}
          onChange={(e) => onUpdateFinish({ saturation: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Veladura</span>
        <div className="button-row">
          <button
            type="button"
            className={finish.overlay.on ? 'active' : ''}
            onClick={() => onUpdateFinish({ overlay: { ...finish.overlay, on: !finish.overlay.on } })}
          >
            {finish.overlay.on ? 'activa' : 'apagada'}
          </button>
        </div>
        {finish.overlay.on && (
          <div className="sub-controls">
            <input
              type="color"
              value={finish.overlay.color}
              onChange={(e) => onUpdateFinish({ overlay: { ...finish.overlay, color: e.target.value } })}
            />
            <span className="control-label">opacidad</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={finish.overlay.opacity}
              onChange={(e) =>
                onUpdateFinish({ overlay: { ...finish.overlay, opacity: Number(e.target.value) } })
              }
            />
          </div>
        )}
      </div>

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
