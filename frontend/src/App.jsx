import { useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { api } from './api.js'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Proyectos from './pages/Proyectos.jsx'
import ProyectoDetalle from './pages/ProyectoDetalle.jsx'
import Busqueda from './pages/Busqueda.jsx'
import Clientes from './pages/Clientes.jsx'
import Equipo from './pages/Equipo.jsx'
import Permisos from './pages/Permisos.jsx'
import Actividad from './pages/Actividad.jsx'
import Alertas from './pages/Alertas.jsx'

function Layout({ children }) {
  const { usuario, logout, esGerente } = useAuth()
  const [abierto, setAbierto] = useState(false)
  const [pendientes, setPendientes] = useState(0)
  const nav = useNavigate()
  const loc = useLocation()

  useEffect(() => { setAbierto(false) }, [loc.pathname])
  useEffect(() => {
    api.get('/dashboard').then((d) => setPendientes(d.alertas_no_leidas)).catch(() => {})
  }, [loc.pathname])

  const salir = async () => { await logout(); nav('/login') }
  const Item = ({ to, icono, children: c }) => (
    <NavLink to={to} className={({ isActive }) => (isActive ? 'activo' : '')}><span>{icono}</span>{c}</NavLink>
  )
  return (
    <div className="app">
      <aside className={'side' + (abierto ? ' abierto' : '')}>
        <div className="logo"><i>C</i> Cimaverso</div>
        <nav>
          <Item to="/" icono="📊">Dashboard</Item>
          <Item to="/proyectos" icono="📁">Proyectos</Item>
          <Item to="/busqueda" icono="🔎">Búsqueda</Item>
          <Item to="/clientes" icono="🏢">Clientes</Item>
          {esGerente && <Item to="/equipo" icono="👥">Equipo</Item>}
          <Item to="/permisos" icono="🔐">Permisos</Item>
          <Item to="/actividad" icono="🕑">Actividad</Item>
        </nav>
        <div className="yo"><b>{usuario.nombre}</b>{usuario.rol}<button onClick={salir}>Cerrar sesión</button></div>
      </aside>
      <div className="main">
        <header className="top">
          <button className="menu-btn" onClick={() => setAbierto(!abierto)} aria-label="Abrir menú">☰</button>
          <div className="grow"><strong>Gestión documental y de proyectos</strong></div>
          <button className="campana" onClick={() => nav('/alertas')} aria-label={`Alertas: ${pendientes} sin leer`}>🔔{pendientes > 0 && <span>{pendientes}</span>}</button>
        </header>
        <div className="page">{children}</div>
      </div>
    </div>
  )
}

export default function App() {
  const { usuario, cargando, esGerente } = useAuth()
  if (cargando) return <div className="vacio">Cargando…</div>
  if (!usuario) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/proyectos" element={<Proyectos />} />
        <Route path="/proyectos/:id" element={<ProyectoDetalle />} />
        <Route path="/busqueda" element={<Busqueda />} />
        <Route path="/clientes" element={<Clientes />} />
        <Route path="/equipo" element={esGerente ? <Equipo /> : <Navigate to="/" replace />} />
        <Route path="/permisos" element={<Permisos />} />
        <Route path="/actividad" element={<Actividad />} />
        <Route path="/alertas" element={<Alertas />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
