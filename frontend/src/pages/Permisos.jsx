import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'

export default function Permisos() {
  const { usuario } = useAuth()
  const [m, setM] = useState(null)
  useEffect(() => { api.get('/permisos').then(setM) }, [])
  return (
    <>
      <h1>Permisos por rol</h1>
      <p className="sub">Tu rol actual es <span className="chip az">{usuario.rol}</span>. El servidor verifica estos permisos en cada petición.</p>
      <div className="card tabla-wrap">{!m ? <div className="vacio">Cargando…</div> : (
        <table><thead><tr><th>Funcionalidad</th><th style={usuario.rol === 'gerente' ? { color: 'var(--azul)' } : {}}>Gerente</th><th style={usuario.rol === 'desarrollador' ? { color: 'var(--azul)' } : {}}>Desarrollador</th></tr></thead>
          <tbody>{m.map((r) => (<tr key={r.funcionalidad}><td>{r.funcionalidad}</td><td>{r.gerente}</td><td>{r.desarrollador}</td></tr>))}</tbody></table>)}</div>
    </>
  )
}
