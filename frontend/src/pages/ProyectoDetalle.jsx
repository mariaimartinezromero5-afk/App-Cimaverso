import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fechaCorta, fechaHora, tamano } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Error, Estado, Modal, Progreso } from '../components.jsx'

const ESTADOS_TAREA = ['pendiente', 'en curso', 'completada']
const ESTADOS_PROY = ['planeación', 'en curso', 'en pausa', 'finalizado']

export default function ProyectoDetalle() {
  const { id } = useParams()
  const { esGerente } = useAuth()
  const nav = useNavigate()
  const [p, setP] = useState(null)
  const [tab, setTab] = useState('tareas')
  const [error, setError] = useState('')
  const cargar = useCallback(() => api.get(`/proyectos/${id}`).then(setP).catch((e) => setError(e.message)), [id])
  useEffect(() => { cargar() }, [cargar])

  if (error && !p) return <div className="card"><Error texto={error} /><button className="btn sec" onClick={() => nav('/proyectos')}>Volver</button></div>
  if (!p) return <div className="vacio">Cargando…</div>
  const cambiarEstado = async (estado) => { await api.patch(`/proyectos/${id}`, { estado }); cargar() }
  return (
    <>
      <p className="sub"><Link to="/proyectos">← Proyectos</Link></p>
      <div className="fila"><h1 className="grow">{p.nombre}</h1><Estado valor={p.estado} />
        {esGerente && <select style={{ width: 150 }} value={p.estado} onChange={(e) => cambiarEstado(e.target.value)} aria-label="Cambiar estado">{ESTADOS_PROY.map((e) => <option key={e}>{e}</option>)}</select>}
      </div>
      <p className="sub">{p.cliente || 'Sin cliente'} · {fechaCorta(p.fecha_inicio)} → {fechaCorta(p.fecha_entrega)}</p>
      <div className="card"><p style={{ margin: '0 0 12px' }}>{p.descripcion || 'Sin descripción.'}</p>
        <div className="fila"><div className="grow"><Progreso valor={p.porcentaje} /></div><b>{p.porcentaje} %</b><small>{p.tareas_completadas} de {p.tareas_total} tareas completadas</small></div></div>
      <div className="tabs" role="tablist">
        {[['tareas', `Tareas (${p.tareas.length})`], ['documentos', `Documentos (${p.documentos.length})`], ['miembros', `Equipo (${p.miembros.length})`], ['actividad', 'Actividad']].map(([k, t]) => (
          <button key={k} role="tab" className={tab === k ? 'activo' : ''} onClick={() => setTab(k)}>{t}</button>))}
      </div>
      {tab === 'tareas' && <Tareas p={p} recargar={cargar} />}
      {tab === 'documentos' && <Documentos p={p} recargar={cargar} />}
      {tab === 'miembros' && <Miembros p={p} recargar={cargar} />}
      {tab === 'actividad' && <ActividadProyecto id={id} />}
    </>
  )
}

function Tareas({ p, recargar }) {
  const [abierto, setAbierto] = useState(false)
  const [f, setF] = useState({ titulo: '', fecha_limite: '', responsable_id: '' })
  const [error, setError] = useState('')
  const hoy = new Date().toISOString().slice(0, 10)
  const crear = async (e) => {
    e.preventDefault(); setError('')
    try {
      await api.post(`/proyectos/${p.id}/tareas`, { titulo: f.titulo, fecha_limite: f.fecha_limite || null, responsable_id: f.responsable_id ? Number(f.responsable_id) : null })
      setAbierto(false); setF({ titulo: '', fecha_limite: '', responsable_id: '' }); recargar()
    } catch (err) { setError(err.message) }
  }
  const cambiar = async (t, estado) => { await api.patch(`/tareas/${t.id}`, { estado }); recargar() }
  return (
    <div className="card">
      <div className="fila"><h2 className="grow">Tareas</h2><button className="btn" onClick={() => setAbierto(true)}>+ Nueva tarea</button></div>
      {p.tareas.length === 0 ? <div className="vacio">Este proyecto aún no tiene tareas.</div> : (
        <div className="tabla-wrap"><table>
          <thead><tr><th>Tarea</th><th>Responsable</th><th>Fecha límite</th><th>Estado</th></tr></thead>
          <tbody>{p.tareas.map((t) => {
            const vencida = t.estado !== 'completada' && t.fecha_limite && t.fecha_limite < hoy
            return (<tr key={t.id}>
              <td style={{ textDecoration: t.estado === 'completada' ? 'line-through' : 'none' }}>{t.titulo}</td>
              <td>{t.responsable || '—'}</td>
              <td>{fechaCorta(t.fecha_limite)} {vencida && <span className="chip err">vencida</span>}</td>
              <td><select value={t.estado} onChange={(e) => cambiar(t, e.target.value)} style={{ width: 140 }} aria-label={`Estado de ${t.titulo}`}>{ESTADOS_TAREA.map((e) => <option key={e}>{e}</option>)}</select></td>
            </tr>)
          })}</tbody>
        </table></div>)}
      {abierto && (
        <Modal titulo="Nueva tarea" cerrar={() => setAbierto(false)}>
          <form onSubmit={crear}>
            <label>Título *</label><input required autoFocus value={f.titulo} onChange={(e) => setF({ ...f, titulo: e.target.value })} />
            <div className="fila"><div className="grow"><label>Responsable</label>
              <select value={f.responsable_id} onChange={(e) => setF({ ...f, responsable_id: e.target.value })}><option value="">— Sin asignar —</option>{p.miembros.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}</select></div>
              <div className="grow"><label>Fecha límite</label><input type="date" value={f.fecha_limite} onChange={(e) => setF({ ...f, fecha_limite: e.target.value })} /></div></div>
            <Error texto={error} />
            <div className="fila" style={{ marginTop: 14, justifyContent: 'flex-end' }}><button type="button" className="btn sec" onClick={() => setAbierto(false)}>Cancelar</button><button className="btn">Crear tarea</button></div>
          </form>
        </Modal>)}
    </div>
  )
}

function Documentos({ p, recargar }) {
  const [carpeta, setCarpeta] = useState(null)
  const [error, setError] = useState('')
  const [subiendo, setSubiendo] = useState(false)
  const [verVersiones, setVerVersiones] = useState(null)
  const [papelera, setPapelera] = useState(false)
  const [enPapelera, setEnPapelera] = useState([])
  const [nuevaCarpeta, setNuevaCarpeta] = useState(false)
  const [nombreCarpeta, setNombreCarpeta] = useState('')
  const input = useRef(null)
  const versionInput = useRef(null)
  const [docVersion, setDocVersion] = useState(null)

  const cargarPapelera = useCallback(() => api.get(`/documentos?proyecto=${p.id}&papelera=true`).then(setEnPapelera), [p.id])
  useEffect(() => { if (papelera) cargarPapelera() }, [papelera, cargarPapelera])

  const subir = async (archivo) => {
    if (!archivo) return
    setError(''); setSubiendo(true)
    const fd = new FormData(); fd.append('archivo', archivo); fd.append('proyecto_id', p.id)
    if (carpeta) fd.append('carpeta_id', carpeta)
    try { await api.upload('/documentos', fd); recargar() } catch (e) { setError(e.message) } finally { setSubiendo(false); if (input.current) input.current.value = '' }
  }
  const subirVersion = async (archivo) => {
    if (!archivo || !docVersion) return
    const fd = new FormData(); fd.append('archivo', archivo)
    try { await api.upload(`/documentos/${docVersion}/versiones`, fd); recargar() } catch (e) { setError(e.message) }
    setDocVersion(null); versionInput.current.value = ''
  }
  const abrirVersiones = async (d) => setVerVersiones({ doc: d, lista: await api.get(`/documentos/${d.id}/versiones`) })
  const aPapelera = async (d) => { await api.del(`/documentos/${d.id}`); recargar(); if (papelera) cargarPapelera() }
  const restaurar = async (d) => { await api.post(`/documentos/${d.id}/restaurar`); recargar(); cargarPapelera() }
  const crearCarpeta = async (e) => {
    e.preventDefault()
    try { await api.post(`/proyectos/${p.id}/carpetas`, { nombre: nombreCarpeta, padre_id: carpeta }); setNuevaCarpeta(false); setNombreCarpeta(''); recargar() } catch (err) { setError(err.message) }
  }
  const docs = p.documentos.filter((d) => (carpeta ? d.carpeta_id === carpeta : true))
  const nombreDe = (cid) => p.carpetas.find((c) => c.id === cid)?.nombre
  return (
    <div className="card">
      <div className="fila"><h2 className="grow">Documentos</h2>
        <button className="btn sec" onClick={() => setNuevaCarpeta(true)}>+ Carpeta</button>
        <button className="btn sec" onClick={() => setPapelera(!papelera)}>{papelera ? 'Ocultar papelera' : '🗑 Papelera'}</button></div>
      <div className="carpetas" style={{ marginTop: 12 }}>
        <button className={carpeta === null ? 'activo' : ''} onClick={() => setCarpeta(null)}>Todos</button>
        {p.carpetas.map((c) => <button key={c.id} className={carpeta === c.id ? 'activo' : ''} onClick={() => setCarpeta(c.id)}>📁 {c.nombre}</button>)}
      </div>
      <div className="drop" onClick={() => input.current.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); subir(e.dataTransfer.files[0]) }} role="button" tabIndex={0}>
        {subiendo ? 'Subiendo…' : <>⬆ Arrastra un archivo aquí o <b>haz clic para cargarlo</b>{carpeta ? ` en «${nombreDe(carpeta)}»` : ''}</>}
        <input ref={input} type="file" hidden onChange={(e) => subir(e.target.files[0])} />
      </div>
      <input ref={versionInput} type="file" hidden onChange={(e) => subirVersion(e.target.files[0])} />
      <Error texto={error} />
      {docs.length === 0 ? <div className="vacio">No hay documentos {carpeta ? 'en esta carpeta' : 'en este proyecto'}.</div> : (
        <div className="tabla-wrap"><table>
          <thead><tr><th>Nombre</th><th>Versión</th><th>Autor</th><th>Fecha</th><th>Tamaño</th><th></th></tr></thead>
          <tbody>{docs.map((d) => (
            <tr key={d.id}><td>📄 <b>{d.nombre}</b><div className="frag">{nombreDe(d.carpeta_id) || 'Sin carpeta'}</div></td>
              <td><button className="chip az" style={{ border: 0, cursor: 'pointer' }} onClick={() => abrirVersiones(d)}>v{d.version_actual}</button></td>
              <td>{d.autor}</td><td>{fechaHora(d.fecha)}</td><td>{tamano(d.tamano)}</td>
              <td><div className="fila" style={{ flexWrap: 'nowrap' }}>
                <button className="btn sec peq" onClick={() => api.descargar(d.id, d.nombre)}>Descargar</button>
                <button className="btn sec peq" onClick={() => { setDocVersion(d.id); versionInput.current.click() }}>Nueva versión</button>
                <button className="btn rojo peq" onClick={() => aPapelera(d)} aria-label={`Enviar ${d.nombre} a la papelera`}>🗑</button></div></td></tr>))}</tbody>
        </table></div>)}
      {papelera && (<><h3 style={{ marginTop: 22 }}>Papelera</h3>
        {enPapelera.length === 0 ? <div className="vacio">La papelera está vacía.</div> : enPapelera.map((d) => (
          <div className="fila" key={d.id} style={{ padding: '6px 0' }}><span className="grow">📄 {d.nombre}</span><button className="btn sec peq" onClick={() => restaurar(d)}>Restaurar</button></div>))}</>)}
      {verVersiones && (
        <Modal titulo={`Historial de ${verVersiones.doc.nombre}`} cerrar={() => setVerVersiones(null)}>
          <table><thead><tr><th>Versión</th><th>Autor</th><th>Fecha</th><th></th></tr></thead>
            <tbody>{verVersiones.lista.map((v) => (<tr key={v.id}><td><b>v{v.numero}</b></td><td>{v.autor}</td><td>{fechaHora(v.fecha)}</td>
              <td><button className="btn sec peq" onClick={() => api.descargar(verVersiones.doc.id, verVersiones.doc.nombre, v.numero)}>Descargar</button></td></tr>))}</tbody></table>
        </Modal>)}
      {nuevaCarpeta && (
        <Modal titulo={carpeta ? `Nueva subcarpeta en «${nombreDe(carpeta)}»` : 'Nueva carpeta'} cerrar={() => setNuevaCarpeta(false)}>
          <form onSubmit={crearCarpeta}><label>Nombre</label><input required autoFocus value={nombreCarpeta} onChange={(e) => setNombreCarpeta(e.target.value)} />
            <div className="fila" style={{ marginTop: 14, justifyContent: 'flex-end' }}><button className="btn">Crear</button></div></form>
        </Modal>)}
    </div>
  )
}

function Miembros({ p, recargar }) {
  const { esGerente } = useAuth()
  const [usuarios, setUsuarios] = useState([])
  const [sel, setSel] = useState('')
  useEffect(() => { if (esGerente) api.get('/usuarios').then(setUsuarios) }, [esGerente])
  const disponibles = usuarios.filter((u) => u.activo && !p.miembros.some((m) => m.id === u.id))
  const agregar = async () => { if (sel) { await api.post(`/proyectos/${p.id}/miembros`, { usuario_id: Number(sel) }); setSel(''); recargar() } }
  const quitar = async (uid) => { await api.del(`/proyectos/${p.id}/miembros/${uid}`); recargar() }
  return (
    <div className="card"><h2>Equipo del proyecto</h2>
      {p.miembros.length === 0 && <div className="vacio">Aún no hay miembros asignados.</div>}
      {p.miembros.map((m) => (<div key={m.id} className="fila" style={{ padding: '6px 0' }}><span className="grow">👤 <b>{m.nombre}</b> <small>({m.correo})</small></span>{esGerente && <button className="btn rojo peq" onClick={() => quitar(m.id)}>Quitar</button>}</div>))}
      {esGerente && (<div className="fila" style={{ marginTop: 14 }}><select className="grow" value={sel} onChange={(e) => setSel(e.target.value)} aria-label="Agregar miembro"><option value="">— Selecciona una persona —</option>{disponibles.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}</select><button className="btn" onClick={agregar} disabled={!sel}>Asignar</button></div>)}
    </div>
  )
}

function ActividadProyecto({ id }) {
  const [a, setA] = useState(null)
  useEffect(() => { api.get(`/actividad?proyecto=${id}&limite=50`).then(setA) }, [id])
  if (!a) return <div className="vacio">Cargando…</div>
  return (<div className="card"><h2>Historial de actividad</h2>{a.length === 0 && <div className="vacio">Sin actividad registrada.</div>}
    {a.map((e) => (<div className="linea" key={e.id}><b>{e.usuario}</b> {e.accion} <i>{e.detalle}</i><div className="frag">{fechaHora(e.fecha)}</div></div>))}</div>)
}
