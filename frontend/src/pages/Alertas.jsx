import { useEffect, useState } from 'react'
import { api, fechaHora } from '../api.js'

const ICONO = { tarea_por_vencer: '⏰', proyecto_retrasado: '⚠️', cambio: '🔔' }
export default function Alertas() {
  const [a, setA] = useState(null)
  const cargar = () => api.get('/alertas').then(setA)
  useEffect(() => { cargar() }, [])
  const leer = async (x) => { await api.patch(`/alertas/${x.id}`); cargar() }
  return (
    <>
      <h1>Alertas</h1>
      <p className="sub">Tareas por vencer, proyectos retrasados o en riesgo y cambios en documentos o tareas.</p>
      <div className="card">{!a ? <div className="vacio">Cargando…</div> : a.length === 0 ? <div className="vacio">No tienes alertas.</div> : a.map((x) => (
        <div key={x.id} className={'alerta-item ' + x.tipo} style={{ opacity: x.leida ? 0.55 : 1 }}>
          <span>{ICONO[x.tipo]}</span><span style={{ flex: 1 }}>{x.mensaje}<div className="frag">{fechaHora(x.fecha)}</div></span>
          {!x.leida && <button className="btn sec peq" onClick={() => leer(x)}>Marcar como leída</button>}</div>))}</div>
    </>
  )
}
