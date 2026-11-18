import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Error, Modal } from '../components.jsx'

const VACIO = { nombre: '', contacto: '', correo: '', telefono: '' }
export default function Clientes() {
  const { esGerente } = useAuth()
  const [lista, setLista] = useState(null)
  const [edit, setEdit] = useState(null)
  const [f, setF] = useState(VACIO)
  const [error, setError] = useState('')
  const cargar = () => api.get('/clientes').then(setLista)
  useEffect(() => { cargar() }, [])
  const abrir = (c) => { setEdit(c || {}); setF(c ? { nombre: c.nombre, contacto: c.contacto, correo: c.correo, telefono: c.telefono } : VACIO); setError('') }
  const guardar = async (e) => {
    e.preventDefault(); setError('')
    try { edit.id ? await api.patch(`/clientes/${edit.id}`, f) : await api.post('/clientes', f); setEdit(null); cargar() } catch (err) { setError(err.message) }
  }
  return (
    <>
      <div className="fila"><h1 className="grow">Clientes</h1>{esGerente && <button className="btn" onClick={() => abrir(null)}>+ Nuevo cliente</button>}</div>
      <p className="sub">{esGerente ? 'Gestiona los clientes de Cimaverso.' : 'Consulta de clientes (solo lectura).'}</p>
      <div className="card tabla-wrap">{!lista ? <div className="vacio">Cargando…</div> : lista.length === 0 ? <div className="vacio">Aún no hay clientes registrados.</div> : (
        <table><thead><tr><th>Cliente</th><th>Contacto</th><th>Correo</th><th>Teléfono</th>{esGerente && <th></th>}</tr></thead>
          <tbody>{lista.map((c) => (<tr key={c.id}><td>🏢 <b>{c.nombre}</b></td><td>{c.contacto || '—'}</td><td>{c.correo || '—'}</td><td>{c.telefono || '—'}</td>{esGerente && <td><button className="btn sec peq" onClick={() => abrir(c)}>Editar</button></td>}</tr>))}</tbody></table>)}</div>
      {edit && (<Modal titulo={edit.id ? 'Editar cliente' : 'Nuevo cliente'} cerrar={() => setEdit(null)}>
        <form onSubmit={guardar}>
          <label>Nombre *</label><input required autoFocus value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />
          <label>Persona de contacto</label><input value={f.contacto} onChange={(e) => setF({ ...f, contacto: e.target.value })} />
          <div className="fila"><div className="grow"><label>Correo</label><input type="email" value={f.correo} onChange={(e) => setF({ ...f, correo: e.target.value })} /></div>
            <div className="grow"><label>Teléfono</label><input value={f.telefono} onChange={(e) => setF({ ...f, telefono: e.target.value })} /></div></div>
          <Error texto={error} />
          <div className="fila" style={{ marginTop: 14, justifyContent: 'flex-end' }}><button type="button" className="btn sec" onClick={() => setEdit(null)}>Cancelar</button><button className="btn">Guardar</button></div>
        </form></Modal>)}
    </>
  )
}
