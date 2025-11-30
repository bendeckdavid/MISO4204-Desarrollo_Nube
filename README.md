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
- **ECS** Autoescalado para web y worker
- **Application Load Balancer** - Distribución de carga
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

## 👥 Equipo

Proyecto desarrollado para el curso **MISO4204 - Desarrollo en la Nube**
Grupo #12
**Universidad de los Andes**

## 📖 Documentación de Entrega 5

### Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| **[Arquitectura AWS ECS Fargate](docs/Entrega_5/arquitectura-aws.md)** | Arquitectura escalable con Fargate y SQS:<br>• Autoescalado: Web por CPU (70%) y Workers por profundidad de cola (target 5)<br>• SQS con DLQ<br>• RDS PostgreSQL y S3 para almacenamiento<br>• Diagrama de arquitectura<br>• Sección de “Comportamiento bajo carga”<br>• Comparativa Entrega 4 vs 5 |
| **[Guía de Despliegue (CloudFormation)](docs/Entrega_5/deployment/deployment-instructions.md)** | Despliegue en Fargate:<br>• Generación de imágenes Docker (`linux/amd64`) y carga a ECR<br>• Template `infrastructure-fargate.yaml`<br>• Creación del stack y validación de servicios<br>• Comandos para verificación (ECS, logs) |
| **[Pruebas de Carga – Entrega 5](docs/Entrega_5/pruebas_de_carga_entrega5.md)** | Evidencia de escalado: <br>• Crecimiento y procesamiento de SQS<br>• Escalado 1→3 workers y ajuste 1→2 web<br>• Capturas de consola de AWS evidanciando la operación bajo carga. |

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
│   └── Entrega_4/                          # Entrega 4 (SQS + Worker ASG)
│   └── Entrega_5/                          # ✅ Entrega 5 (ECS + Fargate)
│       ├── arquitectura-aws.md
│       └── images/                         # Capturas de pantalla de AWS
│       └── deployment/
│           └── cloudformation/
│               └── infrastructure.yaml-fargate  # 🔧 Template CloudFormation
│           └── deployment-instructions.md     # Paso a paso para el despliegue en AWS.
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

### Flujo de Procesamiento en Entrega 4

1. **Usuario sube video** → API Web + ECS
2. **API guarda en S3** → Amazon S3
3. **API envía mensaje** → Amazon SQS Queue
4. **Worker recibe mensaje** → Long polling (20s)
5. **Worker procesa video** → moviepy + S3 + ECS
6. **Worker elimina mensaje** → SQS (si exitoso)
7. **Si falla** → Reintenta hasta 3 veces
8. **Si falla definitivamente** → Dead Letter Queue

---

### Infraestructura como Código

- **[infrastructure-fargate.yaml](docs/Entrega_5/deployment/cloudformation/infrastructure-fargate.yaml)** – Template CloudFormation con:
  - VPC Multi-AZ y Security Groups
  - Application Load Balancer (HTTP/HTTPS)
  - ECS Cluster Fargate
  - Servicios ECS:
    - `anb-video-web-service` (Target Tracking CPU 70%) – 1–2 tareas
    - `anb-video-worker-service` (Target: 5 msgs visibles) – 1–3 tareas
  - Amazon SQS + Dead Letter Queue
  - Amazon RDS PostgreSQL y Amazon S3
  - CloudWatch Logs y métricas (CPU, SQS depth)

---

### Scripts de Pruebas de Carga

Para generar carga y disparar el autoescalado en Entrega 5 se reutilizan los scripts de Entrega 4 ubicados en [`capacity-planning/scripts-entrega4/`](capacity-planning/scripts-entrega4/):

| Script | Descripción |
|--------|-------------|
| **[setup_crear_usuarios_prueba.sh](capacity-planning/scripts-entrega4/setup_crear_usuarios_prueba.sh)** | Crea 5 usuarios de prueba (test1-5@anb.com) |
| **[test_escenario1_capa_web.js](capacity-planning/scripts-entrega4/test_escenario1_capa_web.js)** | Genera tráfico HTTP para la capa web |
| **[test_escenario2_worker_autoscaling.sh](capacity-planning/scripts-entrega4/test_escenario2_worker_autoscaling.sh)** | Encola videos para provocar escalado de workers |
| **[upload_videos_python.py](capacity-planning/scripts-entrega4/upload_videos_python.py)** | Carga múltiple de videos hacia la API |

> La evidencia y análisis se documentan en `docs/Entrega_5/pruebas_de_carga_entrega5.md` y en la sección “Comportamiento Bajo Carga (Evidencia)” del documento de arquitectura.

---