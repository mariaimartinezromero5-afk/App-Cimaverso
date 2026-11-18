import os
import shutil
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="cimaverso_test_")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://pguser@localhost:5433/cimaverso_test")
os.environ["STORAGE_DIR"] = _tmp
os.environ["JWT_SECRET"] = "secreto-de-pruebas-con-longitud-suficiente-32b"

from litestar.testing import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import CLAVE_DEMO, sembrar  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(engine)
    sembrar()
    with TestClient(app=app) as c:
        yield c
    shutil.rmtree(_tmp, ignore_errors=True)


def _login(client, correo):
    r = client.post("/api/auth/login", json={"correo": correo, "password": CLAVE_DEMO})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture(scope="session")
def gerente(client):
    return _login(client, "gerente@cimaverso.co")


@pytest.fixture(scope="session")
def dev_andres(client):
    return _login(client, "andres@cimaverso.co")   # proyectos 1 y 2


@pytest.fixture(scope="session")
def dev_daniel(client):
    return _login(client, "daniel@cimaverso.co")   # solo proyecto 3
