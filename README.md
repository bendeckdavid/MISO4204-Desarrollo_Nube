# ANB Rising Stars Showcase API

API para la gestión de videos de artistas emergentes con sistema de votación y rankings. Proyecto desarrollado con FastAPI, PostgreSQL, Celery, Redis y Docker para el curso MISO4204 - Desarrollo en la Nube.

## 🚀 Características

- ✅ **FastAPI** - Framework moderno y rápido para construir APIs
- ✅ **Autenticación JWT** - Seguridad con tokens y bcrypt para contraseñas
- ✅ **PostgreSQL** - Base de datos relacional con UUIDs como primary keys
- ✅ **Procesamiento Asíncrono** - Celery + Redis para procesar videos en background
- ✅ **FFmpeg** - Procesamiento de video (recorte a 30s, resize a 720p, logo)
- ✅ **Docker Compose** - Orquestación de 5 contenedores
- ✅ **Nginx** - Reverse proxy con load balancing
- ✅ **Gunicorn** - 4 workers Uvicorn para alta concurrencia
- ✅ **pytest** - Suite de tests completa con 79% de cobertura (40 tests)
- ✅ **CI/CD** - Pipeline automatizado con GitHub Actions
- ✅ **Postman Collection** - Colección completa con tests automatizados

## 📋 Tabla de Contenidos

- [Inicio Rápido](#-inicio-rápido)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Documentación](#-documentación)
- [Video de Sustentación](#-video-de-sustentación)
- [API Endpoints](#-api-endpoints)
- [Ejemplos de Uso](#-ejemplos-de-uso)
- [Tests](#-tests)
- [Desarrollo](#-desarrollo)
- [Despliegue](#-despliegue)

## 🏃 Inicio Rápido

### Prerrequisitos

- Docker >= 20.10
- Docker Compose >= 2.0
- Python 3.12+ (solo para desarrollo local)

### 1. Clonar y Configurar

```bash
git clone https://github.com/tu-usuario/MISO4204-Desarrollo_Nube.git
cd MISO4204-Desarrollo_Nube

# El archivo .env ya está configurado para desarrollo local
# Puedes modificarlo si lo necesitas
```

### 2. Iniciar Servicios

```bash
# Construir e iniciar todos los servicios
docker-compose build --no-cache
docker-compose up -d

# Esperar ~30 segundos para que todos los servicios estén listos
sleep 30

# Verificar el estado de los servicios
docker-compose ps
```

Deberías ver:
```
     Name                   Command                  State                        Ports
-----------------------------------------------------------------------------------------------------------
fastapi_api      gunicorn app.main:app ...        Up             8000/tcp
fastapi_db       docker-entrypoint.sh postgres    Up (healthy)   0.0.0.0:5433->5432/tcp
fastapi_nginx    /docker-entrypoint.sh nginx ...  Up (healthy)   0.0.0.0:8080->80/tcp
fastapi_redis    docker-entrypoint.sh redis ...   Up (healthy)   0.0.0.0:6380->6379/tcp
fastapi_worker   celery -A app.worker.celery ...  Up             8000/tcp
```

### 3. Verificar Instalación

```bash
# Health check
curl http://localhost:8080/health

# Respuesta esperada:
# {"status":"healthy","version":"1.0.0"}
```

### 4. Acceder a la Documentación

- **API Base URL**: http://localhost:8080
- **Swagger UI (Interactiva)**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 📁 Estructura del Proyecto

```
MISO4204-Desarrollo_Nube/
├── app/                                 # Código fuente de la aplicación
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py                  # Endpoints de autenticación
│   │       ├── health.py                # Health check
│   │       ├── videos.py                # Gestión de videos (CRUD)
│   │       └── public.py                # Endpoints públicos (votos, rankings)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Configuración con Pydantic Settings
│   │   └── security.py                  # JWT token management
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                      # Base model con UUID y timestamps
│   │   ├── database.py                  # SQLAlchemy engine y session
│   │   └── models.py                    # Modelos (User, Video, Vote)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                      # Schemas de autenticación
│   │   ├── video.py                     # Schemas de videos
│   │   └── vote.py                      # Schemas de votos y rankings
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── celery_app.py                # Configuración de Celery
│   │   └── tasks.py                     # Tareas asíncronas (procesamiento de video)
│   └── main.py                          # Punto de entrada de FastAPI
│
├── tests/                               # Suite de tests
│   ├── api/
│   │   ├── test_auth.py                 # Tests de autenticación (15 tests)
│   │   ├── test_videos.py               # Tests de videos (14 tests)
│   │   ├── test_public.py               # Tests de endpoints públicos (9 tests)
│   │   └── test_health.py               # Tests de health check (2 tests)
│   └── conftest.py                      # Fixtures de pytest
│
├── docs/                                # Documentación del proyecto
│   └── Entrega_1/
│       ├── arquitectura.md              # Arquitectura completa del sistema
│       ├── decisiones_diseno.md         # Decisiones arquitectónicas
│       ├── modelo_datos.md              # Modelo de datos y relaciones
│       ├── images/                      # Diagramas exportados
│       │   ├── modelo_contexto.jpeg     # Diagrama C4 - Contexto
│       │   ├── modelo_contenedores.png  # Diagrama C4 - Contenedores
│       │   ├── modelo_secuencia.png     # Diagrama de secuencia
│       │   └── modelo_relacional.jpeg   # Modelo relacional de BD
│       └── pruebas_carga/
│           └── reporte.md               # Resultados de pruebas de carga
│
├── collections/                         # Colección de Postman
│   ├── postman_collection.json          # Colección con 9 endpoints + tests
│   ├── postman_environment.json         # Variables de entorno
│   └── README.md                        # Guía de uso con Newman CLI
│
├── scripts/
│   └── load_data.py                     # Script para cargar datos de ejemplo
│
├── media/                               # Archivos de video (montado como volumen)
│   ├── uploads/                         # Videos originales subidos
│   └── processed/                       # Videos procesados
│
├── .env                                 # Variables de entorno
├── .github/
│   └── workflows/
│       └── ci.yml                       # Pipeline de CI/CD
├── docker-compose.yml                   # Orquestación de servicios
├── Dockerfile                           # Imagen para API y Worker
├── nginx.conf                           # Configuración de Nginx
├── pyproject.toml                       # Dependencias con Poetry
├── .pre-commit-config.yaml              # Hooks de pre-commit
└── README.md                            # Este archivo
```

## 📚 Documentación

### Documentos Disponibles

| Documento | Ubicación | Descripción |
|-----------|-----------|-------------|
| **Arquitectura del Sistema** | [docs/Entrega_1/arquitectura.md](docs/Entrega_1/arquitectura.md) | Documentación completa incluyendo:<br>• Diagramas C4 (Contexto y Contenedores)<br>• Diagramas de secuencia<br>• Decisiones de diseño<br>• Contratos de API<br>• Stack tecnológico |
| **Decisiones de Diseño** | [docs/Entrega_1/decisiones_diseno.md](docs/Entrega_1/decisiones_diseno.md) | Decisiones arquitectónicas y justificaciones |
| **Modelo de Datos** | [docs/Entrega_1/modelo_datos.md](docs/Entrega_1/modelo_datos.md) | Modelo relacional y relaciones entre entidades |
| **Reporte SonarQube** | [docs/Entrega_1/reporte_sonarqube.md](docs/Entrega_1/reporte_sonarqube.md) | Análisis de calidad de código, cobertura, seguridad y mantenibilidad |
| **Pruebas de Carga** | [docs/Entrega_1/pruebas_carga/reporte.md](docs/Entrega_1/pruebas_carga/reporte.md) | Resultados y análisis de pruebas de rendimiento |
| **Colección de Postman** | [collections/README.md](collections/README.md) | Guía completa para usar la colección con Postman y Newman |

### Diagramas

Todos los diagramas están disponibles como imágenes en [`docs/Entrega_1/images/`](docs/Entrega_1/images/):

- **[Diagrama de Contexto (C4)](docs/Entrega_1/images/modelo_contexto.jpeg)** - Vista de alto nivel del sistema
- **[Diagrama de Contenedores (C4)](docs/Entrega_1/images/modelo_contenedores.png)** - Arquitectura de contenedores
- **[Diagrama de Secuencia](docs/Entrega_1/images/modelo_secuencia.png)** - Flujo de procesamiento de videos
- **[Modelo Relacional](docs/Entrega_1/images/modelo_relacional.jpeg)** - Estructura de base de datos

### Reporte de Calidad

El proyecto incluye un análisis exhaustivo de calidad de código realizado con SonarQube:

- **[Reporte SonarQube](docs/Entrega_1/reporte_sonarqube.md)** - Análisis completo de calidad, cobertura y seguridad
  - Quality Gate: ✅ PASSED
  - Code Coverage: 100%
  - Code Duplications: 0.0%
  - Security Rating: A
  - Reliability Rating: C (3 minor issues)
  - Maintainability Rating: A

---

## 🎥 Video de Sustentación

### Demostración del Proyecto

A continuación se presenta el video de sustentación donde se demuestra el funcionamiento completo del sistema **ANB Rising Stars Showcase API**, incluyendo:

- Arquitectura del sistema y decisiones de diseño
- Demostración de endpoints de autenticación (registro y login)
- Carga y procesamiento asíncrono de videos con Celery
- Sistema de votación y rankings públicos
- Análisis de cobertura de tests (79% pytest, 100% SonarQube)
- Resultados de pruebas de carga con K6
- Reporte de calidad de código con SonarQube

### 📹 Enlace al Video

> **[Aquí se colocará el enlace al video de sustentación]**
>
> _Nota: El video será publicado próximamente_

**Duración aproximada:** 15-20 minutos

**Contenido del video:**
1. Introducción al proyecto y objetivos (2 min)
2. Arquitectura y stack tecnológico (3 min)
3. Demostración de funcionalidades principales (8 min)
   - Registro y autenticación de usuarios
   - Upload y procesamiento de videos
   - Votación por videos publicados
   - Consulta de rankings por ciudad
4. Métricas de calidad y testing (4 min)
   - Cobertura de tests con pytest (79%, 40 tests)
   - Análisis SonarQube (Quality Gate: Passed, Coverage: 100%)
   - Pruebas de carga con K6
5. Conclusiones y trabajo futuro (2 min)

**Plataforma de visualización:** YouTube / Vimeo

---

## 🔌 API Endpoints

### Resumen de Endpoints

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check del servicio |
| `/api/auth/signup` | POST | No | Registro de nuevo usuario |
| `/api/auth/login` | POST | No | Login y obtención de JWT |
| `/api/videos/upload` | POST | JWT | Subir video para procesamiento |
| `/api/videos/` | GET | JWT | Listar mis videos |
| `/api/videos/{video_id}` | GET | JWT | Obtener detalles de un video |
| `/api/videos/{video_id}` | DELETE | JWT | Eliminar un video |
| `/api/public/videos` | GET | No | Listar videos públicos |
| `/api/public/videos/{video_id}/vote` | POST | JWT | Votar por un video |
| `/api/public/rankings` | GET | No | Ver ranking de videos |

### Base URL

```
http://localhost:8080
```

**Nota:** Todas las peticiones pasan por el proxy reverso de Nginx en el puerto 8080.

## 💡 Ejemplos de Uso

### 1. Health Check

```bash
curl http://localhost:8080/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### 2. Registro de Usuario

```bash
curl -X POST http://localhost:8080/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "artist@example.com",
    "password1": "SecurePass123!",
    "password2": "SecurePass123!",
    "first_name": "Carlos",
    "last_name": "Martinez",
    "city": "Bogota",
    "country": "Colombia"
  }'
```

**Respuesta (201 Created):**
```json
{
  "id": "ec3fe238-8640-4649-8837-e1b2cfc19be8",
  "first_name": "Carlos",
  "last_name": "Martinez",
  "email": "artist@example.com",
  "city": "Bogota",
  "country": "Colombia"
}
```

**Errores posibles:**
- `400` - Email ya registrado o contraseñas no coinciden
- `422` - Error de validación (email inválido, contraseña corta, etc.)

---

### 3. Login

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "artist@example.com",
    "password": "SecurePass123!"
  }'
```

**Respuesta (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Guarda el `access_token` para usarlo en endpoints protegidos!**

---

### 4. Subir Video (requiere JWT)

```bash
# Primero exporta el token
export TOKEN="tu_access_token_aqui"

# Subir video con archivo
# El video debe existir si se prueba con curl
curl -X POST http://localhost:8080/api/videos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/ruta/a/tu/video.mp4" \
  -F "title=Mi Video Musical" \
  -F "description=Una presentación increíble"
```

**Respuesta (202 Accepted):**
```json
{
  "id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "title": "Mi Video Musical",
  "description": "Una presentación increíble",
  "status": "processing",
  "user_id": "ec3fe238-8640-4649-8837-e1b2cfc19be8",
  "created_at": "2025-10-19T20:30:00"
}
```

**Notas:**
- El video se procesará de forma asíncrona con Celery
- Formatos aceptados: MP4, AVI, MOV
- Tamaño máximo: 500MB
- El video será recortado a 30 segundos, redimensionado a 720p y se le agregará un logo

---

### 5. Listar Mis Videos (requiere JWT)

```bash
curl -X GET http://localhost:8080/api/videos/ \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta (200 OK):**
```json
[
  {
    "id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "title": "Mi Video Musical",
    "description": "Una presentación increíble",
    "status": "completed",
    "original_file_path": "/media/uploads/video.mp4",
    "processed_file_path": "/media/processed/video_processed.mp4",
    "is_published": false,
    "created_at": "2025-10-19T20:30:00",
    "updated_at": "2025-10-19T20:32:00"
  }
]
```

**Estados posibles:**
- `pending` - En cola de procesamiento
- `processing` - Procesándose actualmente
- `completed` - Procesado exitosamente
- `failed` - Error en el procesamiento

---

### 6. Obtener Detalles de un Video (requiere JWT)

```bash
# Cambiar el video_id

curl -X GET http://localhost:8080/api/videos/{video_id} \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta (200 OK):**
```json
{
  "id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "title": "Mi Video Musical",
  "description": "Una presentación increíble",
  "status": "completed",
  "original_file_path": "/media/uploads/video.mp4",
  "processed_file_path": "/media/processed/video_processed.mp4",
  "is_published": false,
  "user_id": "ec3fe238-8640-4649-8837-e1b2cfc19be8",
  "created_at": "2025-10-19T20:30:00",
  "updated_at": "2025-10-19T20:32:00"
}
```

---

### 7. Eliminar Video (requiere JWT)
```bash
# Cambiar el video_id
curl -X DELETE http://localhost:8080/api/videos/{video_id} \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta (204 No Content):**
*(Sin contenido en el body)*

**Errores posibles:**
- `404` - Video no encontrado
- `403` - No tienes permiso para eliminar este video

---

### 8. Listar Videos Públicos (sin auth)

```bash
curl "http://localhost:8080/api/public/videos?page=1&page_size=10&order_by=created_at&order=desc"
```

**Parámetros de query:**
- `page` (opcional): Número de página (default: 1)
- `page_size` (opcional): Videos por página (default: 10, máx: 100)
- `order_by` (opcional): Campo para ordenar (created_at, title)
- `order` (opcional): Orden (asc, desc)
- `city` (opcional): Filtrar por ciudad del artista
- `country` (opcional): Filtrar por país del artista

**Respuesta (200 OK):**
```json
[
  {
    "video_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "title": "Mi Video Musical",
    "player_name": "Carlos Martinez",
    "city": "Bogota",
    "country": "Colombia",
    "processed_url": "https://anb.com/videos/processed/a1b2c3d4-5678-90ab-cdef-1234567890ab.mp4",
    "votes": 15,
    "uploaded_at": "2025-10-19T20:30:00"
  }
]
```

---

### 9. Votar por un Video (requiere JWT)

```bash
curl -X POST http://localhost:8080/api/public/videos/{video_id}/vote \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta (200 OK):**
```json
{
  "message": "Vote registered successfully",
  "video_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "user_id": "ec3fe238-8640-4649-8837-e1b2cfc19be8"
}
```

**Errores posibles:**
- `400` - Ya votaste por este video
- `404` - Video no encontrado

---

### 10. Ver Ranking de Videos (sin auth)

```bash
curl "http://localhost:8080/api/public/rankings?page=1&page_size=20"
```

**Parámetros de query:**
- `page` (opcional): Número de página (default: 1)
- `page_size` (opcional): Resultados por página (default: 20, máx: 100)
- `city` (opcional): Filtrar por ciudad
- `country` (opcional): Filtrar por país

**Respuesta (200 OK):**
```json
{
  "rankings": [
    {
      "position": 1,
      "video_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
      "title": "Mi Video Musical",
      "vote_count": 150,
      "artist_name": "Carlos Martinez",
      "city": "Bogota",
      "country": "Colombia"
    },
    {
      "position": 2,
      "video_id": "b2c3d4e5-6789-01bc-def0-2345678901bc",
      "title": "Otro Video",
      "vote_count": 120,
      "artist_name": "Maria Lopez",
      "city": "Medellin",
      "country": "Colombia"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

## 🧪 Tests

### Ejecutar Tests

```bash
# Ejecutar todos los tests
docker-compose exec -T api pytest tests/ -v

# Con reporte de cobertura
docker-compose exec -T api pytest tests/ --cov=app --cov-report=term

# Generar reporte HTML de cobertura
docker-compose exec -T api pytest tests/ --cov=app --cov-report=html
# Abre htmlcov/index.html en tu navegador

# Ejecutar suite específica
docker-compose exec -T api pytest tests/api/test_auth.py -v
```

### Cobertura de Tests

**Cobertura actual: 79% (40 tests pasando)**

**Desglose por archivo:**
- `app/api/routes/auth.py` - **100%** (15 tests)
- `app/api/routes/health.py` - **100%** (2 tests)
- `app/api/routes/public.py` - **98%** (9 tests)
- `app/api/routes/videos.py` - **82%** (14 tests)
- `app/core/security.py` - **74%**
- `app/db/models.py` - **95%**
- `app/schemas/*` - **100%**

**Suites de tests:**
1. **Autenticación** (15 tests) - Signup, login, JWT, protección de endpoints
2. **Gestión de Videos** (14 tests) - Upload, list, get, delete
3. **Endpoints Públicos** (9 tests) - Videos públicos, votación, rankings
4. **Health Check** (2 tests) - Verificación de salud del servicio

### Pruebas con Postman/Newman

```bash
# Instalar newman (si no lo tienes)
npm install -g newman

# Ejecutar colección completa
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --delay-request 1000

# Ejecutar carpeta específica
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --folder "Authentication"

# Generar reporte HTML
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  -r html \
  --reporter-html-export newman-report.html
```

Ver [collections/README.md](collections/README.md) para guía completa.

---

## 💻 Desarrollo

### Configuración Local (sin Docker)

```bash
# Instalar Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependencias
poetry install

# Iniciar servicios de base de datos
docker-compose up -d db redis

# Ejecutar API
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar worker de Celery (en otra terminal)
poetry run celery -A app.worker.celery_app worker --loglevel=info
```

### Variables de Entorno

Configuradas en el archivo `.env`:

```bash
# Base de datos
DATABASE_URL=postgresql://fastapi_user:fastapi_password@db:5432/fastapi_db

# JWT
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Aplicación
PROJECT_NAME=ANB Rising Stars Showcase API
VERSION=1.0.0
ENVIRONMENT=development
```

### Code Quality

```bash
# Formatear código
docker-compose exec api poetry run black .

# Ordenar imports
docker-compose exec api poetry run isort .

# Linting
docker-compose exec api poetry run flake8 app tests

# Type checking
docker-compose exec api poetry run mypy app

# Ejecutar todos los checks
docker-compose exec api poetry run black . --check && \
  docker-compose exec api poetry run flake8 app tests && \
  docker-compose exec api poetry run mypy app
```

---

## 🚀 Despliegue

### Arquitectura

El sistema está configurado con:

- **Gunicorn** con 4 workers Uvicorn para alto rendimiento
- **Nginx** como reverse proxy con load balancing `least_conn`
- **PostgreSQL** con connection pooling (10 base + 20 overflow por worker)
- **Redis** para caché y cola de tareas de Celery
- **Celery Worker** para procesamiento asíncrono de videos

### Comandos Docker

```bash
# Iniciar servicios
docker-compose up -d

# Reconstruir e iniciar
docker-compose up --build -d

# Ver logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs --tail=100 api

# Detener servicios
docker-compose stop

# Eliminar todo (incluyendo volúmenes)
docker-compose down -v

# Ejecutar comando en contenedor
docker-compose exec api bash
docker-compose exec api python scripts/load_data.py

# Reiniciar servicios específicos
docker-compose restart api worker
```

### Base de Datos

```bash
# Conectar a PostgreSQL
docker-compose exec db psql -U fastapi_user -d fastapi_db

# Ver tablas
docker-compose exec db psql -U fastapi_user -d fastapi_db -c "\dt"

# Ver usuarios
docker-compose exec db psql -U fastapi_user -d fastapi_db -c "SELECT id, email, first_name, last_name FROM users;"

# Backup
docker-compose exec db pg_dump -U fastapi_user fastapi_db > backup.sql

# Restore
docker-compose exec -T db psql -U fastapi_user fastapi_db < backup.sql
```

### Celery Operations

```bash
# Ver tareas activas
docker-compose exec worker celery -A app.worker.celery_app inspect active

# Ver tareas registradas
docker-compose exec worker celery -A app.worker.celery_app inspect registered

# Purgar todas las tareas de la cola
docker-compose exec worker celery -A app.worker.celery_app purge
```

---

## 📊 CI/CD Pipeline

Pipeline automatizado con GitHub Actions que se ejecuta en cada push a `main` o `develop`:

### Etapas

1. **Tests y Linting**
   - Setup de Python 3.12 y Poetry
   - Ejecución de flake8, black y mypy
   - Ejecución de 40 tests con pytest
   - Generación de reporte de cobertura

2. **Build de Docker**
   - Construcción de imagen Docker
   - Validación de docker-compose.yml
   - Uso de caché para optimización

3. **SonarQube** (condicional)
   - Análisis de código estático
   - Métricas de calidad y cobertura

Ver configuración completa en [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

---

## 👥 Equipo

Proyecto desarrollado para el curso MISO4204 - Desarrollo en la Nube, Universidad de los Andes.

---

## 🔗 Enlaces Útiles

- [Documentación Interactiva (Swagger)](http://localhost:8080/docs)
- [Documentación Alternativa (ReDoc)](http://localhost:8080/redoc)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)

---

**¿Necesitas ayuda?** Consulta la [documentación completa](docs/Entrega_1/arquitectura.md) o abre un issue en GitHub.
