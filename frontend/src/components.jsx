import { useEffect } from 'react'

export function Modal({ titulo, cerrar, children }) {
  useEffect(() => {
    const f = (e) => e.key === 'Escape' && cerrar()
    window.addEventListener('keydown', f)
    return () => window.removeEventListener('keydown', f)
  }, [cerrar])
  return (
    <div className="modal-fondo" onMouseDown={(e) => e.target === e.currentTarget && cerrar()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={titulo}>
        <div className="fila" style={{ marginBottom: 6 }}>
          <h2 className="grow" style={{ margin: 0 }}>{titulo}</h2>
          <button className="btn sec peq" onClick={cerrar} aria-label="Cerrar">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export const Progreso = ({ valor }) => (
  <div className={'barra' + (valor === 100 ? ' ok' : '')} title={`${valor} %`} role="progressbar" aria-valuenow={valor} aria-valuemin={0} aria-valuemax={100}>
    <i style={{ width: valor + '%' }} />
  </div>
)

const COLOR_ESTADO = { 'en curso': 'az', 'planeación': '', 'en pausa': 'warn', finalizado: 'ok', pendiente: '', completada: 'ok' }
export const Estado = ({ valor }) => <span className={'chip ' + (COLOR_ESTADO[valor] ?? '')}>{valor}</span>

export const Error = ({ texto }) => (texto ? <div className="error" role="alert">{texto}</div> : null)
