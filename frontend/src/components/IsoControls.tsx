import { DEFAULT_FACE_COLORS, type FaceColors, type ShapeLayer } from '../api/client'
import { Stepper } from './Stepper'

type Props = {
  config: ShapeLayer
  // Figura -> [mínimo, por defecto, máximo] de su tamaño.
  figures: Record<string, [number, number, number]>
  onUpdate: (patch: Partial<ShapeLayer>) => void
}

const CARAS = ['arriba', 'izquierda', 'derecha'] as const

// Controles propios de una figura isométrica (proun/ops/iso.py): cuál
// figura, el largo de sus brazos y de qué color va cada cara. Las caras
// "del lote" pasan por el recoloreado global como cualquier capa; con
// colores propios, toLayerDict arma un colormap de tres stops para esta
// capa sola.
export function IsoControls({ config: c, figures, onUpdate }: Props) {
  const rango = figures[c.isoFigure] ?? [1, 1, 1]
  const [minimo, , maximo] = rango

  function setCara(indice: number, color: string) {
    const caras = [...(c.faceColors ?? DEFAULT_FACE_COLORS)] as FaceColors
    caras[indice] = color
    onUpdate({ faceColors: caras })
  }

  return (
    <>
      <span className="control-label">cuerpo</span>
      <div className="button-row wrap">
        {Object.entries(figures).map(([nombre, [, porDefecto]]) => (
          <button
            key={nombre}
            type="button"
            className={c.isoFigure === nombre ? 'active' : ''}
            // Cada figura arranca en su propio tamaño: el de una no siempre
            // es válido para otra (penrose pide al menos 4).
            onClick={() => onUpdate({ isoFigure: nombre, isoSize: porDefecto })}
          >
            {nombre}
          </button>
        ))}
      </div>
      {minimo < maximo && (
        <div className="row">
          <span className="control-label">largo</span>
          <Stepper
            value={c.isoSize}
            min={minimo}
            max={maximo}
            onChange={(isoSize) => onUpdate({ isoSize })}
          />
        </div>
      )}
      <span className="control-label">caras</span>
      <div className="button-row wrap">
        <button
          type="button"
          className={c.faceColors === null ? 'active' : ''}
          onClick={() => onUpdate({ faceColors: null })}
          title="las tres caras toman tonos del color y el recoloreado del lote"
        >
          del lote
        </button>
        <button
          type="button"
          className={c.faceColors !== null ? 'active' : ''}
          onClick={() => onUpdate({ faceColors: c.faceColors ?? DEFAULT_FACE_COLORS })}
          title="un color propio por cara"
        >
          tres colores
        </button>
      </div>
      {c.faceColors && (
        <div className="button-row wrap">
          {CARAS.map((cara, i) => (
            <label key={cara} className="row">
              <span className="control-label">{cara}</span>
              <input
                type="color"
                value={c.faceColors![i]}
                onChange={(e) => setCara(i, e.target.value)}
              />
            </label>
          ))}
        </div>
      )}
    </>
  )
}
