import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fechaCorta } from '../api.js'
import { Estado, Progreso } from '../components.jsx'

const ICONO = { tarea_por_vencer: '⏰', proyecto_retrasado: '⚠️', cambio: '🔔' }

export default function Dashboard() {
  const [d, setD] = useState(null)
  useEffect(() => { api.get('/dashboard').then(setD) }, [])
  if (!d) return <div className="vacio">Cargando…</div>
  const maxCarga = Math.max(1, ...d.carga_trabajo.map((c) => c.pendientes))
  return (
    <>
      <h1>Dashboard</h1>
      <p className="sub">Resumen de proyectos, avance de tareas y alertas.</p>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <div className="card kpi"><div className="ico">📁</div><div><div className="n">{d.proyectos_activos}</div><small>Proyectos activos</small></div></div>
        <div className="card kpi"><div className="ico">✅</div><div><div className="n">{d.porcentaje_global} %</div><small>Tareas completadas ({d.tareas_completadas}/{d.tareas_total})</small></div></div>
        <div className="card kpi"><div className="ico" style={{ background: 'var(--err-bg)' }}>⏰</div><div><div className="n">{d.tareas_vencidas}</div><small>Tareas vencidas</small></div></div>
        <div className="card kpi"><div className="ico">📄</div><div><div className="n">{d.documentos}</div><small>Documentos activos</small></div></div>
      </div>
      <div className="grid g2">
        <div className="card">
          <h2>Proyectos activos y su estado</h2>
          {d.proyectos.length === 0 && <div className="vacio">No tienes proyectos activos.</div>}
          <div className="tabla-wrap"><table>
            <thead><tr><th>Proyecto</th><th>Estado</th><th>Avance</th><th>Entrega</th></tr></thead>
            <tbody>
              {d.proyectos.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/proyectos/${p.id}`}><b>{p.nombre}</b></Link><div className="frag">{p.cliente}</div></td>
                  <td><Estado valor={p.estado} /></td>
                  <td style={{ minWidth: 120 }}><Progreso valor={p.porcentaje} /><small>{p.porcentaje} % · {p.tareas_completadas}/{p.tareas_total}</small></td>
                  <td>{fechaCorta(p.fecha_entrega)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
        <div>
          <div className="card">
            <h2>Alertas recientes</h2>
            {d.alertas.length === 0 && <div className="vacio">Sin alertas pendientes 🎉</div>}
            {d.alertas.map((a) => (
              <div key={a.id} className={'alerta-item ' + a.tipo}><span>{ICONO[a.tipo]}</span><span>{a.mensaje}</span></div>
            ))}
            <Link to="/alertas">Ver todas las alertas →</Link>
          </div>
          {d.carga_trabajo.length > 0 && (
            <div className="card">
              <h2>Carga de trabajo (tareas pendientes)</h2>
              {d.carga_trabajo.map((c) => (
                <div className="carga-fila" key={c.usuario}><span>{c.usuario}</span><div className="barra"><i style={{ width: (100 * c.pendientes) / maxCarga + '%' }} /></div><b>{c.pendientes}</b></div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
