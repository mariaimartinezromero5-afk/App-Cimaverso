import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { Error } from '../components.jsx'

export default function Login() {
  const { login, usuario } = useAuth()
  const [correo, setCorreo] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const nav = useNavigate()
  if (usuario) return <Navigate to="/" replace />

  const enviar = async (e) => {
    e.preventDefault()
    setError(''); setEnviando(true)
    try { await login(correo, password); nav('/') } catch (err) { setError(err.message) } finally { setEnviando(false) }
  }
  return (
    <div className="login">
      <form className="card" onSubmit={enviar}>
        <div className="logo"><i>C</i> Cimaverso</div>
        <h2 style={{ textAlign: 'center' }}>Inicia sesión</h2>
        <label htmlFor="correo">Correo electrónico</label>
        <input id="correo" type="email" required autoFocus value={correo} onChange={(e) => setCorreo(e.target.value)} placeholder="tu@cimaverso.co" />
        <label htmlFor="pw">Contraseña</label>
        <input id="pw" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        <Error texto={error} />
        <button className="btn" style={{ width: '100%', marginTop: 14 }} disabled={enviando}>{enviando ? 'Ingresando…' : 'Ingresar'}</button>
        <div className="demo">
          <b>Cuentas de demostración</b> (contraseña <code>Cimaverso2026*</code>)<br />
          Gerente: gerente@cimaverso.co<br />Desarrolladora: laura@cimaverso.co
        </div>
      </form>
    </div>
  )
}
