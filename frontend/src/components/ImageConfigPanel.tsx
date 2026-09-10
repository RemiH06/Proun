import type { ImageConfig, Options } from '../api/client'
import { thumbnailUrl } from '../api/client'
import { PositionPad } from './PositionPad'
import { Stepper } from './Stepper'

type Props = {
  config: ImageConfig
  options: Options | null
  onUpdate: (patch: Partial<ImageConfig>) => void
  onRemove: () => void
  onDuplicate: () => void
}

const ANGLES = [0, 90, 180, 270] as const

type Direccion = -1 | 0 | 1

// [dx, dy] por dirección; el centro (sin flecha) no existe, es "repeat" apagado.
const DIRECCIONES: Array<{ label: string; dx: Direccion; dy: Direccion }> = [
  { label: '↖', dx: -1, dy: -1 },
  { label: '↑', dx: 0, dy: -1 },
  { label: '↗', dx: 1, dy: -1 },
  { label: '←', dx: -1, dy: 0 },
  { label: '·', dx: 0, dy: 0 },
  { label: '→', dx: 1, dy: 0 },
  { label: '↙', dx: -1, dy: 1 },
  { label: '↓', dx: 0, dy: 1 },
  { label: '↘', dx: 1, dy: 1 },
]

// Mismo compás que DIRECCIONES, sin el centro (el pivote siempre queda
// afuera de la imagen); spacing (slider aparte) escala esta dirección.
const PIVOTES: Array<{ label: string; dx: number; dy: number }> = [
  { label: '←', dx: -1, dy: 0 },
  { label: '↑', dx: 0, dy: -1 },
  { label: '→', dx: 1, dy: 0 },
  { label: '↓', dx: 0, dy: 1 },
  { label: '↘ esquina', dx: 1, dy: 1 },
]

const GRIDS: Array<[number, number]> = [
  [2, 1],
  [1, 2],
  [2, 2],
  [3, 3],
  [4, 1],
  [1, 4],
]

export function ImageConfigPanel({ config: c, options, onUpdate, onRemove, onDuplicate }: Props) {
  const blendModes = options?.blend_modes ?? [c.blend]

  return (
    <section className="panel image-panel">
      <div className="image-panel-header">
        <img className="image-panel-thumb" src={thumbnailUrl(c.path, 64)} alt={c.name} />
        <span className="image-panel-name" title={c.name}>
          {c.name}
        </span>
        <button type="button" className="duplicate" onClick={onDuplicate} title="agregar otra vez">
          +
        </button>
        <button type="button" className="remove" onClick={onRemove} title="quitar">
          ×
        </button>
      </div>

      <div className="control-group">
        <span className="control-label">Posición</span>
        <PositionPad value={c.position} onChange={(position) => onUpdate({ position })} />
      </div>

      <div className="control-group">
        <span className="control-label">Rotar</span>
        <div className="button-row">
          {ANGLES.map((a) => (
            <button
              key={a}
              type="button"
              className={c.angle === a ? 'active' : ''}
              onClick={() => onUpdate({ angle: a })}
            >
              {a}°
            </button>
          ))}
        </div>
      </div>

      <div className="control-group">
        <span className="control-label">Voltear</span>
        <div className="button-row">
          <button
            type="button"
            className={c.flipH ? 'active' : ''}
            onClick={() => onUpdate({ flipH: !c.flipH })}
            title="voltear horizontal"
          >
            ↔
          </button>
          <button
            type="button"
            className={c.flipV ? 'active' : ''}
            onClick={() => onUpdate({ flipV: !c.flipV })}
            title="voltear vertical"
          >
            ↕
          </button>
        </div>
      </div>

      <div className="control-group">
        <span className="control-label">Opacidad</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={c.opacity}
          onChange={(e) => onUpdate({ opacity: Number(e.target.value) })}
        />
      </div>

      <div className="control-group">
        <span className="control-label">Fusión</span>
        <div className="button-row wrap">
          {blendModes.map((m) => (
            <button
              key={m}
              type="button"
              className={c.blend === m ? 'active' : ''}
              onClick={() => onUpdate({ blend: m })}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="control-group">
        <span className="control-label">Color propio</span>
        <div className="button-row">
          <button
            type="button"
            className={c.color === null ? 'active' : ''}
            onClick={() => onUpdate({ color: null })}
          >
            del lote
          </button>
          <input
            type="color"
            value={c.color ?? '#3ba7ff'}
            onChange={(e) => onUpdate({ color: e.target.value })}
          />
        </div>
      </div>

      <div className="control-group">
        <span className="control-label">Repetición</span>
        <div className="button-row">
          <button
            type="button"
            className={c.repeat === null ? 'active' : ''}
            onClick={() => onUpdate({ repeat: null })}
          >
            sin repetir
          </button>
          <button
            type="button"
            className={c.repeat?.kind === 'linear' ? 'active' : ''}
            onClick={() =>
              onUpdate({
                repeat: { kind: 'linear', dirX: 1, dirY: 0, spacing: 1, times: 1, mirror: false },
              })
            }
          >
            lineal
          </button>
          <button
            type="button"
            className={c.repeat?.kind === 'kaleidoscope' ? 'active' : ''}
            onClick={() =>
              onUpdate({
                repeat: { kind: 'kaleidoscope', pivotDirX: 1, pivotDirY: 0, spacing: 0.5, sectors: 6 },
              })
            }
          >
            caleidoscopio
          </button>
        </div>

        {c.repeat?.kind === 'linear' && (
          <div className="sub-controls">
            <div className="compass">
              {DIRECCIONES.map(({ label, dx, dy }) => (
                <button
                  key={label}
                  type="button"
                  disabled={dx === 0 && dy === 0}
                  className={
                    c.repeat?.kind === 'linear' && c.repeat.dirX === dx && c.repeat.dirY === dy
                      ? 'active'
                      : ''
                  }
                  onClick={() =>
                    c.repeat?.kind === 'linear' && onUpdate({ repeat: { ...c.repeat, dirX: dx, dirY: dy } })
                  }
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="control-label">espaciado</span>
            <input
              type="range"
              min={0.1}
              max={2}
              step={0.05}
              value={c.repeat.spacing}
              onChange={(e) =>
                c.repeat?.kind === 'linear' &&
                onUpdate({ repeat: { ...c.repeat, spacing: Number(e.target.value) } })
              }
            />
            <div className="row">
              <span className="control-label">copias</span>
              <Stepper
                value={c.repeat.times}
                min={1}
                max={12}
                onChange={(times) =>
                  c.repeat?.kind === 'linear' && onUpdate({ repeat: { ...c.repeat, times } })
                }
              />
              <button
                type="button"
                className={c.repeat.mirror ? 'active' : ''}
                onClick={() =>
                  c.repeat?.kind === 'linear' && onUpdate({ repeat: { ...c.repeat, mirror: !c.repeat.mirror } })
                }
              >
                espejo
              </button>
            </div>
          </div>
        )}

        {c.repeat?.kind === 'kaleidoscope' && (
          <div className="sub-controls">
            <div className="button-row wrap">
              {PIVOTES.map(({ label, dx, dy }) => (
                <button
                  key={label}
                  type="button"
                  className={
                    c.repeat?.kind === 'kaleidoscope' &&
                    c.repeat.pivotDirX === dx &&
                    c.repeat.pivotDirY === dy
                      ? 'active'
                      : ''
                  }
                  onClick={() =>
                    c.repeat?.kind === 'kaleidoscope' &&
                    onUpdate({ repeat: { ...c.repeat, pivotDirX: dx, pivotDirY: dy } })
                  }
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="control-label">espaciado (qué tan lejos se abre)</span>
            <input
              type="range"
              min={0.1}
              max={1.5}
              step={0.05}
              value={c.repeat.spacing}
              onChange={(e) =>
                c.repeat?.kind === 'kaleidoscope' &&
                onUpdate({ repeat: { ...c.repeat, spacing: Number(e.target.value) } })
              }
            />
            <div className="row">
              <span className="control-label">sectores</span>
              <Stepper
                value={c.repeat.sectors}
                min={2}
                max={12}
                onChange={(sectors) =>
                  c.repeat?.kind === 'kaleidoscope' && onUpdate({ repeat: { ...c.repeat, sectors } })
                }
              />
            </div>
          </div>
        )}
      </div>

      <div className="control-group">
        <span className="control-label">Mosaico</span>
        <div className="button-row">
          <button
            type="button"
            className={c.mosaic === null ? 'active' : ''}
            onClick={() => onUpdate({ mosaic: null })}
          >
            sin mosaico
          </button>
        </div>
        <div className="button-row wrap">
          {GRIDS.map(([cols, rows]) => (
            <button
              key={`${cols}x${rows}`}
              type="button"
              className={c.mosaic?.cols === cols && c.mosaic?.rows === rows ? 'active' : ''}
              onClick={() => onUpdate({ mosaic: { cols, rows, mirror: c.mosaic?.mirror ?? false } })}
            >
              {cols}x{rows}
            </button>
          ))}
        </div>
        {c.mosaic && (
          <div className="row">
            <button
              type="button"
              className={c.mosaic.mirror ? 'active' : ''}
              onClick={() => c.mosaic && onUpdate({ mosaic: { ...c.mosaic, mirror: !c.mosaic.mirror } })}
            >
              espejo
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
