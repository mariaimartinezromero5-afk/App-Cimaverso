// Cliente de la API REST (/api). El token JWT se guarda en sessionStorage.
const TOKEN = 'cimaverso_token'

export const getToken = () => sessionStorage.getItem(TOKEN)
export const setToken = (t) => (t ? sessionStorage.setItem(TOKEN, t) : sessionStorage.removeItem(TOKEN))

async function request(method, url, body, isForm = false) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body && !isForm) headers['Content-Type'] = 'application/json'
  const res = await fetch('/api' + url, { method, headers, body: body ? (isForm ? body : JSON.stringify(body)) : undefined })
  if (res.status === 401 && token) {
    setToken(null)
    window.location.href = '/login'
    throw new Error('Sesión expirada')
  }
  const texto = await res.text()
  const datos = texto ? JSON.parse(texto) : null
  if (!res.ok) throw new Error(datos?.detail || datos?.message || 'Ocurrió un error')
  return datos
}

export const api = {
  get: (u) => request('GET', u),
  post: (u, b) => request('POST', u, b),
  patch: (u, b) => request('PATCH', u, b),
  del: (u) => request('DELETE', u),
  upload: (u, formData) => request('POST', u, formData, true),
  async descargar(id, nombre, version) {
    const res = await fetch(`/api/documentos/${id}/descargar${version ? `?version=${version}` : ''}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error('No se pudo descargar el archivo')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = nombre
    a.click()
    URL.revokeObjectURL(a.href)
  },
}

export const fechaCorta = (iso) =>
  iso ? new Date(iso.length <= 10 ? iso + 'T00:00:00' : iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
export const fechaHora = (iso) =>
  iso ? new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'
export const tamano = (b) => (b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`)
