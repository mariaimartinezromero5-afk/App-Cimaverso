import { useEffect, useState } from 'react'
import { api, fechaHora } from '../api.js'

export default function Actividad() {
  const [a, setA] = useState(null)
  useEffect(() => { api.get('/actividad?limite=100').then(setA) }, [])
  return (
    <>
      <h1>Historial de actividad</h1>
      <p className="sub">Trazabilidad de quién hizo qué y cuándo.</p>
      <div className="card">{!a ? <div className="vacio">Cargando…</div> : a.length === 0 ? <div className="vacio">Sin actividad registrada.</div> :
        a.map((e) => (<div className="linea" key={e.id}><b>{e.usuario}</b> {e.accion} <i>{e.detalle}</i><div className="frag">{fechaHora(e.fecha)}</div></div>))}</div>
    </>
  )
}
