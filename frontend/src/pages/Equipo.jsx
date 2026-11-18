import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Error, Modal } from '../components.jsx'

export default function Equipo() {
  const [lista, setLista] = useState(null)
  const [edit, setEdit] = useState(null)
  const [f, setF] = useState({ nombre: '', correo: '', password: '', rol: 'desarrollador' })
  const [error, setError] = useState('')
  const cargar = () => api.get('/usuarios').then(setLista)
  useEffect(() => { cargar() }, [])
  const abrir = (u) => { setEdit(u || {}); setF(u ? { nombre: u.nombre, correo: u.correo, password: '', rol: u.rol } : { nombre: '', correo: '', password: '', rol: 'desarrollador' }); setError('') }
  const guardar = async (e) => {
    e.preventDefault(); setError('')
    try {
      if (edit.id) await api.patch(`/usuarios/${edit.id}`, { nombre: f.nombre, rol: f.rol, ...(f.password ? { password: f.password } : {}) })
      else await api.post('/usuarios', f)
      setEdit(null); cargar()
    } catch (err) { setError(err.message) }
  }
  const alternar = async (u) => { try { await api.patch(`/usuarios/${u.id}`, { activo: !u.activo }); cargar() } catch (err) { alert(err.message) } }
  return (
    <>
      <div className="fila"><h1 className="grow">Equipo</h1><button className="btn" onClick={() => abrir(null)}>+ Nuevo usuario</button></div>
      <p className="sub">Administra los usuarios y sus roles (solo el gerente).</p>
      <div className="card tabla-wrap">{!lista ? <div className="vacio">Cargando…</div> : (
        <table><thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th></th></tr></thead>
          <tbody>{lista.map((u) => (<tr key={u.id}><td>👤 <b>{u.nombre}</b></td><td>{u.correo}</td><td><span className={'chip ' + (u.rol === 'gerente' ? 'az' : '')}>{u.rol}</span></td>
            <td><span className={'chip ' + (u.activo ? 'ok' : 'err')}>{u.activo ? 'activo' : 'inactivo'}</span></td>
            <td><div className="fila" style={{ flexWrap: 'nowrap' }}><button className="btn sec peq" onClick={() => abrir(u)}>Editar</button><button className="btn sec peq" onClick={() => alternar(u)}>{u.activo ? 'Desactivar' : 'Activar'}</button></div></td></tr>))}</tbody></table>)}</div>
      {edit && (<Modal titulo={edit.id ? 'Editar usuario' : 'Nuevo usuario'} cerrar={() => setEdit(null)}>
        <form onSubmit={guardar}>
          <label>Nombre *</label><input required autoFocus value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />
          <label>Correo *</label><input type="email" required disabled={!!edit.id} value={f.correo} onChange={(e) => setF({ ...f, correo: e.target.value })} />
          <label>{edit.id ? 'Nueva contraseña (opcional)' : 'Contraseña * (mínimo 8 caracteres)'}</label><input type="password" required={!edit.id} minLength={f.password ? 8 : undefined} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete="new-password" />
          <label>Rol</label><select value={f.rol} onChange={(e) => setF({ ...f, rol: e.target.value })}><option>desarrollador</option><option>gerente</option></select>
          <Error texto={error} />
          <div className="fila" style={{ marginTop: 14, justifyContent: 'flex-end' }}><button type="button" className="btn sec" onClick={() => setEdit(null)}>Cancelar</button><button className="btn">Guardar</button></div>
        </form></Modal>)}
    </>
  )
}
