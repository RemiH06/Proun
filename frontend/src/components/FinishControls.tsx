import type { FinishConfig } from '../api/client'

type Props = {
  finish: FinishConfig
  onUpdate: (patch: Partial<FinishConfig>) => void
}

// Los siete efectos de "acabado" que no son manchas (esas ya tienen su
// propio control: global en `background`/`finish.stain`, o por capa en
// `stain`). Un solo componente para que el panel global (`CanvasControls`)
// y el de cada capa (`LayerConfigPanel`) no dupliquen estos sliders.
export function FinishControls({ finish, onUpdate }: Props) {
  return (
    <>
      <div className="control-group">
        <span className="control-label">Viñeta</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={finish.vignette}
          onChange={(e) => onUpdate({ vignette: Number(e.target.value) })}
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
          onChange={(e) => onUpdate({ grain: Number(e.target.value) })}
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
          onChange={(e) => onUpdate({ blur: Number(e.target.value) })}
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
          onChange={(e) => onUpdate({ contrast: Number(e.target.value) })}
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
          onChange={(e) => onUpdate({ brightness: Number(e.target.value) })}
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
          onChange={(e) => onUpdate({ saturation: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Veladura</span>
        <div className="button-row">
          <button
            type="button"
            className={finish.overlay.on ? 'active' : ''}
            onClick={() => onUpdate({ overlay: { ...finish.overlay, on: !finish.overlay.on } })}
          >
            {finish.overlay.on ? 'activa' : 'apagada'}
          </button>
        </div>
        {finish.overlay.on && (
          <div className="sub-controls">
            <input
              type="color"
              value={finish.overlay.color}
              onChange={(e) => onUpdate({ overlay: { ...finish.overlay, color: e.target.value } })}
            />
            <span className="control-label">opacidad</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={finish.overlay.opacity}
              onChange={(e) =>
                onUpdate({ overlay: { ...finish.overlay, opacity: Number(e.target.value) } })
              }
            />
          </div>
        )}
      </div>
    </>
  )
}
