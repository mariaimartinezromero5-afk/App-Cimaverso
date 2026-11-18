import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api.js'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api.get('/auth/me').then(setUsuario).catch(() => setToken(null)).finally(() => setCargando(false))
  }, [])

  const login = async (correo, password) => {
    const r = await api.post('/auth/login', { correo, password })
    setToken(r.token)
    setUsuario(r.usuario)
  }
  const logout = async () => {
    try { await api.post('/auth/logout') } catch { /* sesión ya inválida */ }
    setToken(null)
    setUsuario(null)
  }
  return <Ctx.Provider value={{ usuario, cargando, login, logout, esGerente: usuario?.rol === 'gerente' }}>{children}</Ctx.Provider>
}
