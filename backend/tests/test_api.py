"""Pruebas funcionales y de permisos del prototipo (una por requerimiento clave)."""
import io
from datetime import date, timedelta


# ---------------------------------------------------------------- RF01 autenticación
def test_rf01_login_correcto_e_incorrecto(client):
    ok = client.post("/api/auth/login", json={"correo": "gerente@cimaverso.co", "password": "Cimaverso2026*"})
    assert ok.status_code == 200 and ok.json()["usuario"]["rol"] == "gerente"
    mal = client.post("/api/auth/login", json={"correo": "gerente@cimaverso.co", "password": "incorrecta"})
    assert mal.status_code == 401


def test_rf01_rutas_protegidas_sin_token(client):
    assert client.get("/api/proyectos").status_code == 401
    assert client.get("/api/proyectos", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_rf01_logout_registra_actividad(client, gerente):
    assert client.post("/api/auth/logout", headers=gerente).status_code == 200
    acts = client.get("/api/actividad", headers=gerente).json()
    assert any(a["accion"] == "cerró sesión" for a in acts)


# ---------------------------------------------------------------- RF02/RF03 usuarios, roles y permisos
def test_rf02_gerente_crea_y_edita_usuarios(client, gerente):
    r = client.post("/api/usuarios", json={"nombre": "Nueva Persona", "correo": "nueva@cimaverso.co", "password": "ClaveSegura1", "rol": "desarrollador"}, headers=gerente)
    assert r.status_code == 201
    uid = r.json()["id"]
    assert client.post("/api/usuarios", json={"nombre": "X", "correo": "nueva@cimaverso.co", "password": "ClaveSegura1"}, headers=gerente).status_code == 400
    assert client.post("/api/usuarios", json={"nombre": "X", "correo": "x@x.co", "password": "corta"}, headers=gerente).status_code == 400
    p = client.patch(f"/api/usuarios/{uid}", json={"activo": False}, headers=gerente)
    assert p.status_code == 200 and p.json()["activo"] is False
    assert client.post("/api/auth/login", json={"correo": "nueva@cimaverso.co", "password": "ClaveSegura1"}).status_code == 401


def test_rf02_desarrollador_no_administra_usuarios(client, dev_andres):
    r = client.post("/api/usuarios", json={"nombre": "X", "correo": "z@z.co", "password": "ClaveSegura1"}, headers=dev_andres)
    assert r.status_code == 403
    assert client.patch("/api/usuarios/1", json={"nombre": "Hack"}, headers=dev_andres).status_code == 403


def test_rf03_desarrollador_solo_ve_proyectos_asignados(client, dev_andres, dev_daniel, gerente):
    assert len(client.get("/api/proyectos", headers=gerente).json()) >= 3
    ids_andres = {p["id"] for p in client.get("/api/proyectos", headers=dev_andres).json()}
    ids_daniel = {p["id"] for p in client.get("/api/proyectos", headers=dev_daniel).json()}
    assert len(ids_daniel) == 1 and ids_andres.isdisjoint(ids_daniel)
    ajeno = next(iter(ids_andres))
    assert client.get(f"/api/proyectos/{ajeno}", headers=dev_daniel).status_code == 403
    assert client.get(f"/api/proyectos/{ajeno}/tareas", headers=dev_daniel).status_code == 403
    assert client.get(f"/api/documentos?proyecto={ajeno}", headers=dev_daniel).json() == []


# ---------------------------------------------------------------- RF04 clientes
def test_rf04_clientes(client, gerente, dev_andres):
    r = client.post("/api/clientes", json={"nombre": "Cliente Prueba", "contacto": "Ana", "correo": "a@c.co"}, headers=gerente)
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.patch(f"/api/clientes/{cid}", json={"telefono": "3000000000"}, headers=gerente).json()["telefono"] == "3000000000"
    assert client.get("/api/clientes", headers=dev_andres).status_code == 200        # consulta
    assert client.post("/api/clientes", json={"nombre": "X"}, headers=dev_andres).status_code == 403   # no crea
    assert client.post("/api/clientes", json={"nombre": " "}, headers=gerente).status_code == 400


# ---------------------------------------------------------------- RF05/RF06 proyectos y miembros
def test_rf05_rf06_proyectos_y_asignacion(client, gerente, dev_daniel):
    r = client.post("/api/proyectos", json={"nombre": "Proyecto QA", "estado": "en curso", "fecha_inicio": "2026-01-10", "fecha_entrega": "2026-03-01"}, headers=gerente)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.post("/api/proyectos", json={"nombre": "Mal", "fecha_inicio": "2026-05-01", "fecha_entrega": "2026-04-01"}, headers=gerente).status_code == 400
    assert client.post("/api/proyectos", json={"nombre": "Mal", "estado": "inventado"}, headers=gerente).status_code == 400
    assert client.get(f"/api/proyectos/{pid}", headers=dev_daniel).status_code == 403      # aún no asignado
    daniel_id = next(u["id"] for u in client.get("/api/usuarios", headers=gerente).json() if u["correo"] == "daniel@cimaverso.co")
    assert client.post(f"/api/proyectos/{pid}/miembros", json={"usuario_id": daniel_id}, headers=gerente).status_code == 201
    assert client.get(f"/api/proyectos/{pid}", headers=dev_daniel).status_code == 200      # ya asignado
    assert client.patch(f"/api/proyectos/{pid}", json={"estado": "finalizado"}, headers=dev_daniel).status_code == 403
    client.delete(f"/api/proyectos/{pid}/miembros/{daniel_id}", headers=gerente)
    assert client.get(f"/api/proyectos/{pid}", headers=dev_daniel).status_code == 403


# ---------------------------------------------------------------- RF07 tareas
def test_rf07_tareas_y_porcentaje(client, gerente, dev_andres):
    pid = client.get("/api/proyectos", headers=dev_andres).json()[0]["id"]
    antes = client.get(f"/api/proyectos/{pid}", headers=dev_andres).json()
    t = client.post(f"/api/proyectos/{pid}/tareas", json={"titulo": "Tarea de prueba", "fecha_limite": str(date.today() + timedelta(days=30))}, headers=dev_andres)
    assert t.status_code == 201
    tid = t.json()["id"]
    assert client.patch(f"/api/tareas/{tid}", json={"estado": "inventado"}, headers=dev_andres).status_code == 400
    assert client.patch(f"/api/tareas/{tid}", json={"estado": "completada"}, headers=dev_andres).json()["estado"] == "completada"
    despues = client.get(f"/api/proyectos/{pid}", headers=dev_andres).json()
    assert despues["tareas_total"] == antes["tareas_total"] + 1
    assert despues["tareas_completadas"] == antes["tareas_completadas"] + 1


def test_rf07_no_se_edita_tarea_de_proyecto_ajeno(client, dev_daniel, gerente):
    tarea_p1 = client.get("/api/proyectos/1/tareas", headers=gerente).json()[0]["id"]
    assert client.patch(f"/api/tareas/{tarea_p1}", json={"estado": "completada"}, headers=dev_daniel).status_code == 403


# ---------------------------------------------------------------- RF08–RF10, RF13 documentos y versiones
def test_rf08_rf09_rf10_documentos_versiones_descarga(client, dev_andres):
    pid = client.get("/api/proyectos", headers=dev_andres).json()[0]["id"]
    r = client.post("/api/documentos", data={"proyecto_id": str(pid)}, files={"archivo": ("acta.txt", io.BytesIO("Acta de inicio del proyecto Alfa.".encode()), "text/plain")}, headers=dev_andres)
    assert r.status_code == 201, r.text
    did = r.json()["id"]
    assert r.json()["version_actual"] == 1
    v2 = client.post(f"/api/documentos/{did}/versiones", files={"archivo": ("acta.txt", io.BytesIO("Acta de inicio del proyecto Alfa, versión corregida.".encode()), "text/plain")}, headers=dev_andres)
    assert v2.status_code == 201 and v2.json()["version_actual"] == 2
    vs = client.get(f"/api/documentos/{did}/versiones", headers=dev_andres).json()
    assert [v["numero"] for v in vs] == [2, 1]
    d1 = client.get(f"/api/documentos/{did}/descargar?version=1", headers=dev_andres)
    assert d1.status_code == 200 and d1.content == "Acta de inicio del proyecto Alfa.".encode()
    d2 = client.get(f"/api/documentos/{did}/descargar", headers=dev_andres)
    assert b"corregida" in d2.content
    assert client.post("/api/documentos", data={"proyecto_id": str(pid)}, files={"archivo": ("vacio.txt", io.BytesIO(b""), "text/plain")}, headers=dev_andres).status_code == 400


def test_rf08_no_se_sube_a_proyecto_ajeno(client, dev_daniel, gerente):
    ajeno = client.get("/api/proyectos", headers=gerente).json()[-1]["id"]  # el más antiguo (proyecto 1)
    pid_daniel = client.get("/api/proyectos", headers=dev_daniel).json()[0]["id"]
    otro = next(p["id"] for p in client.get("/api/proyectos", headers=gerente).json() if p["id"] != pid_daniel)
    r = client.post("/api/documentos", data={"proyecto_id": str(otro)}, files={"archivo": ("x.txt", io.BytesIO(b"hola"), "text/plain")}, headers=dev_daniel)
    assert r.status_code == 403


# ---------------------------------------------------------------- RF11/RF12 búsqueda
def test_rf12_busqueda_por_contenido(client, gerente):
    r = client.get("/api/busqueda?q=garantía", headers=gerente).json()
    assert any(x["nombre"] == "contrato_asistente.docx" for x in r)        # texto dentro de un .docx
    assert any("garant" in x["fragmento"].lower() for x in r)
    r2 = client.get("/api/busqueda?q=reprogramar", headers=gerente).json()  # solo está en la versión 2
    assert [x["nombre"] for x in r2] == ["requerimientos_citas.txt"] and r2[0]["version"] == 2


def test_rf11_busqueda_filtros(client, gerente):
    por_tipo = client.get("/api/busqueda?tipo=docx", headers=gerente).json()
    assert por_tipo and all(x["tipo"] == "docx" for x in por_tipo)
    por_nombre = client.get("/api/busqueda?q=arquitectura", headers=gerente).json()
    assert any(x["nombre"] == "arquitectura_asistente.md" for x in por_nombre)
    assert client.get("/api/busqueda?q=palabraqueNoExiste123", headers=gerente).json() == []
    assert client.get("/api/busqueda?desde=2999-01-01", headers=gerente).json() == []


def test_rf11_busqueda_respeta_permisos(client, dev_daniel):
    assert client.get("/api/busqueda?q=garantía", headers=dev_daniel).json() == []      # contrato del proyecto 1


# ---------------------------------------------------------------- RF13 trazabilidad
def test_rf13_actividad_registra_quien_que_cuando(client, gerente, dev_daniel):
    acts = client.get("/api/actividad", headers=gerente).json()
    assert acts and {"usuario", "accion", "fecha"} <= set(acts[0])
    assert any(a["accion"] == "cargó una nueva versión de" for a in acts)
    # el desarrollador solo ve la actividad de sus proyectos
    pid_daniel = client.get("/api/proyectos", headers=dev_daniel).json()[0]["id"]
    assert all(a["proyecto_id"] == pid_daniel for a in client.get("/api/actividad", headers=dev_daniel).json())


# ---------------------------------------------------------------- RF14 dashboard
def test_rf14_dashboard(client, gerente, dev_daniel):
    d = client.get("/api/dashboard", headers=gerente).json()
    assert d["proyectos_activos"] >= 3 and 0 <= d["porcentaje_global"] <= 100
    assert d["carga_trabajo"] and d["tareas_vencidas"] >= 1
    dd = client.get("/api/dashboard", headers=dev_daniel).json()
    assert dd["proyectos_activos"] == 1 and dd["carga_trabajo"] == []


# ---------------------------------------------------------------- RF15 alertas
def test_rf15_alertas_automaticas(client, dev_andres):
    alertas = client.get("/api/alertas", headers=dev_andres).json()
    tipos = {a["tipo"] for a in alertas}
    assert "tarea_por_vencer" in tipos and "proyecto_retrasado" in tipos
    assert any("vencida" in a["mensaje"] for a in alertas)
    a = alertas[0]
    assert client.patch(f"/api/alertas/{a['id']}", headers=dev_andres).json()["leida"] is True
    # sin duplicados al consultar de nuevo
    otra = client.get("/api/alertas", headers=dev_andres).json()
    assert len(otra) == len({(x["mensaje"]) for x in otra if x["tipo"] != "cambio"}) + len([x for x in otra if x["tipo"] == "cambio"])


def test_rf15_alerta_por_cambio_en_documentos(client, dev_andres, gerente):
    ma = client.get("/api/alertas", headers=gerente).json()
    assert any(x["tipo"] == "cambio" for x in ma)   # el gerente se entera de cambios en tareas y documentos


def test_rf15_no_se_marca_alerta_ajena(client, gerente, dev_andres):
    aid = client.get("/api/alertas", headers=gerente).json()[0]["id"]
    assert client.patch(f"/api/alertas/{aid}", headers=dev_andres).status_code == 404


# ---------------------------------------------------------------- RF16 papelera
def test_rf16_papelera_y_restauracion(client, dev_andres):
    pid = client.get("/api/proyectos", headers=dev_andres).json()[0]["id"]
    did = client.post("/api/documentos", data={"proyecto_id": str(pid)}, files={"archivo": ("borrar.txt", io.BytesIO(b"borrame"), "text/plain")}, headers=dev_andres).json()["id"]
    assert client.delete(f"/api/documentos/{did}", headers=dev_andres).json()["estado"] == "papelera"
    assert did not in [d["id"] for d in client.get(f"/api/documentos?proyecto={pid}", headers=dev_andres).json()]
    assert did in [d["id"] for d in client.get(f"/api/documentos?proyecto={pid}&papelera=true", headers=dev_andres).json()]
    assert client.get("/api/busqueda?q=borrame", headers=dev_andres).json() == []
    assert client.post(f"/api/documentos/{did}/restaurar", headers=dev_andres).json()["estado"] == "activo"
    assert client.get("/api/busqueda?q=borrame", headers=dev_andres).json() != []


# ---------------------------------------------------------------- RNF03 seguridad
def test_rnf03_contrasena_con_hash(client):
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models import Usuario
    with SessionLocal() as db:
        for u in db.scalars(select(Usuario)):
            assert u.password_hash.startswith("$2") and "Cimaverso2026" not in u.password_hash


def test_rnf03_descarga_no_sale_de_la_carpeta(client, gerente):
    assert client.get("/api/documentos/999999/descargar", headers=gerente).status_code == 404


# ---------------------------------------------------------------- RNF04 rendimiento
def test_rnf04_busqueda_en_menos_de_3_segundos(client, gerente):
    import time
    t0 = time.perf_counter()
    client.get("/api/busqueda?q=proyecto", headers=gerente)
    assert time.perf_counter() - t0 < 3


def test_permisos_matriz(client, gerente):
    m = client.get("/api/permisos", headers=gerente).json()
    assert len(m) == 8 and m[0]["gerente"] == "Sí"
