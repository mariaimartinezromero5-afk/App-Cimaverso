"""Lógica de negocio: permisos, trazabilidad, alertas, extracción de texto y búsqueda."""
from __future__ import annotations
import io
import uuid
from datetime import date, timedelta
from litestar.exceptions import NotFoundException, PermissionDeniedException
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session, aliased
from . import config
from .db import es_postgres
from .models import (Alerta, Documento, EventoActividad, Proyecto, ProyectoMiembro, Tarea,
                     Usuario, VersionDocumento)


# ------------------------------------------------------------------ permisos
def ids_proyectos_visibles(db: Session, u: Usuario) -> list[int] | None:
    """None = todos (gerente). Lista = solo los proyectos asignados (desarrollador)."""
    if u.es_gerente:
        return None
    return list(db.scalars(select(ProyectoMiembro.proyecto_id).where(ProyectoMiembro.usuario_id == u.id)))


def exigir_proyecto(db: Session, u: Usuario, proyecto_id: int) -> Proyecto:
    p = db.get(Proyecto, proyecto_id)
    if p is None:
        raise NotFoundException("Proyecto no encontrado")
    visibles = ids_proyectos_visibles(db, u)
    if visibles is not None and proyecto_id not in visibles:
        raise PermissionDeniedException("No tienes acceso a este proyecto")
    return p


def exigir_gerente(u: Usuario) -> None:
    if not u.es_gerente:
        raise PermissionDeniedException("Solo el gerente puede realizar esta acción")


# ------------------------------------------------------------------ trazabilidad y alertas
def registrar(db: Session, u: Usuario | None, accion: str, entidad: str, entidad_id: int | None = None,
              detalle: str = "", proyecto_id: int | None = None, notificar: bool = False) -> None:
    db.add(EventoActividad(usuario_id=u.id if u else None, accion=accion, entidad=entidad,
                           entidad_id=entidad_id, detalle=detalle[:400], proyecto_id=proyecto_id))
    if notificar and proyecto_id:
        destinatarios = set(db.scalars(select(ProyectoMiembro.usuario_id).where(ProyectoMiembro.proyecto_id == proyecto_id)))
        destinatarios |= set(db.scalars(select(Usuario.id).join(Usuario.rol).where(Usuario.activo.is_(True), Usuario.rol.has(nombre="gerente"))))
        if u:
            destinatarios.discard(u.id)
        for dest in destinatarios:
            crear_alerta(db, dest, "cambio", f"{u.nombre if u else 'Sistema'}: {accion} — {detalle}"[:400],
                         f"cambio:{uuid.uuid4().hex}")


def crear_alerta(db: Session, usuario_id: int, tipo: str, mensaje: str, clave: str) -> None:
    """Inserta la alerta si no existe ya una con la misma clave para el usuario."""
    existe = db.scalar(select(Alerta.id).where(Alerta.usuario_id == usuario_id, Alerta.clave == clave))
    if existe is None:
        db.add(Alerta(usuario_id=usuario_id, tipo=tipo, mensaje=mensaje, clave=clave))
        db.flush()


def generar_alertas(db: Session, u: Usuario, hoy: date | None = None) -> None:
    """Calcula las alertas automáticas de tareas por vencer y proyectos retrasados o en riesgo."""
    hoy = hoy or date.today()
    limite = hoy + timedelta(days=config.DIAS_ALERTA_VENCIMIENTO)
    visibles = ids_proyectos_visibles(db, u)
    q = select(Tarea, Proyecto).join(Proyecto, Proyecto.id == Tarea.proyecto_id).where(
        Tarea.estado != "completada", Tarea.fecha_limite.is_not(None), Tarea.fecha_limite <= limite)
    if visibles is not None:
        q = q.where(Tarea.proyecto_id.in_(visibles or [0]))
    vencidas_por_proyecto: dict[int, int] = {}
    for t, p in db.execute(q):
        if t.fecha_limite < hoy:
            vencidas_por_proyecto[p.id] = vencidas_por_proyecto.get(p.id, 0) + 1
            msg = f"Tarea vencida: «{t.titulo}» ({p.nombre}), debía entregarse el {t.fecha_limite.isoformat()}"
        else:
            msg = f"Tarea por vencer: «{t.titulo}» ({p.nombre}), vence el {t.fecha_limite.isoformat()}"
        crear_alerta(db, u.id, "tarea_por_vencer", msg, f"tarea:{t.id}:{t.fecha_limite.isoformat()}")
    qp = select(Proyecto).where(Proyecto.estado != "finalizado")
    if visibles is not None:
        qp = qp.where(Proyecto.id.in_(visibles or [0]))
    for p in db.scalars(qp):
        if p.fecha_entrega and p.fecha_entrega < hoy:
            crear_alerta(db, u.id, "proyecto_retrasado",
                         f"Proyecto retrasado: «{p.nombre}» superó su fecha de entrega ({p.fecha_entrega.isoformat()})",
                         f"retraso:{p.id}:{p.fecha_entrega.isoformat()}")
        elif vencidas_por_proyecto.get(p.id):
            crear_alerta(db, u.id, "proyecto_retrasado",
                         f"Proyecto en riesgo: «{p.nombre}» tiene {vencidas_por_proyecto[p.id]} tarea(s) vencida(s)",
                         f"riesgo:{p.id}:{vencidas_por_proyecto[p.id]}")
    db.commit()


# ------------------------------------------------------------------ extracción de texto
def extraer_texto(nombre: str, contenido: bytes) -> str:
    ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    try:
        if ext in ("txt", "md", "csv", "json", "html", "xml", "log", "py", "js", "sql"):
            return contenido.decode("utf-8", errors="ignore")
        if ext == "pdf":
            from pypdf import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(contenido)).pages)
        if ext == "docx":
            import docx
            documento = docx.Document(io.BytesIO(contenido))
            partes = [p.text for p in documento.paragraphs]
            for tabla in documento.tables:
                for fila in tabla.rows:
                    partes.extend(c.text for c in fila.cells)
            return "\n".join(partes)
    except Exception:
        return ""
    return ""


# ------------------------------------------------------------------ búsqueda
def buscar(db: Session, u: Usuario, q: str | None, proyecto: int | None, tipo: str | None,
           desde: date | None, hasta: date | None, responsable: int | None) -> list[dict]:
    visibles = ids_proyectos_visibles(db, u)
    vmax = aliased(VersionDocumento)
    ultima = select(func.max(vmax.numero)).where(vmax.documento_id == Documento.id).correlate(Documento).scalar_subquery()
    stmt = (select(Documento, VersionDocumento, Proyecto)
            .join(VersionDocumento, VersionDocumento.documento_id == Documento.id)
            .join(Proyecto, Proyecto.id == Documento.proyecto_id)
            .where(Documento.estado == "activo",
                   VersionDocumento.numero == ultima))
    if visibles is not None:
        stmt = stmt.where(Documento.proyecto_id.in_(visibles or [0]))
    if proyecto:
        stmt = stmt.where(Documento.proyecto_id == proyecto)
    if tipo:
        stmt = stmt.where(Documento.tipo == tipo.lower().lstrip("."))
    if desde:
        stmt = stmt.where(func.date(VersionDocumento.fecha) >= desde)
    if hasta:
        stmt = stmt.where(func.date(VersionDocumento.fecha) <= hasta)
    if responsable:
        stmt = stmt.where(VersionDocumento.autor_id == responsable)
    if q:
        q = q.strip()
        patron = f"%{q}%"
        if es_postgres():
            tsq = func.websearch_to_tsquery("spanish", q)
            tsv = func.to_tsvector("spanish", func.coalesce(VersionDocumento.texto, ""))
            stmt = stmt.where(or_(tsv.op("@@")(tsq), Documento.nombre.ilike(patron), VersionDocumento.texto.ilike(patron)))
        else:
            stmt = stmt.where(or_(Documento.nombre.ilike(patron), VersionDocumento.texto.ilike(patron)))
    resultados = []
    for doc, ver, proy in db.execute(stmt.order_by(VersionDocumento.fecha.desc()).limit(100)):
        fragmento = ""
        if q and ver.texto:
            pos = ver.texto.lower().find(q.lower())
            if pos < 0:
                primera = q.split()[0].lower() if q.split() else ""
                pos = ver.texto.lower().find(primera) if primera else -1
            if pos >= 0:
                ini = max(0, pos - 60)
                fragmento = ("…" if ini else "") + ver.texto[ini:pos + 140].replace("\n", " ") + "…"
        resultados.append({"id": doc.id, "nombre": doc.nombre, "tipo": doc.tipo, "proyecto_id": proy.id,
                           "proyecto": proy.nombre, "version": ver.numero, "autor": ver.autor.nombre,
                           "autor_id": ver.autor_id, "fecha": ver.fecha.isoformat(), "fragmento": fragmento})
    return resultados
