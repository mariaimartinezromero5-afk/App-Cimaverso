import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from . import config


def hash_password(plana: str) -> str:
    return bcrypt.hashpw(plana.encode(), bcrypt.gensalt()).decode()


def verificar_password(plana: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(plana.encode(), hash_.encode())
    except ValueError:
        return False


def crear_token(usuario_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=config.JWT_HORAS)
    return jwt.encode({"sub": str(usuario_id), "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def leer_token(token: str) -> int | None:
    try:
        datos = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        return int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
