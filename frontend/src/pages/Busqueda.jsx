import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fechaHora } from '../api.js'

export default function Busqueda() {
  const [f, setF] = useState({ q: '', proyecto: '', tipo: '', desde: '', hasta: '', responsable: '' })
  const [proyectos, setProyectos] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [res, setRes] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)
  useEffect(() => { api.get('/proyectos').then(setProyectos); api.get('/usuarios').then(setUsuarios) }, [])

  const buscar = async (e) => {
    e?.preventDefault(); setError(''); setCargando(true)
    const params = new URLSearchParams()
    Object.entries(f).forEach(([k, v]) => v && params.set(k, v))
    try { setRes(await api.get('/busqueda?' + params)) } catch (err) { setError(err.message) } finally { setCargando(false) }
  }
  const resaltar = (txt) => {
    if (!f.q.trim() || !txt) return txt
    const palabra = f.q.trim().split(/\s+/)[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    return txt.split(new RegExp(`(${palabra})`, 'ig')).map((t, i) => (t.toLowerCase() === palabra.toLowerCase() ? <mark key={i}>{t}</mark> : t))
  }
  return (
    <>
      <h1>Búsqueda de documentos</h1>
      <p className="sub">Busca por palabras dentro del contenido de los documentos, o filtra por proyecto, tipo, fecha y responsable.</p>
      <form className="card" onSubmit={buscar}>
        <div className="fila"><input className="grow" placeholder="Ej.: garantía, contrato, requerimientos…" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} aria-label="Texto a buscar" /><button className="btn" disabled={cargando}>{cargando ? 'Buscando…' : 'Buscar'}</button></div>
        <div className="fila" style={{ marginTop: 10 }}>
          <select className="grow" value={f.proyecto} onChange={(e) => setF({ ...f, proyecto: e.target.value })} aria-label="Proyecto"><option value="">Todos los proyectos</option>{proyectos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select>
          <select className="grow" value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value })} aria-label="Tipo de archivo"><option value="">Todos los tipos</option>{['pdf', 'docx', 'txt', 'md', 'xlsx', 'png'].map((t) => <option key={t}>{t}</option>)}</select>
          <select className="grow" value={f.responsable} onChange={(e) => setF({ ...f, responsable: e.target.value })} aria-label="Responsable"><option value="">Cualquier responsable</option>{usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}</select>
          <input type="date" className="grow" value={f.desde} onChange={(e) => setF({ ...f, desde: e.target.value })} aria-label="Desde" />
          <input type="date" className="grow" value={f.hasta} onChange={(e) => setF({ ...f, hasta: e.target.value })} aria-label="Hasta" />
        </div>
      </form>
      {error && <div className="error">{error}</div>}
      {res && (<div className="card"><h2>{res.length} resultado{res.length === 1 ? '' : 's'}</h2>
        {res.length === 0 && <div className="vacio">No se encontraron documentos con esos criterios.</div>}
        {res.map((r) => (<div key={r.id} style={{ padding: '10px 0', borderBottom: '1px solid #f0f2f6' }}>
          <div className="fila"><span className="grow">📄 <b>{r.nombre}</b> <span className="chip az">v{r.version}</span> <small>· <Link to={`/proyectos/${r.proyecto_id}`}>{r.proyecto}</Link> · {r.autor} · {fechaHora(r.fecha)}</small></span>
            <button className="btn sec peq" onClick={() => api.descargar(r.id, r.nombre)}>Descargar</button></div>
          {r.fragmento && <div className="frag">{resaltar(r.fragmento)}</div>}</div>))}</div>)}
    </>
  )
}
