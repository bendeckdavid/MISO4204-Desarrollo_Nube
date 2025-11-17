# ANB Rising Stars Showcase API - Entrega 4

API para la gestión de videos de artistas emergentes con sistema de votación y rankings. **Entrega 4** implementa una arquitectura escalable en AWS con **Amazon SQS**, **Worker Auto Scaling**, **Application Load Balancer**, **Amazon S3** y **CloudFormation**.

**Proyecto:** MISO4204 - Desarrollo en la Nube
**Universidad:** Universidad de los Andes

---

## 🎥 Video de Sustentación

**Link del video:** [Ver video en OneDrive](https://uniandes-my.sharepoint.com/:v:/g/personal/o_saraza_uniandes_edu_co/IQDnxFXL5NtzQJ79GgJUBJSfAS7hlRmrhBHIYk0hBOVdXeU?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=PwxnRx)

> Video demostrativo del funcionamiento de la aplicación desplegada en AWS con Auto Scaling, Amazon SQS y Worker Auto Scaling basado en profundidad de cola.

---

## 📊 Arquitectura de Entrega 4

### Arquitectura Escalable con Amazon SQS y Worker Auto Scaling

```
                         Internet
                             ↓
                 ┌───────────────────────┐
                 │ Application Load      │
                 │ Balancer (ALB)        │
                 └───────────┬───────────┘
                             │
             ┌───────────────┼───────────────┐
             │    Auto Scaling Group         │
             │  (1-3 instancias t3.small)    │
             │                               │
             │  ┌──────┐  ┌──────┐  ┌──────┐│
             │  │ Web  │  │ Web  │  │ Web  ││
             │  │  API │  │  API │  │  API ││
             │  └──┬───┘  └──┬───┘  └──┬───┘│
             └─────┼─────────┼─────────┼─────┘
                   │         │         │
                   └─────────┼─────────┘
                             │
                   ┌─────────▼─────────┐
                   │   Amazon SQS      │
                   │ Processing Queue  │
                   └─────────┬─────────┘
                             │
                   ┌─────────▼─────────┐
                   │ Dead Letter Queue │
                   │      (DLQ)        │
                   └───────────────────┘
                             │
             ┌───────────────▼───────────────┐
             │  Worker Auto Scaling Group    │
             │  (1-3 instancias t3.small)    │
             │  Target: 5 msgs/worker        │
             │                               │
             │  ┌──────┐  ┌──────┐  ┌──────┐│
             │  │Worker│  │Worker│  │Worker││
             │  │ SQS  │  │ SQS  │  │ SQS  ││
             │  └──┬───┘  └──┬───┘  └──┬───┘│
             └─────┼─────────┼─────────┼─────┘
                   │         │         │
                   └─────────┼─────────┘
                             │
         ┌───────────────────┼───────────────┐
         │                   ↓               │
         │      ┌─────────┐    ┌──────────┐ │
         │      │   RDS   │    │ S3 Bucket│ │
         │      │Postgres │    │  Videos  │ │
         │      └─────────┘    └──────────┘ │
         └─────────────────────────────────────┘
```

### Componentes Principales

| Componente | Descripción | Tipo de Instancia |
|------------|-------------|-------------------|
| **Application Load Balancer** | Distribuye tráfico HTTP/HTTPS entre instancias web | - |
| **Web Auto Scaling Group** | Escala automáticamente de 1 a 3 instancias según CPU | t3.small (Multi-AZ) |
| **Web Servers** | FastAPI + Gunicorn + Nginx | t3.small |
| **Amazon SQS** | Cola de mensajes administrada para procesamiento asíncrono | Managed Service ✨ |
| **Dead Letter Queue (DLQ)** | Cola para mensajes fallidos (max 3 intentos) | Managed Service |
| **Worker Auto Scaling Group** | Escala de 1 a 3 workers según profundidad de cola SQS | t3.small (Multi-AZ) ✨ |
| **SQS Workers** | Procesamiento de videos con moviepy | t3.small |
| **Amazon RDS** | PostgreSQL 16 administrado | db.t3.micro |
| **Amazon S3** | Almacenamiento escalable para videos | - |
| **VPC Multi-AZ** | Red privada en 2 zonas de disponibilidad | 10.0.0.0/16 |

### Mejoras vs Entregas Anteriores

| Aspecto | Entrega 3 | Entrega 4 ✅ |
|---------|-----------|-------------|
| **Cola de Mensajes** | Redis (single instance) | **Amazon SQS** (managed, HA) |
| **Workers** | Celery (fixed capacity) | **Worker ASG** (1-3, auto scaling) |
| **Escalamiento Workers** | Manual | **Automático** (basado en queue depth) |
| **Resiliencia** | Redis SPOF | SQS + DLQ (3 reintentos) |
| **Disponibilidad** | Single-AZ | Multi-AZ |
| **Despliegue** | CloudFormation (IaC) | CloudFormation (IaC) |
| **Almacenamiento** | Amazon S3 | Amazon S3 |
| **Capacidad probada** | 150 usuarios concurrentes | **150+ usuarios con mejor procesamiento** |

### Novedades de Entrega 4 🆕

1. **Amazon SQS**: Reemplazo de Redis por cola de mensajes administrada
2. **Worker Auto Scaling**: Workers escalan automáticamente según profundidad de cola
3. **Dead Letter Queue**: Manejo robusto de errores con 3 reintentos automáticos
4. **Long Polling**: 20 segundos para reducir llamadas vacías a SQS
5. **Graceful Shutdown**: Manejo de señales SIGTERM/SIGINT en workers
6. **CloudWatch Metrics**: Monitoreo de profundidad de cola y actividad de workers

---

## 📖 Documentación de Entrega 4

### Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| **[Arquitectura AWS SQS](docs/Entrega_4/arquitectura_aws.md)** | Arquitectura escalable con SQS:<br>• Amazon SQS para procesamiento asíncrono<br>• Worker Auto Scaling Group (1-3 instancias)<br>• Dead Letter Queue para reintentos<br>• Application Load Balancer<br>• Amazon S3 para videos<br>• Multi-AZ para alta disponibilidad<br>• Diagramas de flujo y arquitectura |
| **[Pruebas de Carga](capacity-planning/pruebas_de_carga_entrega4.md)** | Pruebas de capacidad con k6 y scripts bash:<br>• **Escenario 1:** Capa Web - Validación de capacidad con SQS<br>• **Escenario 2:** Worker Auto Scaling - Escalado 1→3 workers<br>• Análisis de Auto Scaling bajo carga<br>• Comparación con Entrega 3<br>• Métricas de profundidad de cola SQS<br>• Recomendaciones de escalabilidad |
| **[Guía de Despliegue CloudFormation](docs/Entrega_4/aws_deployment.md)** | Despliegue automatizado con CloudFormation:<br>• Stack con SQS y Worker ASG<br>• Configuración de Auto Scaling basado en queue<br>• Variables de entorno y secretos<br>• Troubleshooting y validación<br>• Scripts de apoyo para pruebas |
| **[Reporte SonarQube](docs/Entrega_4/reporte_sonarqube.md)** | Análisis de calidad actualizado:<br>• Quality Gate: **PASSED**<br>• 0 bugs, 0 vulnerabilidades<br>• Coverage: **99.9%** (753/753 líneas)<br>• 152 tests pasando<br>• Issues de complejidad cognitiva resueltos<br>• Código refactorizado para mejor mantenibilidad |

### Infraestructura como Código

- **[infrastructure.yaml](docs/Entrega_4/deployment/cloudformation/infrastructure.yaml)** - Template CloudFormation con:
  - VPC Multi-AZ (10.0.0.0/16)
  - Application Load Balancer
  - Web Auto Scaling Group (1-3 instancias)
  - **Amazon SQS Queue** con DLQ ✨
  - **Worker Auto Scaling Group** (1-3 instancias) ✨
  - **Target Tracking Policy** (5 msgs/worker) ✨
  - Amazon RDS PostgreSQL
  - S3 Bucket para videos
  - Security Groups y IAM Roles
  - CloudWatch Logs y Métricas

### Scripts de Pruebas de Carga

Ubicados en [`capacity-planning/scripts-entrega4/`](capacity-planning/scripts-entrega4/):

| Script | Descripción |
|--------|-------------|
| **[setup_crear_usuarios_prueba.sh](capacity-planning/scripts-entrega4/setup_crear_usuarios_prueba.sh)** | Crea 5 usuarios de prueba (test1-5@anb.com) |
| **[test_escenario1_capa_web.js](capacity-planning/scripts-entrega4/test_escenario1_capa_web.js)** | Test k6 para validar capa web con SQS |
| **[test_escenario2_worker_autoscaling.sh](capacity-planning/scripts-entrega4/test_escenario2_worker_autoscaling.sh)** | Test bash para demostrar Worker Auto Scaling |
| **[upload_videos_python.py](capacity-planning/scripts-entrega4/upload_videos_python.py)** | Script Python para subir múltiples videos |
| **[README.md](capacity-planning/scripts-entrega4/README.md)** | Guía completa de uso de scripts |

---

## 🚀 Prueba Local con Docker Compose

Aunque la arquitectura principal está en AWS con SQS, puedes probar la aplicación localmente con Docker Compose (versión simplificada).

### Prerrequisitos

- Docker >= 20.10
- Docker Compose >= 2.0
- 8GB RAM disponible
- 10GB espacio en disco

### Inicio Rápido

```bash
# 1. Clonar el repositorio
git clone https://github.com/bendeckdavid/MISO4204-Desarrollo_Nube.git
cd MISO4204-Desarrollo_Nube

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env si es necesario

# 3. Reconstruir imágenes
docker-compose down -v
docker-compose build --no-cache

# 4. Iniciar servicios
docker-compose up -d

# 5. Esperar ~30 segundos para que todos los servicios estén listos
sleep 30

# 6. Verificar estado
docker-compose ps
```

### Servicios Locales

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **API** | - | FastAPI (4 workers Gunicorn) |
| **Nginx** | 8080 | Reverse proxy y load balancer |
| **PostgreSQL** | 5433 | Base de datos |
| **Redis** | 6380 | Message broker (solo local, AWS usa SQS) |
| **Worker** | - | Worker para procesamiento de videos (local) |

> **Nota:** En local se usa Redis por simplicidad, pero en AWS se usa Amazon SQS.

### Verificar Instalación

```bash
# Health check
curl http://localhost:8080/health

# Respuesta esperada:
# {"status":"healthy","version":"1.0.0"}
```

### Documentación Interactiva

- **API Base URL**: http://localhost:8080
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### Comandos Útiles

```bash
# Ver logs
docker-compose logs -f api
docker-compose logs -f worker

# Reiniciar servicios
docker-compose restart api worker

# Detener todo
docker-compose down

# Limpiar todo (incluye volúmenes)
docker-compose down -v
```

---

## 🔌 API Endpoints

### Autenticación

```bash
# Registro de usuario
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

# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "artist@example.com",
    "password": "SecurePass123!"
  }'
```

### Gestión de Videos (requiere JWT)

```bash
# Guardar token
export TOKEN="tu_access_token_aqui"

# Subir video (entra a SQS en AWS)
curl -X POST http://localhost:8080/api/videos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/ruta/a/tu/video.mp4" \
  -F "title=Mi Video Musical" \
  -F "description=Una presentación increíble"

# Listar mis videos
curl -X GET http://localhost:8080/api/videos/ \
  -H "Authorization: Bearer $TOKEN"

# Ver detalles de un video
curl -X GET http://localhost:8080/api/videos/{video_id} \
  -H "Authorization: Bearer $TOKEN"

# Eliminar video
curl -X DELETE http://localhost:8080/api/videos/{video_id} \
  -H "Authorization: Bearer $TOKEN"
```

### Endpoints Públicos

```bash
# Listar videos públicos
curl "http://localhost:8080/api/public/videos?page=1&page_size=10"

# Votar por un video (requiere JWT)
curl -X POST http://localhost:8080/api/public/videos/{video_id}/vote \
  -H "Authorization: Bearer $TOKEN"

# Ver ranking
curl "http://localhost:8080/api/public/rankings?page=1&page_size=20"
```

---

## 🧪 Ejecutar Tests

```bash
# Todos los tests
poetry run pytest tests/ -v

# Con reporte de cobertura
poetry run pytest tests/ --cov=app --cov-report=term --cov-report=html

# Tests específicos
poetry run pytest tests/api/test_videos.py -v
poetry run pytest tests/worker/test_sqs_worker.py -v

# Generar coverage.xml para SonarQube
poetry run pytest tests/ --cov=app --cov-report=xml
```

### Linters y Formateo

```bash
# Ejecutar todos los linters
poetry run flake8 app tests
poetry run black --check app tests
poetry run isort --check-only app tests

# Formatear código
poetry run black app tests
poetry run isort app tests
```

### Cobertura de Tests

- **Cobertura actual:** 99.9% (753/753 líneas)
- **Tests totales:** 152 tests pasando
- **Suites:**
  - Autenticación (15 tests)
  - Videos API (35 tests)
  - Videos Extended (2 tests)
  - Endpoints Públicos (10 tests)
  - Health Check (2 tests)
  - Security (6 tests)
  - Storage/S3 (33 tests)
  - Database (7 tests)
  - Schemas (4 tests)
  - Queue/SQS (24 tests) ✨
  - Worker SQS (6 tests) ✨
  - Worker Videos (19 tests) ✨

---

## 📊 Resultados de Pruebas de Carga (AWS con SQS)

### Escenario 1: Capa Web con SQS

- **Arquitectura:** SQS en lugar de Redis
- **Usuarios concurrentes:** Hasta 150 VUs
- **Resultado:** Mantiene capacidad similar a Entrega 3
- **Mejora:** Mayor estabilidad al usar servicio administrado (SQS)
- **Tasa de éxito:** >80%

**Conclusión:** La migración a SQS no afecta negativamente el rendimiento de la capa web y mejora la resiliencia del sistema.

### Escenario 2: Worker Auto Scaling ✨

- **Estado inicial:** 1 worker
- **Videos subidos:** 12 videos (genera 12 mensajes en SQS)
- **Profundidad máxima de cola:** 12 mensajes
- **Escalado observado:** 1 → 2 → 3 workers
- **Target tracking:** 5 mensajes/worker
- **Tiempo de escalado:** ~2-3 minutos (cooldown de 300s)
- **Resultado:** **Auto Scaling EXITOSO** ✅

**Métricas clave:**
- Threshold alcanzado: 12 msgs > 5 msgs/worker
- Workers escalaron correctamente de 1 a 3
- Cola procesada completamente
- Scale-down automático a 1 worker al terminar

**Conclusión:** El Worker Auto Scaling basado en profundidad de cola SQS funciona correctamente y permite procesar cargas variables de trabajo de forma eficiente.

### Comparación con Entrega 3

| Métrica | Entrega 3 (Redis) | Entrega 4 (SQS) | Mejora |
|---------|-------------------|-----------------|--------|
| Cola de mensajes | Redis (single instance) | Amazon SQS (HA) | **Managed service** |
| Escalabilidad workers | Manual/fija | Automática (1-3) | **Dinámica** |
| Resiliencia | SPOF | DLQ + 3 reintentos | **Mayor** |
| Disponibilidad | Single-AZ | Multi-AZ | **Alta** |
| Capacidad web | 150 VUs | 150+ VUs | **Mantenida** |

---

## 🏗️ Stack Tecnológico

### Backend
- **FastAPI** 0.118+ - Framework moderno para APIs
- **Python** 3.12 - Lenguaje de programación
- **Gunicorn + Uvicorn** - Servidor ASGI con 4 workers
- **SQLAlchemy** 2.0+ - ORM para PostgreSQL
- **Pydantic** 2.5+ - Validación de datos

### Procesamiento Asíncrono ✨ NUEVO
- **Amazon SQS** - Cola de mensajes administrada
- **boto3** - SDK de AWS para Python
- **moviepy** 2.2+ - Procesamiento de videos (trim, resize, watermark)
- **Long Polling** - 20 segundos para eficiencia

### Almacenamiento
- **PostgreSQL** 16 - Base de datos relacional (RDS)
- **Amazon S3** - Almacenamiento de videos
- **boto3** - SDK de AWS para Python

### Infraestructura AWS
- **CloudFormation** - Infraestructura como código
- **EC2** t3.small - Instancias de cómputo
- **Application Load Balancer** - Distribución de carga
- **Auto Scaling Group** - Escalado automático (Web + Workers)
- **Amazon SQS** - Cola de mensajes ✨
- **Dead Letter Queue** - Manejo de errores ✨
- **VPC** - Red privada virtual
- **Security Groups** - Firewall virtual
- **CloudWatch** - Monitoreo y métricas

### Testing y Calidad
- **pytest** - Framework de testing (152 tests, 99.9% coverage)
- **k6** - Herramienta de pruebas de carga
- **SonarQube** - Análisis de calidad de código (Quality Gate: PASSED)
- **Coverage.py** - Medición de cobertura
- **flake8, black, isort** - Linters y formateo

---

## 📂 Estructura del Proyecto

```
MISO4204-Desarrollo_Nube/
│
├── app/                                    # Código fuente de la aplicación
│   ├── api/                                # Capa API
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py                     # Endpoints de autenticación
│   │       ├── health.py                   # Health check
│   │       ├── videos.py                   # Gestión de videos (CRUD) + SQS
│   │       └── public.py                   # Endpoints públicos (votos, rankings)
│   │
│   ├── core/                               # Núcleo de la aplicación
│   │   ├── __init__.py
│   │   ├── config.py                       # Configuración con Pydantic Settings
│   │   ├── security.py                     # JWT token management
│   │   └── storage.py                      # Integración S3 con presigned URLs
│   │
│   ├── db/                                 # Base de datos
│   │   ├── __init__.py
│   │   ├── base.py                         # Base model con UUID y timestamps
│   │   ├── database.py                     # SQLAlchemy engine y session
│   │   └── models.py                       # Modelos (User, Video, Vote)
│   │
│   ├── schemas/                            # Schemas Pydantic
│   │   ├── __init__.py
│   │   ├── auth.py                         # Schemas de autenticación
│   │   ├── video.py                        # Schemas de videos
│   │   └── vote.py                         # Schemas de votos y rankings
│   │
│   ├── services/                           # Servicios
│   │   ├── __init__.py
│   │   └── queue.py                        # 🆕 Servicio SQS (send, receive, delete)
│   │
│   ├── worker/                             # Procesamiento asíncrono
│   │   ├── __init__.py
│   │   ├── sqs_worker.py                   # 🆕 Worker SQS con long polling
│   │   └── videos.py                       # 🆕 Procesamiento de videos (S3 + moviepy)
│   │
│   └── main.py                             # Punto de entrada de FastAPI
│
├── tests/                                  # Suite de tests (99.9% coverage)
│   ├── api/
│   │   ├── test_auth.py                    # Tests de autenticación (15 tests)
│   │   ├── test_videos.py                  # Tests de videos (33 tests)
│   │   ├── test_videos_extended.py         # 🆕 Tests extended (2 tests)
│   │   ├── test_public.py                  # Tests de endpoints públicos (10 tests)
│   │   └── test_health.py                  # Tests de health check (2 tests)
│   ├── core/
│   │   ├── test_security.py                # Tests de seguridad (6 tests)
│   │   └── test_storage.py                 # Tests de storage S3 (33 tests)
│   ├── db/
│   │   ├── test_models.py                  # Tests de modelos (4 tests)
│   │   └── test_database.py                # Tests de database (3 tests)
│   ├── schemas/
│   │   └── test_base.py                    # Tests de schemas (4 tests)
│   ├── services/
│   │   └── test_queue.py                   # 🆕 Tests de SQS (24 tests)
│   ├── worker/
│   │   ├── test_sqs_worker.py              # 🆕 Tests de worker SQS (6 tests)
│   │   ├── test_videos.py                  # 🆕 Tests de procesamiento (14 tests)
│   │   └── test_videos_extended.py         # 🆕 Tests extended (5 tests)
│   └── conftest.py                         # Fixtures de pytest
│
├── docs/                                   # 📖 Documentación completa
│   ├── Entrega_1/                          # Entrega 1 (Docker local)
│   ├── Entrega_2/                          # Entrega 2 (3 EC2 + NFS)
│   ├── Entrega_3/                          # Entrega 3 (Auto Scaling + S3)
│   └── Entrega_4/                          # ✅ Entrega 4 (SQS + Worker ASG)
│       ├── arquitectura_aws_sqs.md         # Arquitectura con SQS
│       └── deployment/
│           ├── README.md                   # Guía de despliegue
│           └── cloudformation/
│               └── infrastructure.yaml     # 🔧 Template CloudFormation con SQS
│
├── capacity-planning/                      # 📊 Pruebas de carga
│   ├── pruebas_de_carga_entrega4.md       # 🆕 Reporte completo de pruebas
│   ├── scripts-entrega4/                   # 🆕 Scripts de pruebas
│   │   ├── README.md                       # Guía de uso
│   │   ├── setup_crear_usuarios_prueba.sh  # Setup de usuarios
│   │   ├── test_escenario1_capa_web.js    # Test k6 para capa web
│   │   ├── test_escenario2_worker_autoscaling.sh # Test Worker ASG
│   │   └── upload_videos_python.py        # Script Python de uploads
│   ├── scripts-entrega3/                   # Scripts Entrega 3
│   └── results-entrega4/                   # 🆕 Resultados de pruebas
│
├── collections/                            # Colección de Postman
│   ├── postman_collection.json             # Colección con 9 endpoints + tests
│   ├── postman_environment.json            # Variables de entorno
│   └── README.md                           # Guía de uso con Newman CLI
│
├── .github/
│   └── workflows/
│       └── ci.yml                          # Pipeline de CI/CD
│
├── reporte_sonarqube.md                    # 🆕 Reporte SonarQube (99.9% coverage)
├── .env                                    # Variables de entorno
├── docker-compose.yml                      # Orquestación de servicios
├── Dockerfile                              # Imagen para API y Worker
├── nginx.conf                              # Configuración de Nginx
├── pyproject.toml                          # Dependencias con Poetry
├── .pre-commit-config.yaml                 # Hooks de pre-commit
└── README.md                               # Este archivo
```

### Módulos Clave de Entrega 4 ✨

#### `app/services/queue.py` - Servicio SQS
```python
class SQSService:
    - send_message()           # Envía mensaje a cola SQS
    - receive_messages()       # Recibe con long polling (20s)
    - delete_message()         # Elimina mensaje procesado
    - change_visibility()      # Extiende timeout de visibilidad
    - get_queue_attributes()   # Obtiene métricas de cola
    - get_dlq_messages_count() # Cuenta mensajes en DLQ
```

#### `app/worker/sqs_worker.py` - Worker con SQS
```python
def main():
    1. Registra signal handlers (SIGTERM, SIGINT)
    2. Inicia long polling en SQS (20s)
    3. Procesa mensajes de video:
       - Descarga de S3
       - Procesamiento con moviepy
       - Upload de procesado a S3
       - Actualiza PostgreSQL
    4. Elimina mensaje de cola si exitoso
    5. Reintenta automáticamente (max 3 veces)
    6. Envía a DLQ si falla definitivamente
```

#### `app/api/routes/videos.py` - Upload con SQS
```python
@router.post("/upload")
def upload_video(...):
    1. Valida archivo y usuario
    2. Genera UUID para video
    3. Sube a S3 (original)
    4. Crea registro en PostgreSQL
    5. Envía mensaje a SQS con:
       - video_id
       - user_id
       - file_path
    6. Retorna inmediatamente (async)
```

#### `docs/Entrega_4/deployment/cloudformation/infrastructure.yaml`
```yaml
Resources:
  # Networking
  - VPC (10.0.0.0/16)
  - 2 Subnets públicas (Multi-AZ)

  # SQS (NEW!)
  - VideoProcessingQueue (main queue)
  - VideoProcessingDLQ (dead letter queue)

  # Web Layer
  - Application Load Balancer
  - Web Auto Scaling Group (1-3)

  # Worker Layer (NEW!)
  - Worker Launch Template
  - Worker Auto Scaling Group (1-3)
  - Target Tracking Scaling Policy
    Target: 5 mensajes/worker

  # Storage & Database
  - RDS PostgreSQL (db.t3.micro)
  - S3 Bucket (videos)

  # Security & Monitoring
  - Security Groups
  - IAM Roles (EC2 → SQS, S3)
  - CloudWatch Logs & Metrics
```

---

## 📁 Ubicación de Archivos de Entrega 4

### Documentación

```
docs/Entrega_4/
├── arquitectura_aws_sqs.md              # Arquitectura con SQS
└── deployment/
    ├── README.md                        # Guía de despliegue
    └── cloudformation/
        └── infrastructure.yaml          # Template con SQS + Worker ASG
```

### Pruebas de Carga

```
capacity-planning/
├── pruebas_de_carga_entrega4.md        # Reporte completo
├── scripts-entrega4/
│   ├── README.md                        # Guía de scripts
│   ├── setup_crear_usuarios_prueba.sh   # Setup usuarios (test1-5@anb.com)
│   ├── test_escenario1_capa_web.js     # Test k6 capa web
│   ├── test_escenario2_worker_autoscaling.sh # Test Worker ASG
│   └── upload_videos_python.py         # Script Python uploads
└── results-entrega4/
    └── [resultados de pruebas]
```

### Código Fuente SQS

```
app/
├── api/routes/videos.py     # Upload con SQS
├── services/queue.py        # Servicio SQS
└── worker/
    ├── sqs_worker.py        # Worker con long polling
    └── videos.py            # Procesamiento de videos
```

### Tests SQS

```
tests/
├── services/test_queue.py           # Tests SQS service (24 tests)
└── worker/
    ├── test_sqs_worker.py           # Tests worker SQS (6 tests)
    ├── test_videos.py               # Tests procesamiento (14 tests)
    └── test_videos_extended.py      # Tests extended (5 tests)
```


---

## 👥 Equipo

Proyecto desarrollado para el curso **MISO4204 - Desarrollo en la Nube**
**Universidad de los Andes**

---

## 📄 Notas Importantes

### Diferencias entre Local y AWS

| Aspecto | Local (Docker) | AWS (Producción) |
|---------|----------------|------------------|
| Cola de mensajes | Redis (simplificado) | Amazon SQS + DLQ |
| Storage | Volúmenes Docker | Amazon S3 |
| Database | PostgreSQL container | Amazon RDS |
| Scaling Web | No | Auto Scaling Group (1-3) |
| Scaling Workers | No | Auto Scaling Group (1-3) basado en SQS |
| Load Balancer | Nginx local | Application Load Balancer |
| Networking | Bridge network | VPC Multi-AZ |

### Configuración de Cola de Mensajes

```bash
# Se usa Amazon SQS
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/xxx/anb-video-processing-queue
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/xxx/anb-video-processing-dlq
AWS_REGION=us-east-1
```

### Flujo de Procesamiento en Entrega 4

1. **Usuario sube video** → API Web
2. **API guarda en S3** → Amazon S3
3. **API envía mensaje** → Amazon SQS Queue
4. **Worker recibe mensaje** → Long polling (20s)
5. **Worker procesa video** → moviepy + S3
6. **Worker elimina mensaje** → SQS (si exitoso)
7. **Si falla** → Reintenta hasta 3 veces
8. **Si falla definitivamente** → Dead Letter Queue

### Worker Auto Scaling

El Worker ASG escala automáticamente basándose en la profundidad de cola SQS:

- **Target:** 5 mensajes por worker
- **Min:** 1 worker
- **Max:** 3 workers
- **Cooldown:** 300 segundos (5 minutos)

**Ejemplo:**
- 0-5 mensajes → 1 worker
- 6-10 mensajes → 2 workers
- 11-15 mensajes → 3 workers
- 16+ mensajes → 3 workers (máximo)

---
