"""Datos de demostración: equipo de Cimaverso (1 gerente + 4 desarrolladores), clientes, proyectos, tareas y documentos."""
from __future__ import annotations
import io
from datetime import date, timedelta
from sqlalchemy import select
import docx
from .db import SessionLocal
from .main import iniciar, _guardar_archivo
from .models import (Carpeta, Cliente, Documento, Proyecto, ProyectoMiembro, Rol, Tarea, Usuario,
                     VersionDocumento)
from .security import hash_password
from . import servicios as S

CLAVE_DEMO = "Cimaverso2026*"


def _docx(parrafos: list[str]) -> bytes:
    d = docx.Document()
    for p in parrafos:
        d.add_paragraph(p)
    b = io.BytesIO(); d.save(b); return b.getvalue()


def sembrar() -> None:
    iniciar()
    with SessionLocal() as db:
        if db.scalar(select(Usuario.id)) is not None:
            print("La base de datos ya tiene datos; no se siembra de nuevo.")
            return
        rol = {r.nombre: r.id for r in db.scalars(select(Rol))}
        gerente = Usuario(nombre="Gerente Cimaverso", correo="gerente@cimaverso.co", password_hash=hash_password(CLAVE_DEMO), rol_id=rol["gerente"])
        devs = [Usuario(nombre=n, correo=c, password_hash=hash_password(CLAVE_DEMO), rol_id=rol["desarrollador"])
                for n, c in [("Laura Gómez", "laura@cimaverso.co"), ("Andrés Pérez", "andres@cimaverso.co"),
                             ("Camila Rojas", "camila@cimaverso.co"), ("Daniel Ruiz", "daniel@cimaverso.co")]]
        db.add_all([gerente, *devs]); db.flush()
        c1 = Cliente(nombre="Agroindustrias del Norte", contacto="Marta Silva", correo="marta@agronorte.co", telefono="3101112233")
        c2 = Cliente(nombre="Clínica San Rafael", contacto="Jorge Díaz", correo="jdiaz@sanrafael.co", telefono="3204445566")
        c3 = Cliente(nombre="Tienda Aurora", contacto="Paula Mora", correo="paula@aurora.co", telefono="3157778899")
        db.add_all([c1, c2, c3]); db.flush()
        hoy = date.today()
        p1 = Proyecto(nombre="Asistente virtual de atención", descripcion="Asistente de inteligencia artificial para responder preguntas frecuentes de clientes.",
                      estado="en curso", fecha_inicio=hoy - timedelta(days=40), fecha_entrega=hoy + timedelta(days=20), cliente_id=c1.id)
        p2 = Proyecto(nombre="Sistema de citas médicas", descripcion="Aplicación web para agendar y confirmar citas.",
                      estado="en curso", fecha_inicio=hoy - timedelta(days=70), fecha_entrega=hoy - timedelta(days=5), cliente_id=c2.id)
        p3 = Proyecto(nombre="Sitio web e inventario", descripcion="Página web y control de inventario para tienda.",
                      estado="planeación", fecha_inicio=hoy + timedelta(days=5), fecha_entrega=hoy + timedelta(days=60), cliente_id=c3.id)
        db.add_all([p1, p2, p3]); db.flush()
        l, a, c, dn = devs
        for p, miembros in ((p1, [l, a]), (p2, [a, c]), (p3, [dn])):
            for m in miembros:
                db.add(ProyectoMiembro(proyecto_id=p.id, usuario_id=m.id))
        tareas = [
            (p1, "Definir preguntas frecuentes con el cliente", "completada", -20, l), (p1, "Entrenar el modelo de respuestas", "en curso", 5, a),
            (p1, "Integrar el asistente con el sitio web", "pendiente", 14, l), (p1, "Pruebas de aceptación", "pendiente", 18, a),
            (p2, "Diseñar el calendario de citas", "completada", -30, a), (p2, "Módulo de confirmación por correo", "en curso", -2, c),
            (p2, "Reporte mensual de citas", "pendiente", 2, c), (p2, "Manual de usuario", "pendiente", None, a),
            (p3, "Levantar requerimientos", "en curso", 10, dn), (p3, "Maquetar el sitio", "pendiente", 25, dn),
        ]
        for p, t, e, dias, r in tareas:
            db.add(Tarea(proyecto_id=p.id, titulo=t, estado=e, fecha_limite=hoy + timedelta(days=dias) if dias is not None else None, responsable_id=r.id))
        f1 = Carpeta(nombre="Contratos", proyecto_id=p1.id); f2 = Carpeta(nombre="Documentación técnica", proyecto_id=p1.id)
        db.add_all([f1, f2]); db.flush()
        db.add(Carpeta(nombre="Manuales", proyecto_id=p2.id, padre_id=None)); db.flush()
        muestras = [
            (p1, f1, "contrato_asistente.docx", l, _docx(["Contrato de prestación de servicios de desarrollo de un asistente virtual.",
                "El cliente Agroindustrias del Norte recibirá el asistente con garantía de tres meses y soporte en horario laboral.",
                "La entrega final se pacta a los noventa días de la firma del acta de inicio."])),
            (p1, f2, "arquitectura_asistente.md", a, "# Arquitectura\nEl asistente usa un modelo de lenguaje, una base de conocimiento y una API REST.\nSe despliega en contenedores Docker.".encode()),
            (p2, None, "requerimientos_citas.txt", c, "Requerimientos del sistema de citas médicas: agendar, cancelar, confirmar por correo y generar reportes mensuales de ocupación.".encode()),
            (p3, None, "propuesta_sitio_web.docx", dn, _docx(["Propuesta comercial para el sitio web y el inventario de Tienda Aurora.",
                "Incluye catálogo de productos, carrito de compras y control de existencias."])),
        ]
        for p, carp, nombre, autor, contenido in muestras:
            d = Documento(nombre=nombre, tipo=nombre.rsplit(".", 1)[1], proyecto_id=p.id, carpeta_id=carp.id if carp else None)
            db.add(d); db.flush()
            db.add(VersionDocumento(documento_id=d.id, numero=1, ruta=_guardar_archivo(contenido, p.id, nombre),
                                    texto=S.extraer_texto(nombre, contenido), tamano=len(contenido), autor_id=autor.id))
        # una segunda versión para mostrar el control de versiones
        d = db.scalar(select(Documento).where(Documento.nombre == "requerimientos_citas.txt"))
        nuevo = "Requerimientos del sistema de citas médicas (versión 2): agendar, cancelar, reprogramar, confirmar por correo y por mensaje de texto, y reportes mensuales.".encode()
        db.add(VersionDocumento(documento_id=d.id, numero=2, ruta=_guardar_archivo(nuevo, p2.id, d.nombre),
                                texto=S.extraer_texto(d.nombre, nuevo), tamano=len(nuevo), autor_id=c.id))
        S.registrar(db, gerente, "creó los datos de demostración", "sistema", None, "carga inicial")
        db.commit()
        print("Datos de demostración creados. Usuario gerente: gerente@cimaverso.co / " + CLAVE_DEMO)


if __name__ == "__main__":
    sembrar()
