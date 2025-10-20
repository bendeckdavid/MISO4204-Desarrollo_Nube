# Decisiones de Diseño - ANB Rising Stars Showcase

## 1. Arquitectura General

### 1.1 Patrón de Arquitectura: Microservicios con Procesamiento Asíncrono

**Decisión**: Implementar una arquitectura basada en microservicios con procesamiento asíncrono usando Celery + Redis.

**Justificación**:
- **Escalabilidad**: Permite escalar horizontalmente cada componente de forma independiente
- **Resiliencia**: Si el procesamiento de video falla, no afecta la API REST
- **Performance**: La API responde inmediatamente sin bloquear mientras el video se procesa en background
- **Separación de responsabilidades**: API maneja requests HTTP, workers procesan videos

**Flujo de procesamiento**:
```
1. Usuario sube video → API guarda archivo → Status: "uploaded"
2. API encola tarea en Redis → Retorna 201 inmediatamente
3. Worker consume tarea → Status: "processing"
4. FFmpeg procesa video → Status: "processed" o "failed"
5. Usuario consulta status via GET /api/videos/{id}
```

---

## 2. Base de Datos

### 2.1 PostgreSQL como Base de Datos Principal

**Decisión**: Usar PostgreSQL 16 como sistema de base de datos relacional.

**Justificación**:
- **ACID Compliance**: Garantiza integridad transaccional
- **Soporte UUID nativo**: `UUID` type para IDs distribuidos sin colisiones
- **JSON Support**: `JSONB` para metadatos de videos sin crear tablas adicionales
- **Performance**: Índices B-tree y GiST para queries complejas
- **Relaciones complejas**: User → Videos (1:N)

### 2.2 Uso de UUIDs como Claves Primarias

**Decisión**: Usar `UUID v4` como clave primaria en todas las tablas.

**Justificación**:
- **Seguridad**: No expone el número total de registros (no secuencial)
- **Distribución**: Permite sharding futuro sin colisiones
- **APIs**: URLs más seguras (`/videos/{uuid}` vs `/videos/123`)
- **Performance**: PostgreSQL optimiza UUIDs nativamente

### 2.3 Connection Pooling con SQLAlchemy

**Decisión**: Configurar connection pooling con límites específicos para optimizar uso de conexiones.

**Justificación**:
- **Reutilización de conexiones**: Evita overhead de crear/cerrar conexiones constantemente
- **Límites de recursos**: Previene agotamiento de conexiones disponibles en PostgreSQL
- **Timeout configurado**: Evita deadlocks esperando conexiones indefinidamente
- **Pool recycling**: Recicla conexiones después de 1 hora para prevenir conexiones stale

**Configuración de PostgreSQL**:
```bash
# docker-compose.yml - PostgreSQL
postgres -c max_connections=300 \
         -c shared_buffers=256MB \
         -c effective_cache_size=1GB
```

**Configuración de SQLAlchemy**:
```python
# app/core/config.py
DB_POOL_SIZE: int = 10           # Conexiones permanentes por worker
DB_MAX_OVERFLOW: int = 20        # Conexiones adicionales temporales
DB_POOL_TIMEOUT: int = 30        # Segundos esperando conexión
DB_POOL_RECYCLE: int = 3600      # Reciclar conexión después de 1 hora
```

**Cálculo de conexiones necesarias**:
```
Gunicorn workers: 4
Conexiones por worker: 10 (pool_size) + 20 (max_overflow) = 30
Total API: 4 * 30 = 120 conexiones
Celery workers: ~50 conexiones
PostgreSQL max_connections: 300 (suficiente margen)
```

---

## 3. Autenticación y Seguridad

### 3.1 JWT (JSON Web Tokens) para Autenticación

**Decisión**: Usar JWT con algoritmo HS256 para autenticación stateless.

**Justificación**:
- **Stateless**: No requiere almacenar sesiones en base de datos
- **Escalable**: Funciona en múltiples instancias sin sesiones compartidas
- **Estándar**: Ampliamente soportado por clientes (mobile, web, Postman)
- **Performance**: Validación rápida sin consultar BD

**Estructura del token**:
```json
{
  "sub": "user_uuid",
  "exp": 1760777554
}
```

**Configuración de seguridad**:
- **Expiración**: 7 días configurable via `.env`
- **Algoritmo**: HS256 (simétrico, suficiente para app interna)
- **Secret**: Generado aleatoriamente, nunca commiteado

### 3.2 Bcrypt para Hashing de Passwords

**Decisión**: Usar bcrypt con factor de trabajo 12 para hashear contraseñas.

**Justificación**:
- **Resistente a fuerza bruta**: Computacionalmente costoso
- **Salt automático**: Cada hash incluye salt único
- **Estándar de industria**: Ampliamente testeado y confiable

**Implementación**:
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

---

## 4. Procesamiento de Videos

### 4.1 Celery + Redis para Procesamiento Asíncrono

**Decisión**: Usar Celery como task queue con Redis como message broker.

**Justificación**:
- **Asíncrono**: Usuario recibe respuesta inmediata (201 Created)
- **Retry logic**: Reintentos automáticos si FFmpeg falla
- **Monitoring**: Flower para visualizar tasks
- **Escalable**: Múltiples workers en paralelo

### 4.2 FFmpeg para Transformación de Videos

**Decisión**: Usar FFmpeg para recortar, redimensionar y agregar logos.

**Justificación**:
- **Estándar de industria**: Más completo y confiable
- **Open source**: Sin costos de licencia
- **Flexible**: Soporta todos los formatos y operaciones
- **CLI**: Fácil de integrar desde Python

**Operaciones implementadas**:
```bash
# 1. Recortar a primeros 20 segundos
ffmpeg -i input.mp4 -t 20 -c copy trimmed.mp4

# 2. Redimensionar a 1280x720
ffmpeg -i trimmed.mp4 -vf scale=1280:720 resized.mp4

# 3. Agregar logo ANB en esquina superior derecha
ffmpeg -i resized.mp4 -i logo.png -filter_complex \
  "[1:v]scale=120:60[logo];[0:v][logo]overlay=W-w-10:10" \
  output.mp4
```

### 4.3 Almacenamiento Local de Videos con Volúmenes Docker

**Decisión**: Almacenar videos en sistema de archivos local usando volúmenes compartidos de Docker.

**Justificación**:
- **Simplicidad**: No requiere configurar S3/Cloud Storage para MVP
- **Compartición entre contenedores**: API y Worker acceden a mismos archivos via volumen compartido
- **Paths consistentes**: `/app/videos/uploads/` y `/app/videos/processed/` en ambos contenedores
- **Desarrollo local**: Facilita debugging y testing sin servicios externos

**Estructura de directorios**:
```
/app/videos/
├── uploads/         # Videos originales subidos
│   └── {uuid}.mp4
└── processed/       # Videos procesados por FFmpeg
    └── {uuid}.mp4
```

**Configuración de volúmenes**:
```yaml
# docker-compose.yml
api:
  volumes:
    - .:/app  # Comparte /app entre host y contenedor

worker:
  volumes:
    - .:/app  # Worker accede a mismos archivos que API
```

**Nota de producción**:
> Para producción, migrar a **AWS S3**, **Google Cloud Storage** o **Azure Blob Storage** por:
> - Escalabilidad horizontal (múltiples instancias de API/Worker)
> - Durabilidad (replicación automática)
> - CDN integration (CloudFront, CloudFlare)
> - Costos optimizados para almacenamiento a largo plazo

### 4.4 Validación de Uploads de Video

**Decisión**: Implementar múltiples capas de validación para uploads de video.

**Justificación**:
- **Seguridad**: Prevenir uploads de archivos maliciosos o no-video
- **Estabilidad**: Evitar que archivos grandes saturen sistema
- **UX**: Respuestas rápidas y claras sobre errores de validación
- **Costos**: Limitar procesamiento a archivos válidos reduce uso de CPU/storage

**Validaciones implementadas**:
```python
# 1. Archivo existe
if not file or not file.filename:
    raise HTTPException(400, "No file uploaded")

# 2. Content-Type es video/*
if not file.content_type or not file.content_type.startswith("video/"):
    raise HTTPException(400, "File must be a video format")

# 3. Tamaño máximo: 10MB (configurable)
MAX_VIDEO_SIZE = 10 * 1024 * 1024  # 10 MB
if file.size and file.size > MAX_VIDEO_SIZE:
    raise HTTPException(400, "File size exceeds limit")
```

**Límites configurados**:
- **Aplicación**: `MAX_VIDEO_SIZE = 10MB` (config.py)
- **Nginx**: `client_max_body_size 100M` (permite margen)
- **Timeout**: `client_body_timeout 300s` (5 minutos para uploads lentos)

---

## 5. Diseño de API

### 5.1 RESTful API con Convenciones HTTP

**Decisión**: Seguir principios REST estrictamente.

**Justificación**:
- **Predecible**: Clientes saben qué esperar (GET = lectura, POST = creación)
- **Cacheable**: GET requests pueden cachearse
- **Stateless**: Cada request es independiente
- **Estándar**: Compatible con cualquier cliente HTTP

**Convenciones aplicadas**:

| Operación | Método | Endpoint | Auth | Status |
|-----------|--------|----------|------|--------|
| Health check | GET | `/health` | No | 200 |
| Crear usuario | POST | `/api/auth/signup` | No | 201 |
| Login | POST | `/api/auth/login` | No | 200 |
| Subir video | POST | `/api/videos/upload` | Sí | 201 |
| Listar videos del usuario | GET | `/api/videos` | Sí | 200 |
| Ver detalle de video | GET | `/api/videos/{id}` | Sí | 200 |
| Eliminar video | DELETE | `/api/videos/{id}` | Sí | 200 |
| Listar videos públicos | GET | `/api/public/videos` | No | 200 |
| Votar por video | POST | `/api/public/videos/{id}/vote` | Sí | 200 |
| Ver rankings | GET | `/api/public/rankings` | No | 200 |

### 5.2 Pydantic para Validación de Datos

**Decisión**: Usar Pydantic schemas para validación automática.

**Justificación**:
- **Type safety**: Errores de tipo detectados automáticamente
- **Documentación automática**: OpenAPI/Swagger generado
- **Validación robusta**: Email, longitud, regex, custom validators
- **Performance**: Validación en C (Pydantic v2)

**Ejemplo**:
```python
class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr  # Validación de formato
    password1: str = Field(min_length=8)
    password2: str
    city: str
    country: str

    @validator('password2')
    def passwords_match(cls, v, values):
        if 'password1' in values and v != values['password1']:
            raise ValueError('Passwords do not match')
        return v
```

---

## 6. Testing

### 6.1 Pytest para Testing Automatizado

**Decisión**: Usar pytest con cobertura.

**Justificación**:
- **Fixtures**: Reutilización de setup (database, client, users)
- **Parametrización**: Múltiples casos de prueba en un solo test
- **Coverage**: Identificar código no testeado
- **CI/CD**: Integración con GitHub Actions

**Estructura de tests**:
```
tests/
├── conftest.py          # Fixtures compartidos
├── api/
│   ├── test_auth.py     # 13 tests (signup, login, protected)
│   └── test_videos.py   # Tests de videos
└── workers/
    └── test_video_processing.py
```

**Coverage actual**: 88%

### 6.2 PostgreSQL para Tests

**Decisión**: Usar PostgreSQL también en tests, no SQLite.

**Justificación**:
- **Production parity**: Detecta bugs específicos de PostgreSQL
- **UUID support**: SQLite no soporta UUID nativamente
- **JSON queries**: JSONB queries solo funcionan en PostgreSQL
- **Transactions**: Comportamiento de locking idéntico

**Implementación**:
```python
# tests/conftest.py
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fastapi_user:fastapi_password@localhost:5432/fastapi_db"
)
```

---

## 7. DevOps y CI/CD

### 7.1 Docker Compose para Desarrollo y Producción

**Decisión**: Usar Docker Compose para orquestar todos los servicios.

**Justificación**:
- **Reproducibilidad**: Mismo entorno en dev, test y prod
- **Aislamiento**: Cada servicio en su contenedor
- **Networking**: Red privada entre contenedores
- **Healthchecks**: Dependencias solo inician cuando servicios están ready

**Servicios definidos**:
```yaml
services:
  db:        # PostgreSQL 16
  redis:     # Redis 7 (message broker)
  api:       # FastAPI application
  worker:    # Celery worker
```

### 7.2 GitHub Actions para CI/CD

**Decisión**: Pipeline CI/CD con 2 jobs: Test + Build.

**Justificación**:
- **Automatización**: Tests en cada push/PR
- **Quality gates**: No merge si tests fallan
- **Build validation**: Docker image se construye correctamente
- **Free**: GitHub Actions gratis para repos públicos

**Pipeline**:
```yaml
Job 1: Test & Lint
  - Setup Python 3.13
  - Install Poetry dependencies
  - Run flake8 (linting)
  - Run black (formatting)
  - Run pytest (coverage 88%)
  - Upload coverage report

Job 2: Build Docker
  - Build Docker image
  - Validate docker-compose.yml
```

**Herramientas de calidad**:
- **flake8**: PEP 8 compliance
- **black**: Code formatting (line-length 100)
- **mypy**: Type checking
- **pytest-cov**: Code coverage

### 7.3 SonarQube para Análisis de Calidad

**Decisión**: Integrar SonarQube para análisis estático (pendiente de permisos).

**Justificación**:
- **Code smells**: Detecta patrones problemáticos
- **Security vulnerabilities**: OWASP Top 10
- **Technical debt**: Cuantifica deuda técnica
- **Coverage tracking**: Monitorea cobertura en el tiempo

---

## 7.5 Nginx como Reverse Proxy

**Decisión**: Usar Nginx como reverse proxy delante de Gunicorn/FastAPI.

**Justificación**:
- **Performance**: Nginx maneja conexiones concurrentes más eficientemente que Python
- **Load balancing**: Algoritmo `least_conn` distribuye requests al worker menos ocupado
- **Buffer de uploads**: Nginx bufferea archivos grandes antes de pasarlos a FastAPI
- **Timeouts configurables**: 300s para uploads de videos grandes
- **Health checks**: Endpoint `/health` sin logging para monitoreo

**Configuración clave**:
```nginx
upstream fastapi_backend {
    least_conn;  # Enrutar a worker con menos conexiones
    server api:8000 max_fails=3 fail_timeout=30s;
}

server {
    client_max_body_size 100M;  # Permite videos de hasta 100MB
    client_body_timeout 300s;   # 5 minutos para uploads

    location / {
        proxy_pass http://fastapi_backend;
        proxy_read_timeout 300s;  # Timeout para procesamiento largo
    }
}
```

### 7.6 Gunicorn + Uvicorn Workers para Concurrencia

**Decisión**: Usar Gunicorn como process manager con Uvicorn workers.

**Justificación**:
- **Múltiples procesos**: 4 workers para aprovechar múltiples CPUs
- **Async I/O**: Uvicorn workers soportan `async/await` de FastAPI
- **Graceful restarts**: Gunicorn reemplaza workers sin downtime
- **Worker recycling**: `max-requests` recicla workers para prevenir memory leaks
- **Keep-alive**: Reutilización de conexiones HTTP reduce overhead

**Comando de inicio**:
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100
```

**Parámetros clave**:
- **workers=4**: 1 worker por CPU core (típico para I/O-bound apps)
- **timeout=120**: 2 minutos para requests largos (uploads)
- **max-requests=1000**: Recicla worker después de 1000 requests (previene leaks)
- **max-requests-jitter=100**: Randomiza reciclaje para evitar reinicio simultáneo

---

## 8. Sistema de Votación

### 8.1 Modelo de Votos con Restricción Única

**Decisión**: Implementar sistema de votación con tabla intermedia `votes` y constraint único `(user_id, video_id)`.

**Justificación**:
- **Integridad referencial**: Foreign keys garantizan que votos solo existen para usuarios y videos válidos
- **Prevención de duplicados**: Constraint único evita que un usuario vote múltiples veces por el mismo video
- **Escalabilidad**: Tabla separada permite contar votos eficientemente sin modificar tabla de videos
- **Auditabilidad**: Cada voto registra timestamp (`voted_at`) para análisis temporal

**Implementación**:
```python
class Vote(Base):
    __tablename__ = "votes"
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    video_id = Column(UUID, ForeignKey("videos.id"), nullable=False)
    voted_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_user_video_vote"),
    )
```

### 8.2 Endpoints Públicos para Votación

**Decisión**: Crear rutas públicas (`/api/public/*`) que requieren autenticación pero son accesibles a todos los usuarios.

**Justificación**:
- **Separación de responsabilidades**: Rutas privadas (`/api/videos`) para gestión personal vs rutas públicas para interacción social
- **Seguridad**: Usuarios autenticados pueden votar pero no pueden ver quién votó qué
- **UX**: Listados públicos no muestran videos privados (solo `is_published=true` y `status=completed`)

**Endpoints implementados**:
```
GET  /api/public/videos          # Listar videos disponibles para votación
POST /api/public/videos/{id}/vote # Votar por un video
GET  /api/public/rankings         # Ver ranking de jugadores por votos
```

### 8.3 Agregación de Votos con SQLAlchemy

**Decisión**: Usar `func.count()` de SQLAlchemy para contar votos en queries, no cargar todos los votos en memoria.

**Justificación**:
- **Performance**: COUNT en base de datos es O(1) con índices, en Python sería O(n)
- **Memoria**: No carga relación `votes` completa, solo el conteo
- **Escalabilidad**: Funciona con millones de votos sin problemas

**Query de ranking**:
```python
ranking = (
    db.query(
        User.first_name,
        User.last_name,
        User.city,
        User.country,
        func.count(Vote.id).label("total_votes")
    )
    .join(Video, User.id == Video.user_id)
    .join(Vote, Video.id == Vote.video_id)
    .group_by(User.id)
    .order_by(func.count(Vote.id).desc())
    .limit(20)
    .all()
)
```

### 8.4 Filtros en Ranking: City-Based Rankings

**Decisión**: Implementar filtros opcionales en el endpoint de rankings (ej: `?city=Bogotá`).

**Justificación**:
- **Localización**: Permite ver rankings locales (ej: mejores jugadores de Bogotá)
- **Competencia justa**: Jugadores compiten en su región
- **Flexibilidad**: Mismo endpoint sirve rankings globales y locales

**Implementación**:
```python
@router.get("/rankings")
def get_rankings(city: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(...).join(...)
    if city:
        query = query.filter(User.city == city)
    return query.all()
```

### 8.5 Prevención de Auto-Votación

**Decisión**: Usuario NO puede votar por sus propios videos (validación en backend).

**Justificación**:
- **Integridad del sistema**: Previene manipulación artificial de rankings
- **Competencia justa**: Votos deben ser genuinos de otros usuarios
- **UX**: Videos propios no aparecen en listado público de votación

**Validación**:
```python
@router.post("/videos/{video_id}/vote")
def vote_video(video_id: str, current_user: User, db: Session):
    video = db.query(Video).filter(Video.id == video_id).first()

    # Validar que no es su propio video
    if video.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="No puedes votar por tus propios videos"
        )

    # Crear voto (UniqueConstraint previene duplicados)
    vote = Vote(user_id=current_user.id, video_id=video_id)
    db.add(vote)
    db.commit()
```

### 8.6 Protección contra Eliminación de Videos con Votos

**Decisión**: Videos que han recibido votos NO pueden ser eliminados por sus propietarios.

**Justificación**:
- **Integridad de rankings**: Prevenir manipulación eliminando videos competidores después de recibir votos
- **Auditoría**: Mantener registro histórico de videos que participaron en votaciones
- **UX del votante**: Frustración si un video votado desaparece
- **Datos analíticos**: Preservar datos para análisis de comportamiento de usuarios

**Implementación**:
```python
@router.delete("/videos/{video_id}")
def delete_video(video_id: str, current_user: User, db: Session):
    # Verificar si el video tiene votos
    vote_count = db.query(Vote).filter(Vote.video_id == video_id).count()
    if vote_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete video: it has {vote_count} vote(s)"
        )
    # Continuar con eliminación...
```

### 8.7 Paginación en Rankings

**Decisión**: Implementar paginación con `page` y `page_size` en lugar de `skip`/`limit`.

**Justificación**:
- **UX más intuitiva**: Usuarios piensan en "página 1, 2, 3" no en "skip 20"
- **Consistencia con estándares**: APIs populares (GitHub, Twitter) usan paginación por página
- **Metadata útil**: Retornar `total_pages`, `total`, `page`, `page_size` ayuda a frontends
- **Performance**: Límite máximo de 100 items por página previene abuse

**Implementación**:
```python
@router.get("/rankings")
def get_rankings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * page_size
    total = query.count()
    total_pages = math.ceil(total / page_size)
    results = query.offset(skip).limit(page_size).all()

    return {
        "rankings": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }
```

### 8.8 Rankings Públicos sin Autenticación

**Decisión**: El endpoint `/api/public/rankings` NO requiere autenticación.

**Justificación**:
- **Accesibilidad**: Permite compartir rankings públicamente (SEO, redes sociales)
- **Marketing**: Visitantes no autenticados pueden ver competencia y registrarse
- **Performance**: Reduce carga en sistema de autenticación
- **Caching**: Más fácil cachear respuestas sin considerar usuarios individuales

**Nota de seguridad**:
```python
# Otros endpoints públicos SÍ requieren auth (para votar)
@router.post("/videos/{id}/vote")  # Requires auth
async def vote_video(current_user: User = Depends(get_current_user))

# Pero rankings son públicos
@router.get("/rankings")  # No auth required
def get_rankings(db: Session = Depends(get_db))
```

---

## 9. Optimizaciones de Base de Datos

**Índices creados**:
```sql
-- Búsqueda de videos por usuario
CREATE INDEX idx_videos_user_id ON videos(user_id);

-- Listados de videos procesados y publicados
CREATE INDEX idx_videos_status_published ON videos(status, is_published)
WHERE status = 'completed' AND is_published = true;

-- Búsqueda de votos por usuario
CREATE INDEX idx_votes_user_id ON votes(user_id);

-- Contar votos por video (para rankings)
CREATE INDEX idx_votes_video_id ON votes(video_id);

-- Prevenir votos duplicados
CREATE UNIQUE INDEX idx_votes_unique_user_video ON votes(user_id, video_id);
```

**Query optimization**:
- **Pagination**: LIMIT/OFFSET para evitar cargar todos los registros
- **Eager loading**: `joinedload()` para evitar N+1 queries
- **Aggregations**: COUNT() en BD, no en Python
- **Filtros selectivos**: Índices compuestos para queries con múltiples condiciones

---

## 10. Manejo de Errores

### 10.1 Estrategia de Error Handling

**Decisión**: Errores descriptivos con códigos HTTP apropiados.

**Niveles de error**:
1. **Validación (422)**: Pydantic maneja automáticamente
2. **Negocio (400)**: Errores de lógica de negocio (ej: email duplicado)
3. **Autorización (401/403)**: Token inválido o permisos insuficientes
4. **No encontrado (404)**: Recurso no existe
5. **Server error (500)**: Loggear y retornar mensaje genérico

**Ejemplo**:
```python
@router.delete("/videos/{video_id}")
def delete_video(video_id: str, current_user: User, db: Session):
    # Check si video existe
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")

    # Check si es el propietario
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para eliminar este video"
        )

    # Eliminar video
    db.delete(video)
    db.commit()
    return {"message": "Video eliminado exitosamente"}
```

---

## Resumen de Decisiones Clave

| Área | Decisión | Justificación Principal |
|------|----------|------------------------|
| **Arquitectura** | Microservicios + Async | Escalabilidad y resiliencia |
| **Base de Datos** | PostgreSQL + UUIDs + Connection Pooling | ACID, relaciones, seguridad, performance |
| **Autenticación** | JWT + Bcrypt | Stateless, escalable, seguro |
| **Procesamiento** | Celery + Redis + FFmpeg | Async, retry logic, completo |
| **Almacenamiento** | Sistema de archivos local + Docker volumes | Simplicidad MVP, compartición entre contenedores |
| **Infraestructura** | Nginx + Gunicorn + Uvicorn Workers | Load balancing, concurrencia, async I/O |
| **API** | REST + Pydantic | Estándar, validación automática |
| **Votación** | Tabla intermedia + Constraint único | Integridad, prevención duplicados |
| **Rankings** | Agregación SQL + Paginación + Filtros | Performance, UX, flexibilidad |
| **Seguridad Videos** | Validación multi-capa + Límites tamaño | Prevención abuse, estabilidad |
| **Protección Datos** | No eliminación con votos + Auditoría | Integridad rankings, datos históricos |
| **Testing** | pytest + PostgreSQL | Coverage alto, production parity |
| **DevOps** | Docker Compose + GitHub Actions + Health checks | Reproducibilidad, automatización, monitoreo |
| **Escalabilidad** | Pool connections + Worker recycling | Gestión recursos, prevención leaks |
| **Errores** | HTTP codes + Logging | Debugging y UX claros |

---

## Referencias

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/best-practices/)
- [Celery Design Patterns](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [RESTful API Design](https://restfulapi.net/)
- [The Twelve-Factor App](https://12factor.net/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [Nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
