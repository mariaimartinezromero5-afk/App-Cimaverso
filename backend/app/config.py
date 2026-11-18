"""Configuración de la plataforma (se lee de variables de entorno)."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://cimaverso:cimaverso@localhost:5432/cimaverso")
JWT_SECRET = os.getenv("JWT_SECRET", "cambiar-en-produccion")
JWT_HORAS = int(os.getenv("JWT_HORAS", "12"))
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage")).resolve()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
DIAS_ALERTA_VENCIMIENTO = int(os.getenv("DIAS_ALERTA_VENCIMIENTO", "3"))
