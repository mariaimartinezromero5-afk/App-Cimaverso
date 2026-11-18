"""Modelo de datos (Tabla de entidades del diseño de la solución)."""
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

ESTADOS_PROYECTO = ("planeación", "en curso", "en pausa", "finalizado")
ESTADOS_TAREA = ("pendiente", "en curso", "completada")


class Rol(Base):
    __tablename__ = "rol"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)


class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.id"))
    rol: Mapped[Rol] = relationship(lazy="joined")

    @property
    def es_gerente(self) -> bool:
        return self.rol.nombre == "gerente"


class Cliente(Base):
    __tablename__ = "cliente"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    contacto: Mapped[str] = mapped_column(String(160), default="")
    correo: Mapped[str] = mapped_column(String(160), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")


class Proyecto(Base):
    __tablename__ = "proyecto"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    estado: Mapped[str] = mapped_column(String(20), default="planeación")
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("cliente.id"), nullable=True)
    cliente: Mapped[Cliente | None] = relationship(lazy="joined")


class ProyectoMiembro(Base):
    __tablename__ = "proyecto_miembro"
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)


class Tarea(Base):
    __tablename__ = "tarea"
    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"), index=True)
    responsable: Mapped[Usuario | None] = relationship(lazy="joined")


class Carpeta(Base):
    __tablename__ = "carpeta"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"), index=True)
    padre_id: Mapped[int | None] = mapped_column(ForeignKey("carpeta.id"), nullable=True)


class Documento(Base):
    __tablename__ = "documento"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(20), default="")
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"), index=True)
    carpeta_id: Mapped[int | None] = mapped_column(ForeignKey("carpeta.id"), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="activo")  # activo | papelera
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    versiones: Mapped[list["VersionDocumento"]] = relationship(
        back_populates="documento", order_by="VersionDocumento.numero.desc()", lazy="selectin")


class VersionDocumento(Base):
    __tablename__ = "version_documento"
    __table_args__ = (UniqueConstraint("documento_id", "numero"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documento.id", ondelete="CASCADE"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    ruta: Mapped[str] = mapped_column(String(400))
    texto: Mapped[str] = mapped_column(Text, default="")
    tamano: Mapped[int] = mapped_column(Integer, default=0)
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    documento: Mapped[Documento] = relationship(back_populates="versiones")
    autor: Mapped[Usuario] = relationship(lazy="joined")


class EventoActividad(Base):
    __tablename__ = "evento_actividad"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(60))
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detalle: Mapped[str] = mapped_column(String(400), default="")
    proyecto_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    usuario: Mapped[Usuario | None] = relationship(lazy="joined")


class Alerta(Base):
    __tablename__ = "alerta"
    __table_args__ = (UniqueConstraint("usuario_id", "clave"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))  # tarea_por_vencer | proyecto_retrasado | cambio
    mensaje: Mapped[str] = mapped_column(String(400))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    clave: Mapped[str] = mapped_column(String(120))
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
