import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fechaCorta } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Error, Estado, Modal, Progreso } from '../components.jsx'

const ESTADOS = ['planeación', 'en curso', 'en pausa', 'finalizado']

export default function Proyectos() {
  const { esGerente } = useAuth()
  const [lista, setLista] = useState(null)
  const [clientes, setClientes] = useState([])
  const [abierto, setAbierto] = useState(false)
  const [f, setF] = useState({ nombre: '', descripcion: '', estado: 'planeación', fecha_inicio: '', fecha_entrega: '', cliente_id: '' })
  const [error, setError] = useState('')
  const [filtro, setFiltro] = useState('')

  const cargar = () => api.get('/proyectos').then(setLista)
  useEffect(() => { cargar(); api.get('/clientes').then(setClientes) }, [])

  const crear = async (e) => {
    e.preventDefault(); setError('')
    try {
      await api.post('/proyectos', { ...f, cliente_id: f.cliente_id ? Number(f.cliente_id) : null, fecha_inicio: f.fecha_inicio || null, fecha_entrega: f.fecha_entrega || null })
      setAbierto(false); setF({ nombre: '', descripcion: '', estado: 'planeación', fecha_inicio: '', fecha_entrega: '', cliente_id: '' }); cargar()
    } catch (err) { setError(err.message) }
  }
  const visibles = (lista || []).filter((p) => !filtro || p.estado === filtro)
  return (
    <>
      <div className="fila"><h1 className="grow">Proyectos</h1>{esGerente && <button className="btn" onClick={() => setAbierto(true)}>+ Nuevo proyecto</button>}</div>
      <p className="sub">{esGerente ? 'Todos los proyectos de la empresa.' : 'Los proyectos en los que estás asignado.'}</p>
      <div className="fila" style={{ marginBottom: 12 }}>
        <select style={{ width: 200 }} value={filtro} onChange={(e) => setFiltro(e.target.value)} aria-label="Filtrar por estado">
          <option value="">Todos los estados</option>{ESTADOS.map((e) => <option key={e}>{e}</option>)}
        </select>
      </div>
      <div className="card tabla-wrap">
        {!lista ? <div className="vacio">Cargando…</div> : visibles.length === 0 ? <div className="vacio">No hay proyectos para mostrar.</div> : (
          <table>
            <thead><tr><th>Proyecto</th><th>Cliente</th><th>Estado</th><th>Avance</th><th>Entrega</th></tr></thead>
            <tbody>{visibles.map((p) => (
              <tr key={p.id}>
                <td><Link to={`/proyectos/${p.id}`}><b>{p.nombre}</b></Link></td><td>{p.cliente || '—'}</td><td><Estado valor={p.estado} /></td>
                <td style={{ minWidth: 130 }}><Progreso valor={p.porcentaje} /><small>{p.porcentaje} %</small></td><td>{fechaCorta(p.fecha_entrega)}</td>
              </tr>))}</tbody>
          </table>
        )}
      </div>
      {abierto && (
        <Modal titulo="Nuevo proyecto" cerrar={() => setAbierto(false)}>
          <form onSubmit={crear}>
            <label>Nombre *</label><input required value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />
            <label>Descripción</label><textarea rows={3} value={f.descripcion} onChange={(e) => setF({ ...f, descripcion: e.target.value })} />
            <div className="fila"><div className="grow"><label>Cliente</label>
              <select value={f.cliente_id} onChange={(e) => setF({ ...f, cliente_id: e.target.value })}><option value="">— Sin cliente —</option>{clientes.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select></div>
              <div className="grow"><label>Estado</label><select value={f.estado} onChange={(e) => setF({ ...f, estado: e.target.value })}>{ESTADOS.map((e) => <option key={e}>{e}</option>)}</select></div></div>
            <div className="fila"><div className="grow"><label>Fecha de inicio</label><input type="date" value={f.fecha_inicio} onChange={(e) => setF({ ...f, fecha_inicio: e.target.value })} /></div>
              <div className="grow"><label>Fecha de entrega</label><input type="date" value={f.fecha_entrega} onChange={(e) => setF({ ...f, fecha_entrega: e.target.value })} /></div></div>
            <Error texto={error} />
            <div className="fila" style={{ marginTop: 14, justifyContent: 'flex-end' }}><button type="button" className="btn sec" onClick={() => setAbierto(false)}>Cancelar</button><button className="btn">Crear proyecto</button></div>
          </form>
        </Modal>
      )}
    </>
  )
}
