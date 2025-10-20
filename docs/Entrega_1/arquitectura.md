# Arquitectura del Sistema - ANB Rising Stars Showcase

## 1. Introducción

El sistema ANB Rising Stars Showcase es una aplicación web diseñada para permitir que jugadores de baloncesto suban videos mostrando sus habilidades. La arquitectura implementa un patrón de microservicios con procesamiento asíncrono, donde el backend maneja las solicitudes HTTP mientras que workers dedicados procesan los videos en segundo plano.

---

## 2. Vista de Contexto del Sistema

### 2.1 Diagrama C4 - Nivel 1: Contexto

![Diagrama de Contexto](images/modelo_contexto.jpeg)

*Diagrama que muestra: Cliente (Jugador) interactuando con el Sistema ANB Rising Stars Showcase y el Sistema de Almacenamiento, con flechas bidireccionales indicando las comunicaciones HTTP/HTTPS y File I/O.*

### 2.2 Descripción de Actores

**Cliente (Jugador)**
- Usuario que interactúa con el sistema
- Sube videos de sus habilidades
- Consulta el estado de procesamiento de sus videos
- Accede mediante HTTP/HTTPS

**Sistema ANB Rising Stars Showcase**
- Sistema central que gestiona toda la lógica de negocio
- Procesa videos automáticamente con FFmpeg
- Almacena información de usuarios y videos

**Sistema de Almacenamiento**
- Almacena videos originales y procesados
- Actualmente: Filesystem local
- Futuro: AWS S3

---

## 3. Vista de Contenedores

### 3.1 Diagrama C4 - Nivel 2: Contenedores

![Diagrama de Contenedores](images/modelo_contenedores.png)

*Diagrama que muestra: Cliente conectándose al sistema Docker Compose que contiene 5 contenedores (Proxy Inverso, Backend FastAPI, PostgreSQL, Redis, Celery Worker) con sus respectivas conexiones y protocolos de comunicación.*

### 3.2 Componentes del Sistema dentro de Docker Compose

El sistema está compuesto por los siguientes servicios orquestados con Docker Compose:

**1. Proxy Inverso (Nginx)**
- Punto de entrada único para las solicitudes del cliente
- Enruta el tráfico hacia los servicios internos
- Load balancing con algoritmo `least_conn`
- Puerto expuesto: 80 (8080 en host)
- Maneja uploads de hasta 100MB
- Timeouts configurados para operaciones largas (300s)

**2. Database (PostgreSQL)**
- Base de datos relacional
- Almacena usuarios, videos, votos y metadatos
- Persistencia de datos transaccionales
- Connection pooling: max_connections=300
- Optimizado con shared_buffers y effective_cache_size

**3. Backend (Python/FastAPI + Gunicorn)**
- API REST que procesa las solicitudes HTTP
- Maneja autenticación JWT
- Coordina el flujo de trabajo entre servicios
- Lenguaje: Python con framework FastAPI
- Process manager: Gunicorn con 4 workers Uvicorn
- Endpoints para gestión de videos y sistema de votación

**4. Broker de Mensajería (Redis)**
- Sistema de colas para tareas asíncronas
- Coordina la comunicación entre Backend y Worker
- Almacena trabajos pendientes de procesamiento
- Futuro: Cache de rankings con TTL

**5. Worker (Celery)**
- Procesa videos de forma asíncrona
- Ejecuta FFmpeg para transformaciones
- Actualiza el estado de los videos en la base de datos


### 3.3 Descripción Detallada de Contenedores

#### Nginx (Reverse Proxy)
- Contenedor: `fastapi_nginx`
- Puerto expuesto: 8080 → 80
- Responsabilidades:
  - Reverse proxy hacia API backend
  - Load balancing con `least_conn`
  - Buffering de uploads grandes
  - Health checks del backend
  - Configuración de timeouts

#### FastAPI (API Backend)
- Contenedor: `fastapi_api`
- Puerto interno: 8000
- Comando: `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker`
- Responsabilidades:
  - Endpoints REST para autenticación (signup, login)
  - Endpoints REST para gestión de videos (upload, list, detail, delete)
  - Endpoints REST públicos para votación y rankings
  - Validación de datos con Pydantic
  - Autenticación JWT
  - Connection pooling a PostgreSQL (pool_size=10, max_overflow=20)

#### Redis (Message Broker)
- Contenedor: `fastapi_redis`
- Puerto: 6379
- Responsabilidades:
  - Broker de mensajes para Celery
  - Cola de tareas de procesamiento de videos
  - Cache (opcional para optimización futura)

#### Worker (Celery Worker)
- Contenedor: `fastapi_worker`
- Sin puerto expuesto
- Responsabilidades:
  - Consumir tareas de la cola de Redis
  - Procesar videos con FFmpeg
  - Actualizar estado de videos en PostgreSQL

#### PostgreSQL (Base de Datos)
- Contenedor: `fastapi_db`
- Puerto: 5432 (5433 en host)
- Comando: `postgres -c max_connections=300 -c shared_buffers=256MB`
- Responsabilidades:
  - Almacenar usuarios (tabla `users`)
  - Almacenar videos (tabla `videos`)
  - Almacenar votos (tabla `votes`)
  - Garantizar integridad referencial (ACID)
  - Constraint único para prevenir votos duplicados

### 3.4 Flujo de Comunicación entre Contenedores

```
Cliente → Nginx → FastAPI → PostgreSQL (consultas/escrituras)
                     ↓
                   Redis (encolar tarea)
                     ↓
                  Worker → PostgreSQL (actualizar estado)
                     ↓
                  FFmpeg (procesamiento de video)
```

**Flujo de Votación**:
```
Cliente → Nginx → FastAPI → PostgreSQL (INSERT INTO votes)
                                ↓
                          Validaciones:
                          - Usuario autenticado
                          - Video existe y está publicado
                          - No votar por propio video
                          - Constraint único previene duplicados
```

---

## 4. Flujo de Procesamiento de Videos

### 4.1 Diagrama de Secuencia

![Diagrama de Secuencia](images/modelo_secuencia.png)

*Diagrama que muestra los 12 pasos del flujo completo: Cliente → FastAPI → PostgreSQL → Redis → Worker → FFmpeg, dividido en 3 fases: Carga de Archivo (pasos 1-4), Procesamiento Asíncrono (pasos 5-9), y Consulta de Estado (pasos 10-12).*

**Nota:** Este diagrama está en formato PlantUML para mantener las líneas verticales continuas.

### 4.2 Carga de Archivo

**Paso 1: Cliente envía solicitud**
```
POST /api/videos/upload
Authorization: Bearer <JWT_TOKEN>
Body: multipart/form-data con archivo de video
```

**Paso 2: FastAPI recibe y valida**
- Valida JWT token (autenticación)
- Valida formato de archivo
- Valida tamaño de archivo

**Paso 3: Consulta/Entrada a Cola de Mensajes**
- FastAPI guarda metadata en PostgreSQL (estado: `uploaded`)
- Guarda archivo en filesystem temporal
- Encola tarea en Redis con ID del video

**Paso 4: FastAPI responde inmediatamente**
```json
{
  "id": "video-uuid",
  "status": "uploaded",
  "message": "Video en cola para procesamiento"
}
```

### 4.3 Procesamiento Asíncrono

**Paso 5: Worker consume tarea**
- Celery worker lee tarea de Redis
- Actualiza estado en BD: `processing`

**Paso 6: Actualiza estado a procesando**
```sql
UPDATE videos SET status = 'processing' WHERE id = 'video-uuid';
```

**Paso 7: Procesa el archivo**
Worker ejecuta FFmpeg con 3 operaciones:

1. **Recortar**: Primeros 20 segundos
   ```bash
   ffmpeg -i input.mp4 -t 20 -c copy trimmed.mp4
   ```

2. **Redimensionar**: 1280x720
   ```bash
   ffmpeg -i trimmed.mp4 -vf scale=1280:720 resized.mp4
   ```

3. **Agregar logo**: Logo ANB en esquina superior derecha
   ```bash
   ffmpeg -i resized.mp4 -i logo.png -filter_complex \
     "[1:v]scale=120:60[logo];[0:v][logo]overlay=W-w-10:10" \
     output.mp4
   ```

**Paso 8: Guarda archivo procesado**
- Guarda video procesado en filesystem
- Obtiene duración del video procesado

**Paso 9: Actualiza estado a procesado**
```sql
UPDATE videos
SET status = 'processed',
    processed_url = '/path/to/processed/video.mp4',
    duration_seconds = 20,
    processed_at = NOW()
WHERE id = 'video-uuid';
```

### 4.4 Consulta de Estado

**Paso 10: Cliente consulta estado**
```
GET /api/videos/{video_id}
Authorization: Bearer <JWT_TOKEN>
```

**Paso 11: FastAPI consulta Base de Datos**
```sql
SELECT * FROM videos WHERE id = 'video-uuid';
```

**Paso 12: Respuesta con estado actualizado**
```json
{
  "id": "video-uuid",
  "title": "Mi video",
  "status": "processed",
  "processed_url": "/videos/processed/video.mp4",
  "duration_seconds": 20,
  "uploaded_at": "2025-10-19T10:00:00Z",
  "processed_at": "2025-10-19T10:02:30Z"
}
```

### 4.5 Manejo de Errores

Si el procesamiento falla:
- Worker captura excepción
- Actualiza estado a `failed`
- Registra error en logs
- Cliente ve estado "failed" al consultar

---

## 5. Sistema de Votación y Rankings

### 5.1 Arquitectura del Sistema de Votación

El sistema de votación permite a los usuarios votar por videos de otros jugadores y genera rankings basados en el total de votos recibidos.

**Componentes involucrados**:
- **FastAPI**: Endpoints públicos para votación y rankings
- **PostgreSQL**: Tabla `votes` con constraint único `(user_id, video_id)`
- **Nginx**: Proxy de requests de votación

### 5.2 Flujo de Votación

**Paso 1: Usuario solicita votar**
```
POST /api/public/videos/{video_id}/vote
Authorization: Bearer <JWT_TOKEN>
```

**Paso 2: Validaciones en FastAPI**
```python
# 1. Verificar que el video existe
video = db.query(Video).filter(Video.id == video_id).first()
if not video:
    return 404 "Video not found"

# 2. Verificar que el video está publicado y procesado
if video.status not in ["processed", "completed"]:
    return 400 "Video not available for voting"

# 3. Verificar que no es el propio video del usuario
if video.user_id == current_user.id:
    return 400 "Cannot vote for your own video"

# 4. Verificar que no ha votado antes (query)
existing_vote = db.query(Vote).filter(
    Vote.user_id == current_user.id,
    Vote.video_id == video_id
).first()
if existing_vote:
    return 400 "Already voted for this video"
```

**Paso 3: Crear voto en base de datos**
```sql
INSERT INTO votes (id, user_id, video_id, voted_at)
VALUES (uuid_generate_v4(), '{user_id}', '{video_id}', NOW());

-- El UNIQUE CONSTRAINT previene duplicados a nivel de BD
-- CONSTRAINT uq_user_video_vote UNIQUE (user_id, video_id)
```

**Paso 4: Respuesta exitosa**
```json
{
  "message": "Voto registrado exitosamente.",
  "video_id": "uuid",
  "total_votes": 42
}
```

### 5.3 Flujo de Rankings

**Paso 1: Cliente solicita rankings**
```
GET /api/public/rankings?city=Bogotá&page=1&page_size=20
```

**Nota**: Este endpoint NO requiere autenticación (público).

**Paso 2: Query SQL de agregación**
```sql
SELECT
    u.id,
    u.first_name,
    u.last_name,
    u.city,
    u.country,
    COUNT(v.id) AS vote_count
FROM users u
INNER JOIN videos vid ON u.id = vid.user_id
LEFT JOIN votes v ON vid.id = v.video_id
WHERE vid.status IN ('processed', 'completed')
  AND (u.city = 'Bogotá' OR 'Bogotá' IS NULL)  -- Filtro opcional
GROUP BY u.id, u.first_name, u.last_name, u.city, u.country
ORDER BY vote_count DESC
LIMIT 20 OFFSET 0;
```

**Paso 3: Construcción de respuesta con paginación**
```json
{
  "rankings": [
    {
      "position": 1,
      "username": "Juan Pérez",
      "city": "Bogotá",
      "country": "Colombia",
      "votes": 1530
    },
    {
      "position": 2,
      "username": "María López",
      "city": "Bogotá",
      "country": "Colombia",
      "votes": 1495
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

### 5.4 Optimizaciones de Performance

**Índices en tabla `votes`**:
```sql
CREATE INDEX idx_votes_user_id ON votes(user_id);
CREATE INDEX idx_votes_video_id ON votes(video_id);
CREATE UNIQUE INDEX idx_votes_unique ON votes(user_id, video_id);
```

**Mejoras futuras**:
- **Redis caching**: Cachear rankings con TTL de 1-5 minutos
- **Materialized views**: Pre-calcular rankings cada N minutos
- **Read replicas**: Queries de rankings en replica para no afectar writes

### 5.5 Protección de Integridad

**Reglas de negocio implementadas**:
1. **No auto-votación**: Usuario no puede votar por sus propios videos
2. **Un voto por video**: Constraint único previene votos múltiples
3. **No eliminación con votos**: Videos con votos no pueden ser eliminados
4. **Solo videos publicados**: Solo videos con `is_published=true` y `status=completed` son votables

---

## 6. Diagrama de Despliegue

### 6.1 Infraestructura Docker Compose

![Diagrama de Despliegue](images/diagrama_despliegue.png)

*Diagrama que muestra: Servidor/VM conteniendo Docker Compose con los 4 contenedores (FastAPI, PostgreSQL, Redis, Worker), los 3 volúmenes persistentes (postgres_data, video_uploads, video_processed), y las conexiones entre ellos. Cliente externo conectándose al puerto 80/8000.*

### 6.2 Componentes de Infraestructura

**Contenedores:**
- **FastAPI Container**: Puerto 8000 expuesto, conecta con todos los servicios
- **PostgreSQL Container**: Puerto 5432, con volumen `postgres_data` para persistencia
- **Redis Container**: Puerto 6379, broker de mensajes
- **Celery Worker Container**: Sin puerto expuesto, procesa tareas en background

**Volúmenes Persistentes:**
- **postgres_data**: Almacena datos de PostgreSQL (usuarios, videos, metadatos)
- **video_uploads**: Almacena videos originales subidos por usuarios (`/app/uploads`)
- **video_processed**: Almacena videos procesados por FFmpeg (`/app/processed`)

**Red Docker:**
- Red interna privada entre contenedores
- Solo FastAPI expone puerto al exterior (8000)
- Resolución DNS automática entre contenedores por nombre

---

## 7. Almacenamiento de Archivos

### 7.1 Estructura de Directorios

```
/app/
├── uploads/           # Videos originales
│   └── {user_id}/
│       └── {video_id}.mp4
├── processed/         # Videos procesados
│   └── {video_id}_processed.mp4
└── logos/
    └── anb_logo.png   # Logo para overlay
```

---

## 8. Base de Datos

### 8.1 Esquema de Tablas

**Tabla: users**
- id (UUID, PK)
- email (VARCHAR, UNIQUE)
- password (VARCHAR, hashed con bcrypt)
- first_name, last_name, city, country
- created_at, updated_at

**Relaciones**:
- 1:N con `videos` (un usuario puede subir múltiples videos)
- 1:N con `votes` (un usuario puede votar por múltiples videos)

---

**Tabla: videos**
- id (UUID, PK)
- title (VARCHAR)
- status (VARCHAR: pending/processing/completed/failed)
- original_file_path (VARCHAR)
- processed_file_path (VARCHAR)
- is_published (BOOLEAN, default: false)
- user_id (UUID, FK → users.id)
- created_at, updated_at

**Relaciones**:
- N:1 con `users` (cada video pertenece a un usuario)
- 1:N con `votes` (un video puede recibir múltiples votos)

---

**Tabla: votes** 
- id (UUID, PK)
- user_id (UUID, FK → users.id, NOT NULL)
- video_id (UUID, FK → videos.id, NOT NULL)
- voted_at (TIMESTAMP, default: NOW())
- created_at, updated_at

**Constraints**:
- UNIQUE (user_id, video_id) - Un usuario solo puede votar una vez por video
- ON DELETE CASCADE - Si se elimina usuario o video, se eliminan sus votos

**Relaciones**:
- N:1 con `users` (cada voto pertenece a un usuario)
- N:1 con `videos` (cada voto está asociado a un video)

### 8.2 Diagrama de Relaciones

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   users     │         │   videos    │         │   votes     │
├─────────────┤         ├─────────────┤         ├─────────────┤
│ id (PK)     │1────N→│ user_id(FK) │         │ id (PK)     │
│ email       │         │ id (PK)     │1────N→│ video_id(FK)│
│ password    │         │ title       │         │ user_id(FK) │
│ first_name  │         │ status      │         │ voted_at    │
│ last_name   │         │ is_published│         └─────────────┘
│ city        │         │ ...         │                 ↑
│ country     │         └─────────────┘                 │
└─────────────┘                                         │
      │1                                               N│
      └────────────────────────────────────────────────┘

UNIQUE CONSTRAINT: (user_id, video_id)
```

### 8.3 Índices

```sql
-- Tabla: users
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- Tabla: videos
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_status_published ON videos(status, is_published)
  WHERE status = 'completed' AND is_published = true;

-- Tabla: votes (NUEVOS)
CREATE INDEX idx_votes_user_id ON votes(user_id);
CREATE INDEX idx_votes_video_id ON votes(video_id);
CREATE UNIQUE INDEX idx_votes_unique_user_video ON votes(user_id, video_id);
```

### 8.4 Connection Pooling

**Configuración de PostgreSQL**:
```bash
max_connections = 300
shared_buffers = 256MB
effective_cache_size = 1GB
```

**Configuración de SQLAlchemy (por worker de Gunicorn)**:
```python
pool_size = 10          # Conexiones permanentes
max_overflow = 20       # Conexiones adicionales temporales
pool_timeout = 30       # Timeout esperando conexión
pool_recycle = 3600     # Reciclar cada 1 hora
```

**Cálculo total**:
- 4 workers Gunicorn × 30 conexiones max = 120 conexiones
- Celery workers: ~50 conexiones
- Total: ~170 / 300 disponibles (margen adecuado)

---

## 9. CI/CD Pipeline

### 9.1 GitHub Actions

**Job 1: Tests & Linting**
- Setup Python 3.13
- Install dependencies (Poetry)
- Run flake8 (linting)
- Run black (formatting check)
- Run pytest (tests + coverage)

**Job 2: Build Docker**
- Build Docker image
- Validate docker-compose.yml
- (Futuro) Push to registry

### 9.2 Quality Gates

- Tests deben pasar (40/40)
- Coverage > 75% (actual: 79%)
- No linting errors
- Docker build exitoso

### 9.3 Suite de Pruebas

El proyecto cuenta con una suite completa de **40 tests** que validan toda la funcionalidad del sistema.

#### Cobertura de Código: 79%

**Desglose por módulo:**
- `app/api/routes/auth.py` - **100%** ✅
- `app/api/routes/health.py` - **100%** ✅
- `app/api/routes/public.py` - **98%** ✅
- `app/api/routes/videos.py` - **82%**
- `app/core/security.py` - **74%**
- `app/db/models.py` - **95%** ✅
- `app/schemas/*` - **100%** ✅

#### Tests de Autenticación (15 tests)

**Signup (5 tests)**:
- ✅ Registro exitoso con datos válidos
- ✅ Error al registrar email duplicado
- ✅ Error cuando las contraseñas no coinciden
- ✅ Error con campos faltantes
- ✅ Error con email inválido

**Login (4 tests)**:
- ✅ Login exitoso con credenciales correctas
- ✅ Error con contraseña incorrecta
- ✅ Error con email no registrado
- ✅ Error con campos faltantes

**JWT Token Functions (3 tests)**:
- ✅ Creación de token con expiración personalizada
- ✅ Error al validar token sin claim 'sub'
- ✅ Error al validar token con usuario inexistente

**Protected Endpoints (3 tests)**:
- ✅ Error al acceder sin token (401)
- ✅ Error al acceder con token inválido (401)
- ✅ Error al acceder con header mal formado (401/403)

#### Tests de Gestión de Videos (14 tests)

**Upload de Videos (5 tests)**:
- ✅ Upload exitoso con autenticación válida
- ✅ Error al subir video sin autenticación
- ✅ Error al subir video sin título
- ✅ Error al subir archivo con tipo inválido (no video)
- ✅ Error al intentar subir sin archivo

**Listar Mis Videos (3 tests)**:
- ✅ Listado exitoso de videos del usuario autenticado
- ✅ Error al listar videos sin autenticación
- ✅ Retorna lista vacía cuando no hay videos

**Detalle de Video (3 tests)**:
- ✅ Ver detalle de video propio con éxito
- ✅ Error al intentar ver video de otro usuario
- ✅ Error cuando el video no existe (404)

**Eliminar Video (3 tests)**:
- ✅ Eliminación exitosa de video propio
- ✅ Error al intentar eliminar video de otro usuario
- ✅ Error cuando el video no existe (404)

#### Tests de Endpoints Públicos (9 tests)

**Videos Públicos (2 tests)**:
- ✅ Listar videos publicados correctamente
- ✅ Retorna lista vacía cuando no hay videos públicos

**Sistema de Votación (4 tests)**:
- ✅ Votar por video con autenticación exitosa
- ✅ Error al votar sin autenticación
- ✅ Error al votar múltiples veces por el mismo video
- ✅ Error al votar por video que no existe (404)

**Rankings (3 tests)**:
- ✅ Obtener ranking general de jugadores
- ✅ Obtener ranking filtrado por ciudad
- ✅ Retorna ranking vacío cuando no hay datos

#### Tests de Health Check (2 tests)

- ✅ Health check retorna status "healthy"
- ✅ Health check funciona con conexión a BD

#### Ejecución de Tests

```bash
# Ejecutar todos los tests
docker-compose exec -T api pytest tests/ -v

# Ejecutar con reporte de cobertura
docker-compose exec -T api pytest tests/ --cov=app --cov-report=term

# Ejecutar tests de un módulo específico
docker-compose exec -T api pytest tests/api/test_auth.py -v

# Generar reporte HTML de cobertura
docker-compose exec -T api pytest tests/ --cov=app --cov-report=html
# Luego abrir: htmlcov/index.html
```

#### Resultados de Pruebas

```
====================== test session starts ======================
collected 40 items

tests/api/test_auth.py ...............              [ 37%]
tests/api/test_health.py ..                         [ 42%]
tests/api/test_public.py .........                  [ 65%]
tests/api/test_videos.py ..............             [100%]

====================== 40 passed in 11.58s ======================

Coverage: 79% (404/509 lines covered)
```

### 9.4 Pruebas de Rendimiento y Escalabilidad

El sistema ha sido sometido a pruebas de carga para validar su capacidad de manejar múltiples usuarios concurrentes.

#### Infraestructura de Alto Rendimiento

**Mejoras implementadas para producción:**
1. **Gunicorn** con 4 workers Uvicorn (proceso multi-worker)
2. **Nginx** como reverse proxy con load balancing (algoritmo `least_conn`)
3. **Connection pooling** PostgreSQL (10 base + 20 overflow por worker)
4. **PostgreSQL optimizado** (300 max_connections, 256MB shared_buffers, 1GB effective_cache_size)

---

## 10. Tecnologías Utilizadas

### 10.1 Backend
- **Python 3.13**
- **FastAPI 0.118.x** - Framework web
- **Gunicorn** - WSGI HTTP Server (process manager)
- **Uvicorn** - ASGI server (workers)
- **SQLAlchemy 2.0** - ORM
- **Pydantic v2** - Validación de datos
- **python-jose** - JWT tokens
- **bcrypt** - Hashing de passwords

### 10.2 Infraestructura
- **Nginx** - Reverse proxy y load balancer
- **Docker** - Containerización
- **Docker Compose** - Orquestación de servicios

### 10.3 Base de Datos
- **PostgreSQL 16** - Base de datos relacional
- **psycopg2** - Driver de PostgreSQL
- **Alembic** - Migraciones de BD

### 10.4 Procesamiento Asíncrono
- **Celery** - Task queue
- **Redis 7** - Message broker y cache
- **FFmpeg** - Procesamiento de videos

### 10.5 DevOps y CI/CD
- **Poetry** - Gestión de dependencias
- **GitHub Actions** - CI/CD pipeline
- **pytest** - Framework de testing
- **pytest-cov** - Code coverage

### 10.6 Code Quality
- **flake8** - Linting (PEP 8)
- **black** - Code formatting
- **mypy** - Type checking

### 10.7 Resumen de Stack Tecnológico

```
┌─────────────────────────────────────────────┐
│           Cliente (HTTP/HTTPS)               │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Nginx (Reverse Proxy + Load Balancing)     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Gunicorn + Uvicorn Workers (4 workers)     │
│  ├─ FastAPI (Python 3.13)                   │
│  ├─ SQLAlchemy ORM                           │
│  └─ Pydantic (Validación)                    │
└───┬────────────────────────────┬────────────┘
    │                            │
    │                            │
┌───▼───────────────┐    ┌──────▼──────────┐
│  PostgreSQL 16    │    │   Redis 7       │
│  (Users, Videos,  │    │  (Message       │
│   Votes)          │    │   Broker)       │
└───────────────────┘    └──────┬──────────┘
                                │
                         ┌──────▼──────────┐
                         │  Celery Worker  │
                         │  + FFmpeg       │
                         └─────────────────┘
```

---

## 11. API Endpoints

### 11.1 Endpoints de Autenticación

| Método | Endpoint | Autenticación | Descripción |
|--------|----------|---------------|-------------|
| POST | `/api/auth/signup` | No | Registro de nuevo usuario |
| POST | `/api/auth/login` | No | Login y obtención de JWT token |

### 11.2 Endpoints de Gestión de Videos (Privados)

| Método | Endpoint | Autenticación | Descripción |
|--------|----------|---------------|-------------|
| POST | `/api/videos/upload` | Sí (JWT) | Subir video para procesamiento |
| GET | `/api/videos` | Sí (JWT) | Listar videos del usuario autenticado |
| GET | `/api/videos/{id}` | Sí (JWT) | Ver detalle de un video propio |
| DELETE | `/api/videos/{id}` | Sí (JWT) | Eliminar video (si no tiene votos) |

### 11.3 Endpoints Públicos de Votación ⭐ NUEVOS

| Método | Endpoint | Autenticación | Descripción |
|--------|----------|---------------|-------------|
| GET | `/api/public/videos` | No | Listar videos publicados disponibles para votar |
| POST | `/api/public/videos/{id}/vote` | Sí (JWT) | Votar por un video |
| GET | `/api/public/rankings` | No | Ver ranking de jugadores por votos |

**Parámetros de Query para Rankings**:
- `city` (opcional): Filtrar por ciudad (ej: `?city=Bogotá`)
- `page` (default: 1): Número de página
- `page_size` (default: 20, max: 100): Elementos por página

### 11.4 Endpoint de Monitoreo

| Método | Endpoint | Autenticación | Descripción |
|--------|----------|---------------|-------------|
| GET | `/health` | No | Health check del sistema |

### 11.5 Ejemplo de Request y Response

**Votar por un video**:
```bash
POST /api/public/videos/123e4567-e89b-12d3-a456-426614174000/vote
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response exitosa**:
```json
{
  "message": "Voto registrado exitosamente.",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_votes": 42
}
```

**Obtener rankings**:
```bash
GET /api/public/rankings?city=Bogot%C3%A1&page=1&page_size=10
```

**Response**:
```json
{
  "rankings": [
    {
      "position": 1,
      "username": "Juan Pérez",
      "city": "Bogotá",
      "country": "Colombia",
      "votes": 1530
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 10,
  "total_pages": 15
}
```

---

## 12. Referencias

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [Nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Connection Pooling](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [SQLAlchemy Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
