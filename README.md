# Cimaverso · Plataforma web inteligente para la gestión documental y de proyectos

Prototipo funcional (TRL 5) del proyecto de grado de Ingeniería de Sistemas (UNAD, curso 202016907).

**Stack:** Python 3.12 + Litestar · React 18 + Vite · PostgreSQL 16 · Nginx · Docker · metodología Scrum.

## Funcionalidades (RF01–RF16)
Autenticación con JWT y roles (gerente / desarrollador) · clientes · proyectos y equipo · tareas con estados · carpetas y documentos con versionado, papelera y restauración · búsqueda por contenido (texto completo en español) con filtros · dashboard de avance · alertas automáticas (tareas por vencer, proyectos retrasados, cambios) · historial de actividad · matriz de permisos.

## Ejecución con Docker (recomendada)
```bash
cp .env.example .env      # edite las claves
docker compose up --build
# Aplicación: http://localhost:8080
```
Al iniciar, la API crea las tablas y carga datos de demostración.

## Ejecución local sin Docker
```bash
# 1) Base de datos PostgreSQL con usuario/clave/base "cimaverso"
# 2) API
cd backend && pip install -r requirements.txt
python -m app.seed
litestar --app app.main:app run --port 8000
# 3) Frontend
cd frontend && npm install && npm run dev      # http://localhost:5173
```

## Credenciales de demostración
| Rol | Correo | Contraseña
|---|---|---|
| Gerente | mariaimartinezromero5@gmail.com| Maria12345*
| Desarrollador |  camila@gmail.com | Cimaverso2026*

## Pruebas
```bash
cd backend && python -m pytest -v     # 25 pruebas contra PostgreSQL real
```
Informe: `docs/informe_pruebas.txt`. Capturas de cada pantalla: `docs/capturas/`.

## Estructura
```
backend/   API Litestar (app/main.py, models.py, servicios.py, seed.py) y tests/
frontend/  React + Vite (src/pages, src/api.js)
docker-compose.yml · .env.example
```
