"""API REST de la plataforma de gestión documental y de proyectos de Cimaverso (Litestar)."""
from __future__ import annotations
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Optional

from litestar import Litestar, Request, Router, delete, get, patch, post
from litestar.datastructures import UploadFile
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.exceptions import (ClientException, NotAuthorizedException, NotFoundException,
                                 PermissionDeniedException)
from litestar.params import Body
from litestar.response import File
from litestar.status_codes import HTTP_201_CREATED, HTTP_200_OK
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import config, servicios as S
from .db import Base, SessionLocal, engine
from .models import (ESTADOS_PROYECTO, ESTADOS_TAREA, Alerta, Carpeta, Cliente, Documento,
                     EventoActividad, Proyecto, ProyectoMiembro, Rol, Tarea, Usuario, VersionDocumento)
from .security import crear_token, hash_password, leer_token, verificar_password


# ------------------------------------------------------------------ dependencias
def get_db():
    with SessionLocal() as db:
        yield db


def get_usuario(request: Request, db: Session) -> Usuario:
    cabecera = request.headers.get("authorization", "")
    if not cabecera.lower().startswith("bearer "):
        raise NotAuthorizedException("Falta el token de acceso")
    uid = leer_token(cabecera[7:].strip())
    u = db.get(Usuario, uid) if uid else None
    if u is None or not u.activo:
        raise NotAuthorizedException("Sesión inválida o expirada")
    return u


DEPS = {"db": Provide(get_db), "u": Provide(get_usuario, sync_to_thread=False)}


# ------------------------------------------------------------------ serialización
def f(d) -> Optional[str]:
    return d.isoformat() if d else None


def s_usuario(u: Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "correo": u.correo, "rol": u.rol.nombre, "activo": u.activo}


def s_cliente(c: Cliente) -> dict:
    return {"id": c.id, "nombre": c.nombre, "contacto": c.contacto, "correo": c.correo, "telefono": c.telefono}


def s_tarea(t: Tarea) -> dict:
    return {"id": t.id, "titulo": t.titulo, "estado": t.estado, "fecha_limite": f(t.fecha_limite),
            "responsable_id": t.responsable_id, "responsable": t.responsable.nombre if t.responsable else None,
            "proyecto_id": t.proyecto_id}


def avance(db: Session, proyecto_id: int) -> dict:
    total = db.scalar(select(func.count(Tarea.id)).where(Tarea.proyecto_id == proyecto_id)) or 0
    hechas = db.scalar(select(func.count(Tarea.id)).where(Tarea.proyecto_id == proyecto_id, Tarea.estado == "completada")) or 0
    return {"tareas_total": total, "tareas_completadas": hechas, "porcentaje": round(100 * hechas / total) if total else 0}


def s_proyecto(db: Session, p: Proyecto, detalle: bool = False) -> dict:
    out = {"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion, "estado": p.estado,
           "fecha_inicio": f(p.fecha_inicio), "fecha_entrega": f(p.fecha_entrega), "cliente_id": p.cliente_id,
           "cliente": p.cliente.nombre if p.cliente else None, **avance(db, p.id)}
    if detalle:
        miembros = db.scalars(select(Usuario).join(ProyectoMiembro, ProyectoMiembro.usuario_id == Usuario.id)
                              .where(ProyectoMiembro.proyecto_id == p.id).order_by(Usuario.nombre))
        out["miembros"] = [s_usuario(m) for m in miembros]
        out["tareas"] = [s_tarea(t) for t in db.scalars(select(Tarea).where(Tarea.proyecto_id == p.id).order_by(Tarea.fecha_limite.is_(None), Tarea.fecha_limite, Tarea.id))]
        out["carpetas"] = [{"id": c.id, "nombre": c.nombre, "padre_id": c.padre_id}
                           for c in db.scalars(select(Carpeta).where(Carpeta.proyecto_id == p.id).order_by(Carpeta.nombre))]
        out["documentos"] = [s_documento(d) for d in db.scalars(select(Documento).where(Documento.proyecto_id == p.id, Documento.estado == "activo").order_by(Documento.nombre))]
    return out


def s_documento(d: Documento) -> dict:
    v = d.versiones[0] if d.versiones else None
    return {"id": d.id, "nombre": d.nombre, "tipo": d.tipo, "proyecto_id": d.proyecto_id, "carpeta_id": d.carpeta_id,
            "estado": d.estado, "version_actual": v.numero if v else 0, "autor": v.autor.nombre if v else None,
            "fecha": f(v.fecha) if v else None, "tamano": v.tamano if v else 0}


def s_version(v: VersionDocumento) -> dict:
    return {"id": v.id, "numero": v.numero, "autor": v.autor.nombre, "fecha": f(v.fecha), "tamano": v.tamano}


def fecha_o_none(valor: Optional[str], campo: str) -> Optional[date]:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ClientException(f"{campo}: use el formato AAAA-MM-DD")


# ------------------------------------------------------------------ entradas
@dataclass
class LoginIn:
    correo: str
    password: str


@dataclass
class UsuarioIn:
    nombre: str
    correo: str
    password: str
    rol: str = "desarrollador"


@dataclass
class UsuarioPatch:
    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = None


@dataclass
class ClienteIn:
    nombre: str
    contacto: str = ""
    correo: str = ""
    telefono: str = ""


@dataclass
class ClientePatch:
    nombre: Optional[str] = None
    contacto: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None


@dataclass
class ProyectoIn:
    nombre: str
    descripcion: str = ""
    estado: str = "planeación"
    fecha_inicio: Optional[str] = None
    fecha_entrega: Optional[str] = None
    cliente_id: Optional[int] = None


@dataclass
class ProyectoPatch:
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_entrega: Optional[str] = None
    cliente_id: Optional[int] = None


@dataclass
class MiembroIn:
    usuario_id: int


@dataclass
class TareaIn:
    titulo: str
    fecha_limite: Optional[str] = None
    responsable_id: Optional[int] = None
    estado: str = "pendiente"


@dataclass
class TareaPatch:
    titulo: Optional[str] = None
    estado: Optional[str] = None
    fecha_limite: Optional[str] = None
    responsable_id: Optional[int] = None


@dataclass
class CarpetaIn:
    nombre: str
    padre_id: Optional[int] = None


@dataclass
class SubidaIn:
    archivo: UploadFile
    proyecto_id: int
    carpeta_id: Optional[int] = None


@dataclass
class VersionIn:
    archivo: UploadFile


# ------------------------------------------------------------------ autenticación
@post("/auth/login", status_code=HTTP_200_OK, dependencies={"db": DEPS["db"]}, sync_to_thread=False)
def login(data: LoginIn, db: Session) -> dict:
    u = db.scalar(select(Usuario).where(func.lower(Usuario.correo) == data.correo.strip().lower()))
    if u is None or not u.activo or not verificar_password(data.password, u.password_hash):
        raise NotAuthorizedException("Correo o contraseña incorrectos")
    S.registrar(db, u, "inició sesión", "usuario", u.id)
    db.commit()
    return {"token": crear_token(u.id), "usuario": s_usuario(u)}


@post("/auth/logout", status_code=HTTP_200_OK, dependencies=DEPS, sync_to_thread=False)
def logout(db: Session, u: Usuario) -> dict:
    S.registrar(db, u, "cerró sesión", "usuario", u.id)
    db.commit()
    return {"ok": True}


@get("/auth/me", dependencies=DEPS, sync_to_thread=False)
def me(u: Usuario) -> dict:
    return s_usuario(u)


# ------------------------------------------------------------------ usuarios y roles
@get("/roles", dependencies=DEPS, sync_to_thread=False)
def roles(db: Session, u: Usuario) -> list[str]:
    return list(db.scalars(select(Rol.nombre).order_by(Rol.nombre)))


@get("/usuarios", dependencies=DEPS, sync_to_thread=False)
def listar_usuarios(db: Session, u: Usuario) -> list[dict]:
    # Todos pueden ver el equipo (para asignar responsables); solo el gerente lo administra.
    return [s_usuario(x) for x in db.scalars(select(Usuario).order_by(Usuario.nombre))]


def _rol(db: Session, nombre: str) -> Rol:
    r = db.scalar(select(Rol).where(Rol.nombre == nombre))
    if r is None:
        raise ClientException("Rol inválido: use «gerente» o «desarrollador»")
    return r


@post("/usuarios", status_code=HTTP_201_CREATED, dependencies=DEPS, sync_to_thread=False)
def crear_usuario(data: UsuarioIn, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    correo = data.correo.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", correo):
        raise ClientException("Correo inválido")
    if len(data.password) < 8:
        raise ClientException("La contraseña debe tener al menos 8 caracteres")
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.correo) == correo)):
        raise ClientException("Ya existe un usuario con ese correo")
    nuevo = Usuario(nombre=data.nombre.strip(), correo=correo, password_hash=hash_password(data.password), rol_id=_rol(db, data.rol).id)
    db.add(nuevo); db.flush()
    S.registrar(db, u, "creó el usuario", "usuario", nuevo.id, nuevo.nombre)
    db.commit(); db.refresh(nuevo)
    return s_usuario(nuevo)


@patch("/usuarios/{uid:int}", dependencies=DEPS, sync_to_thread=False)
def editar_usuario(uid: int, data: UsuarioPatch, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    x = db.get(Usuario, uid)
    if x is None:
        raise NotFoundException("Usuario no encontrado")
    if data.nombre: x.nombre = data.nombre.strip()
    if data.rol:
        if x.id == u.id and data.rol != "gerente":
            raise ClientException("No puedes quitarte a ti mismo el rol de gerente")
        x.rol_id = _rol(db, data.rol).id
    if data.activo is not None:
        if x.id == u.id and not data.activo:
            raise ClientException("No puedes desactivar tu propia cuenta")
        x.activo = data.activo
    if data.password:
        if len(data.password) < 8:
            raise ClientException("La contraseña debe tener al menos 8 caracteres")
        x.password_hash = hash_password(data.password)
    S.registrar(db, u, "editó el usuario", "usuario", x.id, x.nombre)
    db.commit(); db.refresh(x)
    return s_usuario(x)


@get("/permisos", dependencies=DEPS, sync_to_thread=False)
def matriz_permisos(u: Usuario) -> list[dict]:
    return [
        {"funcionalidad": "Administrar usuarios y roles", "gerente": "Sí", "desarrollador": "No"},
        {"funcionalidad": "Gestionar clientes", "gerente": "Sí", "desarrollador": "Solo consulta"},
        {"funcionalidad": "Crear y editar proyectos", "gerente": "Sí", "desarrollador": "Solo los asignados (edita tareas)"},
        {"funcionalidad": "Gestionar tareas", "gerente": "Todas", "desarrollador": "Las de sus proyectos"},
        {"funcionalidad": "Cargar y versionar documentos", "gerente": "Todos", "desarrollador": "Solo en sus proyectos"},
        {"funcionalidad": "Buscar documentos", "gerente": "En todo el sistema", "desarrollador": "Solo en sus proyectos"},
        {"funcionalidad": "Consultar el dashboard", "gerente": "Global", "desarrollador": "De sus proyectos"},
        {"funcionalidad": "Consultar el historial de actividad", "gerente": "Completo", "desarrollador": "De sus proyectos"},
    ]


# ------------------------------------------------------------------ clientes
@get("/clientes", dependencies=DEPS, sync_to_thread=False)
def listar_clientes(db: Session, u: Usuario) -> list[dict]:
    return [s_cliente(c) for c in db.scalars(select(Cliente).order_by(Cliente.nombre))]


@post("/clientes", status_code=HTTP_201_CREATED, dependencies=DEPS, sync_to_thread=False)
def crear_cliente(data: ClienteIn, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    if not data.nombre.strip():
        raise ClientException("El nombre es obligatorio")
    c = Cliente(nombre=data.nombre.strip(), contacto=data.contacto, correo=data.correo, telefono=data.telefono)
    db.add(c); db.flush()
    S.registrar(db, u, "creó el cliente", "cliente", c.id, c.nombre)
    db.commit()
    return s_cliente(c)


@patch("/clientes/{cid:int}", dependencies=DEPS, sync_to_thread=False)
def editar_cliente(cid: int, data: ClientePatch, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    c = db.get(Cliente, cid)
    if c is None:
        raise NotFoundException("Cliente no encontrado")
    for k in ("nombre", "contacto", "correo", "telefono"):
        v = getattr(data, k)
        if v is not None:
            setattr(c, k, v)
    S.registrar(db, u, "editó el cliente", "cliente", c.id, c.nombre)
    db.commit()
    return s_cliente(c)


# ------------------------------------------------------------------ proyectos
@get("/proyectos", dependencies=DEPS, sync_to_thread=False)
def listar_proyectos(db: Session, u: Usuario) -> list[dict]:
    q = select(Proyecto).order_by(Proyecto.id.desc())
    vis = S.ids_proyectos_visibles(db, u)
    if vis is not None:
        q = q.where(Proyecto.id.in_(vis or [0]))
    return [s_proyecto(db, p) for p in db.scalars(q)]


def _validar_proyecto(estado, cliente_id, db):
    if estado is not None and estado not in ESTADOS_PROYECTO:
        raise ClientException(f"Estado inválido. Use: {', '.join(ESTADOS_PROYECTO)}")
    if cliente_id is not None and db.get(Cliente, cliente_id) is None:
        raise ClientException("El cliente no existe")


@post("/proyectos", status_code=HTTP_201_CREATED, dependencies=DEPS, sync_to_thread=False)
def crear_proyecto(data: ProyectoIn, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    if not data.nombre.strip():
        raise ClientException("El nombre es obligatorio")
    _validar_proyecto(data.estado, data.cliente_id, db)
    ini, fin = fecha_o_none(data.fecha_inicio, "fecha_inicio"), fecha_o_none(data.fecha_entrega, "fecha_entrega")
    if ini and fin and fin < ini:
        raise ClientException("La fecha de entrega no puede ser anterior a la de inicio")
    p = Proyecto(nombre=data.nombre.strip(), descripcion=data.descripcion, estado=data.estado,
                 fecha_inicio=ini, fecha_entrega=fin, cliente_id=data.cliente_id)
    db.add(p); db.flush()
    S.registrar(db, u, "creó el proyecto", "proyecto", p.id, p.nombre, p.id)
    db.commit(); db.refresh(p)
    return s_proyecto(db, p, True)


@get("/proyectos/{pid:int}", dependencies=DEPS, sync_to_thread=False)
def ver_proyecto(pid: int, db: Session, u: Usuario) -> dict:
    return s_proyecto(db, S.exigir_proyecto(db, u, pid), True)


@patch("/proyectos/{pid:int}", dependencies=DEPS, sync_to_thread=False)
def editar_proyecto(pid: int, data: ProyectoPatch, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    p = S.exigir_proyecto(db, u, pid)
    _validar_proyecto(data.estado, data.cliente_id, db)
    if data.nombre: p.nombre = data.nombre.strip()
    if data.descripcion is not None: p.descripcion = data.descripcion
    if data.estado: p.estado = data.estado
    if data.fecha_inicio is not None: p.fecha_inicio = fecha_o_none(data.fecha_inicio, "fecha_inicio")
    if data.fecha_entrega is not None: p.fecha_entrega = fecha_o_none(data.fecha_entrega, "fecha_entrega")
    if data.cliente_id is not None: p.cliente_id = data.cliente_id
    S.registrar(db, u, "editó el proyecto", "proyecto", p.id, p.nombre, p.id, notificar=True)
    db.commit(); db.refresh(p)
    return s_proyecto(db, p, True)


@post("/proyectos/{pid:int}/miembros", status_code=HTTP_201_CREATED, dependencies=DEPS, sync_to_thread=False)
def agregar_miembro(pid: int, data: MiembroIn, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    p = S.exigir_proyecto(db, u, pid)
    miembro = db.get(Usuario, data.usuario_id)
    if miembro is None:
        raise NotFoundException("Usuario no encontrado")
    if db.get(ProyectoMiembro, (pid, data.usuario_id)) is None:
        db.add(ProyectoMiembro(proyecto_id=pid, usuario_id=data.usuario_id))
        S.registrar(db, u, "asignó a", "proyecto", pid, f"{miembro.nombre} → {p.nombre}", pid)
        S.crear_alerta(db, miembro.id, "cambio", f"Te asignaron al proyecto «{p.nombre}»", f"asig:{pid}:{uuid.uuid4().hex}")
        db.commit()
    return s_proyecto(db, p, True)


@delete("/proyectos/{pid:int}/miembros/{uid:int}", status_code=HTTP_200_OK, dependencies=DEPS, sync_to_thread=False)
def quitar_miembro(pid: int, uid: int, db: Session, u: Usuario) -> dict:
    S.exigir_gerente(u)
    p = S.exigir_proyecto(db, u, pid)
    m = db.get(ProyectoMiembro, (pid, uid))
    if m:
        db.delete(m)
        S.registrar(db, u, "retiró a un miembro de", "proyecto", pid, p.nombre, pid)
        db.commit()
    return s_proyecto(db, p, True)


# ------------------------------------------------------------------ tareas y carpetas
def _validar_tarea(estado, responsable_id, p, db):
    if estado is not None and estado not in ESTADOS_TAREA:
        raise ClientException(f"Estado inválido. Use: {', '.join(ESTADOS_TAREA)}")
    if responsable_id is not None:
        if db.get(Usuario, responsable_id) is None:
            raise ClientException("El responsable no existe")


@get("/proyectos/{pid:int}/tareas", dependencies=DEPS, sync_to_thread=False)
def listar_tareas(pid: int, db: Session, u: Usuario) -> list[dict]:
    S.exigir_proyecto(db, u, pid)
    return [s_tarea(t) for t in db.scalars(select(Tarea).where(Tarea.proyecto_id == pid).order_by(Tarea.id))]


@post("/proyectos/{pid:int}/tareas", status_code=HTTP_201_CREATED, dependencies=DEPS, sync_to_thread=False)
def crear_tarea(pid: int, data: TareaIn, db: Session, u: Usuario) -> dict:
    p = S.exigir_proyecto(db, u, pid)
    if not data.titulo.strip():
        raise ClientException("El título es obligatorio")
    _validar_tarea(data.estado, data.responsable_id, p, db)
    t = Tarea(titulo=data.titulo.strip(), estado=data.estado, fecha_limite=fecha_o_none(data.fecha_limite, "fecha_limite"),
              responsable_id=data.responsable_id, proyecto_id=pid)
    db.add(t); db.flush()
    S.registrar(db, u, "creó la tarea", "tarea", t.id, f"{t.titulo} ({p.nombre})", pid, notificar=True)
    db.commit(); db.refresh(t)
    return s_tarea(t)


@patch("/tareas/{tid:int}", dependencies=DEPS, sync_to_thread=False)
def editar_tarea(tid: int, data: TareaPatch, db: Session, u: Usuario) -> dict:
    t = db.get(Tarea, tid)
    if t is None:
        raise NotFoundException("Tarea no encontrada")
    p = S.exigir_proyecto(db, u, t.proyecto_id)
    _validar_tarea(data.estado, data.responsable_id, p, db)
    if data.titulo: t.titulo = data.titulo.strip()
    if data.estado: t.estado = data.estado
    if data.fecha_limite is not None: t.fecha_limite = fecha_o_none(data.fecha_limite, "fecha_limite")
    if data.responsable_id is not None: t.responsable_id = data.responsable_id
    S.registrar(db, u, "actualizó la tarea", "tarea", t.id, f"{t.titulo} → {t.estado} ({p.nombre})", p.id, notificar=True)
    db.commit(); db.refresh(t)
    return s_tarea(t)


@post("/proyectos/{pid:int}/carpetas", status_code=HTTP_201_CREATED, dependencies=DEPS, sync_to_thread=False)
def crear_carpeta(pid: int, data: CarpetaIn, db: Session, u: Usuario) -> dict:
    p = S.exigir_proyecto(db, u, pid)
    if not data.nombre.strip():
        raise ClientException("El nombre es obligatorio")
    if data.padre_id:
        padre = db.get(Carpeta, data.padre_id)
        if padre is None or padre.proyecto_id != pid:
            raise ClientException("La carpeta padre no pertenece al proyecto")
    c = Carpeta(nombre=data.nombre.strip(), proyecto_id=pid, padre_id=data.padre_id)
    db.add(c); db.flush()
    S.registrar(db, u, "creó la carpeta", "carpeta", c.id, f"{c.nombre} ({p.nombre})", pid)
    db.commit()
    return {"id": c.id, "nombre": c.nombre, "padre_id": c.padre_id}


# ------------------------------------------------------------------ documentos
def _guardar_archivo(contenido: bytes, proyecto_id: int, nombre: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9._-]", "_", nombre)[:80] or "archivo"
    rel = Path(str(proyecto_id)) / f"{uuid.uuid4().hex}_{seguro}"
    destino = config.STORAGE_DIR / rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return str(rel)


async def _contenido(archivo: UploadFile) -> bytes:
    datos = await archivo.read()
    if len(datos) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ClientException(f"El archivo supera el máximo de {config.MAX_UPLOAD_MB} MB")
    if not datos:
        raise ClientException("El archivo está vacío")
    return datos


def _doc_visible(db: Session, u: Usuario, did: int) -> Documento:
    d = db.get(Documento, did)
    if d is None:
        raise NotFoundException("Documento no encontrado")
    S.exigir_proyecto(db, u, d.proyecto_id)
    return d


@get("/documentos", dependencies=DEPS, sync_to_thread=False)
def listar_documentos(db: Session, u: Usuario, proyecto: Optional[int] = None, papelera: bool = False) -> list[dict]:
    q = select(Documento).where(Documento.estado == ("papelera" if papelera else "activo")).order_by(Documento.nombre)
    vis = S.ids_proyectos_visibles(db, u)
    if vis is not None:
        q = q.where(Documento.proyecto_id.in_(vis or [0]))
    if proyecto:
        q = q.where(Documento.proyecto_id == proyecto)
    return [s_documento(d) for d in db.scalars(q)]


@post("/documentos", status_code=HTTP_201_CREATED, dependencies=DEPS)
async def subir_documento(data: Annotated[SubidaIn, Body(media_type=RequestEncodingType.MULTI_PART)], db: Session, u: Usuario) -> dict:
    p = S.exigir_proyecto(db, u, data.proyecto_id)
    if data.carpeta_id:
        c = db.get(Carpeta, data.carpeta_id)
        if c is None or c.proyecto_id != p.id:
            raise ClientException("La carpeta no pertenece al proyecto")
    contenido = await _contenido(data.archivo)
    nombre = (data.archivo.filename or "archivo").strip()
    ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    doc = Documento(nombre=nombre, tipo=ext, proyecto_id=p.id, carpeta_id=data.carpeta_id)
    db.add(doc); db.flush()
    db.add(VersionDocumento(documento_id=doc.id, numero=1, ruta=_guardar_archivo(contenido, p.id, nombre),
                            texto=S.extraer_texto(nombre, contenido).replace("\x00", ""), tamano=len(contenido), autor_id=u.id))
    S.registrar(db, u, "cargó el documento", "documento", doc.id, f"{nombre} v1 ({p.nombre})", p.id, notificar=True)
    db.commit(); db.refresh(doc)
    return s_documento(doc)


@post("/documentos/{did:int}/versiones", status_code=HTTP_201_CREATED, dependencies=DEPS)
async def nueva_version(did: int, data: Annotated[VersionIn, Body(media_type=RequestEncodingType.MULTI_PART)], db: Session, u: Usuario) -> dict:
    doc = _doc_visible(db, u, did)
    if doc.estado != "activo":
        raise ClientException("El documento está en la papelera; restáuralo primero")
    contenido = await _contenido(data.archivo)
    nombre = (data.archivo.filename or doc.nombre).strip()
    n = (doc.versiones[0].numero if doc.versiones else 0) + 1
    db.add(VersionDocumento(documento_id=doc.id, numero=n, ruta=_guardar_archivo(contenido, doc.proyecto_id, nombre),
                            texto=S.extraer_texto(nombre, contenido).replace("\x00", ""), tamano=len(contenido), autor_id=u.id))
    S.registrar(db, u, "cargó una nueva versión de", "documento", doc.id, f"{doc.nombre} v{n}", doc.proyecto_id, notificar=True)
    db.commit(); db.refresh(doc)
    return s_documento(doc)


@get("/documentos/{did:int}/versiones", dependencies=DEPS, sync_to_thread=False)
def versiones(did: int, db: Session, u: Usuario) -> list[dict]:
    return [s_version(v) for v in _doc_visible(db, u, did).versiones]


@get("/documentos/{did:int}/descargar", dependencies=DEPS, sync_to_thread=False)
def descargar(did: int, db: Session, u: Usuario, version: Optional[int] = None) -> File:
    doc = _doc_visible(db, u, did)
    v = next((x for x in doc.versiones if x.numero == version), None) if version else (doc.versiones[0] if doc.versiones else None)
    if v is None:
        raise NotFoundException("Versión no encontrada")
    ruta = (config.STORAGE_DIR / v.ruta).resolve()
    if config.STORAGE_DIR not in ruta.parents or not ruta.exists():
        raise NotFoundException("El archivo no está disponible")
    S.registrar(db, u, "descargó el documento", "documento", doc.id, f"{doc.nombre} v{v.numero}", doc.proyecto_id)
    db.commit()
    return File(path=ruta, filename=doc.nombre, content_disposition_type="attachment")


@delete("/documentos/{did:int}", status_code=HTTP_200_OK, dependencies=DEPS, sync_to_thread=False)
def a_papelera(did: int, db: Session, u: Usuario) -> dict:
    doc = _doc_visible(db, u, did)
    doc.estado = "papelera"
    S.registrar(db, u, "envió a la papelera", "documento", doc.id, doc.nombre, doc.proyecto_id, notificar=True)
    db.commit()
    return s_documento(doc)


@post("/documentos/{did:int}/restaurar", status_code=HTTP_200_OK, dependencies=DEPS, sync_to_thread=False)
def restaurar(did: int, db: Session, u: Usuario) -> dict:
    doc = _doc_visible(db, u, did)
    doc.estado = "activo"
    S.registrar(db, u, "restauró el documento", "documento", doc.id, doc.nombre, doc.proyecto_id, notificar=True)
    db.commit()
    return s_documento(doc)


# ------------------------------------------------------------------ búsqueda, dashboard, alertas, actividad
@get("/busqueda", dependencies=DEPS, sync_to_thread=False)
def busqueda(db: Session, u: Usuario, q: Optional[str] = None, proyecto: Optional[int] = None, tipo: Optional[str] = None,
             desde: Optional[str] = None, hasta: Optional[str] = None, responsable: Optional[int] = None) -> list[dict]:
    if proyecto:
        S.exigir_proyecto(db, u, proyecto)
    return S.buscar(db, u, q, proyecto, tipo, fecha_o_none(desde, "desde"), fecha_o_none(hasta, "hasta"), responsable)


@get("/dashboard", dependencies=DEPS, sync_to_thread=False)
def dashboard(db: Session, u: Usuario) -> dict:
    S.generar_alertas(db, u)
    q = select(Proyecto).where(Proyecto.estado != "finalizado").order_by(Proyecto.fecha_entrega.is_(None), Proyecto.fecha_entrega)
    vis = S.ids_proyectos_visibles(db, u)
    if vis is not None:
        q = q.where(Proyecto.id.in_(vis or [0]))
    activos = [s_proyecto(db, p) for p in db.scalars(q)]
    ids = [p["id"] for p in activos] or [0]
    hoy = date.today()
    total = db.scalar(select(func.count(Tarea.id)).where(Tarea.proyecto_id.in_(ids))) or 0
    hechas = db.scalar(select(func.count(Tarea.id)).where(Tarea.proyecto_id.in_(ids), Tarea.estado == "completada")) or 0
    vencidas = db.scalar(select(func.count(Tarea.id)).where(Tarea.proyecto_id.in_(ids), Tarea.estado != "completada",
                                                           Tarea.fecha_limite < hoy)) or 0
    docs = db.scalar(select(func.count(Documento.id)).where(Documento.proyecto_id.in_(ids), Documento.estado == "activo")) or 0
    no_leidas = db.scalar(select(func.count(Alerta.id)).where(Alerta.usuario_id == u.id, Alerta.leida.is_(False))) or 0
    carga = []
    if u.es_gerente:
        for x in db.scalars(select(Usuario).where(Usuario.activo.is_(True)).order_by(Usuario.nombre)):
            carga.append({"usuario": x.nombre, "pendientes": db.scalar(select(func.count(Tarea.id)).where(
                Tarea.responsable_id == x.id, Tarea.estado != "completada")) or 0})
    alertas = db.scalars(select(Alerta).where(Alerta.usuario_id == u.id, Alerta.leida.is_(False)).order_by(Alerta.fecha.desc(), Alerta.id.desc()).limit(6))
    return {"proyectos_activos": len(activos), "proyectos": activos, "tareas_total": total, "tareas_completadas": hechas,
            "porcentaje_global": round(100 * hechas / total) if total else 0, "tareas_vencidas": vencidas,
            "documentos": docs, "alertas_no_leidas": no_leidas, "carga_trabajo": carga,
            "alertas": [{"id": a.id, "tipo": a.tipo, "mensaje": a.mensaje, "fecha": f(a.fecha)} for a in alertas]}


@get("/alertas", dependencies=DEPS, sync_to_thread=False)
def listar_alertas(db: Session, u: Usuario) -> list[dict]:
    S.generar_alertas(db, u)
    q = select(Alerta).where(Alerta.usuario_id == u.id).order_by(Alerta.leida, Alerta.fecha.desc(), Alerta.id.desc()).limit(100)
    return [{"id": a.id, "tipo": a.tipo, "mensaje": a.mensaje, "leida": a.leida, "fecha": f(a.fecha)} for a in db.scalars(q)]


@patch("/alertas/{aid:int}", dependencies=DEPS, sync_to_thread=False)
def marcar_alerta(aid: int, db: Session, u: Usuario) -> dict:
    a = db.get(Alerta, aid)
    if a is None or a.usuario_id != u.id:
        raise NotFoundException("Alerta no encontrada")
    a.leida = True
    db.commit()
    return {"id": a.id, "leida": True}


@get("/actividad", dependencies=DEPS, sync_to_thread=False)
def actividad(db: Session, u: Usuario, proyecto: Optional[int] = None, limite: int = 100) -> list[dict]:
    q = select(EventoActividad).order_by(EventoActividad.fecha.desc(), EventoActividad.id.desc()).limit(min(limite, 500))
    vis = S.ids_proyectos_visibles(db, u)
    if proyecto:
        S.exigir_proyecto(db, u, proyecto)
        q = q.where(EventoActividad.proyecto_id == proyecto)
    elif vis is not None:
        q = q.where(EventoActividad.proyecto_id.in_(vis or [0]))
    return [{"id": e.id, "usuario": e.usuario.nombre if e.usuario else "Sistema", "accion": e.accion, "entidad": e.entidad,
             "detalle": e.detalle, "proyecto_id": e.proyecto_id, "fecha": f(e.fecha)} for e in db.scalars(q)]


@get("/salud", sync_to_thread=False)
def salud() -> dict:
    return {"estado": "ok"}


api = Router(path="/api", route_handlers=[
    login, logout, me, roles, listar_usuarios, crear_usuario, editar_usuario, matriz_permisos,
    listar_clientes, crear_cliente, editar_cliente,
    listar_proyectos, crear_proyecto, ver_proyecto, editar_proyecto, agregar_miembro, quitar_miembro,
    listar_tareas, crear_tarea, editar_tarea, crear_carpeta,
    listar_documentos, subir_documento, nueva_version, versiones, descargar, a_papelera, restaurar,
    busqueda, dashboard, listar_alertas, marcar_alerta, actividad, salud])


def iniciar() -> None:
    Base.metadata.create_all(engine)
    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        for nombre in ("gerente", "desarrollador"):
            if db.scalar(select(Rol).where(Rol.nombre == nombre)) is None:
                db.add(Rol(nombre=nombre))
        db.commit()


app = Litestar(route_handlers=[api], on_startup=[lambda app: iniciar()], debug=False)
