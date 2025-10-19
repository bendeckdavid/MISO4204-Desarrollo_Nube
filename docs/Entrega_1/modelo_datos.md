# Modelo de Datos - ANB Rising Stars Showcase

## Diagrama Entidad-Relación (ERD)

[AGREGAR DIAGRAMA]

---

## Descripción de Entidades

### 1. USER (Usuarios/Jugadores)

Almacena la información de los jugadores que suben videos.

**Campos**:

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | UUID | PRIMARY KEY | Identificador único del usuario |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Email del usuario (login) |
| `password` | VARCHAR(255) | NOT NULL | Contraseña hasheada con bcrypt |
| `first_name` | VARCHAR(100) | NOT NULL | Nombre del jugador |
| `last_name` | VARCHAR(100) | NOT NULL | Apellido del jugador |
| `city` | VARCHAR(100) | NOT NULL | Ciudad de origen |
| `country` | VARCHAR(100) | NOT NULL | País de origen |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Fecha de registro |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Última actualización |

**Reglas de negocio**:
- El email debe ser único en el sistema
- Las contraseñas se hashean con bcrypt (factor 12) antes de almacenar
- Un usuario puede subir múltiples videos

---

### 2. VIDEO (Videos)

Almacena información sobre los videos subidos por los jugadores.

**Campos**:

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | UUID | PRIMARY KEY | Identificador único del video |
| `title` | VARCHAR(255) | NOT NULL | Título del video |
| `description` | TEXT | NULL | Descripción del video |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'uploaded' | Estado del procesamiento |
| `original_url` | VARCHAR(500) | NOT NULL | Path o URL del video original |
| `processed_url` | VARCHAR(500) | NULL | Path o URL del video procesado |
| `duration_seconds` | INTEGER | NULL | Duración del video en segundos |
| `user_id` | UUID | FOREIGN KEY, NOT NULL, INDEX | Referencia al usuario que subió el video |
| `uploaded_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Fecha de subida |
| `processed_at` | TIMESTAMP | NULL | Fecha de finalización del procesamiento |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Fecha de creación del registro |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Última actualización |

**Estados posibles** (`status`):
- `uploaded`: Video subido, esperando procesamiento
- `processing`: Video siendo procesado por Celery worker
- `processed`: Video procesado exitosamente, disponible para visualización
- `failed`: Error en el procesamiento

**Reglas de negocio**:
- Cada video pertenece a un único usuario (`user_id`)
- Solo los videos en estado `processed` aparecen en listados públicos
- Los videos pueden ser eliminados solo por su propietario

**Procesamiento con FFmpeg**:
Cuando un video se sube, el worker de Celery ejecuta:
1. **Recortar**: Primeros 20 segundos (`-t 20`)
2. **Redimensionar**: 1280x720 (`scale=1280:720`)
3. **Logo**: Agregar logo ANB en esquina superior derecha

---

## Relaciones

### USER → VIDEO (1:N)
- Un usuario puede subir **múltiples videos**
- Cada video pertenece a **un solo usuario**
- Relación: `VIDEO.user_id` → `USER.id`
- ON DELETE: CASCADE (si se elimina un usuario, se eliminan sus videos)

---

## Índices y Optimizaciones

### Índices Principales

```sql
-- Índice único en email para login rápido
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- Índice en user_id para buscar videos de un usuario
CREATE INDEX idx_videos_user_id ON videos(user_id);

-- Índice compuesto para listar videos procesados ordenados por fecha
CREATE INDEX idx_videos_status_date ON videos(status, uploaded_at DESC)
WHERE status = 'processed';
```

## Definición en SQLAlchemy

```python
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="uploaded")
    original_url = Column(String(500), nullable=False)
    processed_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación
    user = relationship("User", back_populates="videos")
```
