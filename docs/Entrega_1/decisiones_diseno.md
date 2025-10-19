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
| Operación | Método | Endpoint | Status |
|-----------|--------|----------|--------|
| Crear usuario | POST | `/api/auth/signup` | 201 |
| Login | POST | `/api/auth/login` | 200 |
| Subir video | POST | `/api/videos/upload` | 201 |
| Listar videos del usuario | GET | `/api/videos` | 200 |
| Ver detalle de video | GET | `/api/videos/{id}` | 200 |
| Eliminar video | DELETE | `/api/videos/{id}` | 204 |
| Listar videos públicos | GET | `/api/public/videos` | 200 |
| Votar por video | POST | `/api/public/videos/{id}/vote` | 201 |
| Ver rankings | GET | `/api/public/rankings` | 200 |

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

**Decisión**: Usar pytest con cobertura del 80%+ como objetivo.

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

## 8. Optimizaciones de Base de Datos

**Índices creados**:
```sql
-- Búsqueda de videos por usuario
CREATE INDEX idx_videos_user_id ON videos(user_id);

-- Listados de videos procesados ordenados por fecha
CREATE INDEX idx_videos_status_date ON videos(status, uploaded_at DESC);
```

**Query optimization**:
- **Pagination**: LIMIT/OFFSET para evitar cargar todos los registros
- **Eager loading**: `joinedload()` para evitar N+1 queries
- **Aggregations**: COUNT() en BD, no en Python

---

## 9. Manejo de Errores

### 9.1 Estrategia de Error Handling

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
| **Base de Datos** | PostgreSQL + UUIDs | ACID, relaciones, seguridad |
| **Autenticación** | JWT + Bcrypt | Stateless, escalable, seguro |
| **Procesamiento** | Celery + Redis + FFmpeg | Async, retry logic, completo |
| **API** | REST + Pydantic | Estándar, validación automática |
| **Testing** | pytest + PostgreSQL | Coverage alto, production parity |
| **DevOps** | Docker Compose + GitHub Actions | Reproducibilidad, automatización |
| **Escalabilidad** | Horizontal + Caching | Performance bajo carga |
| **Errores** | HTTP codes + Logging | Debugging y UX claros |

---

## Referencias

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/best-practices/)
- [Celery Design Patterns](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [RESTful API Design](https://restfulapi.net/)
