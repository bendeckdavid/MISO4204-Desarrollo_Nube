# ANB Rising Stars Showcase API - Entrega 3

API para la gestión de videos de artistas emergentes con sistema de votación y rankings. **Entrega 3** implementa una arquitectura escalable en AWS con Auto Scaling, Application Load Balancer, Amazon S3 y CloudFormation.

**Proyecto:** MISO4204 - Desarrollo en la Nube
**Universidad:** Universidad de los Andes

---

## 🎥 Video de Sustentación

**Link del video:** [Ver video en OneDrive](https://uniandes-my.sharepoint.com/:v:/g/personal/o_saraza_uniandes_edu_co/EU4jBLJmGHxBk3xY04vv0J4Bb_FN3VYcN4PVtjharFzehQ?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=T4RQfW)

> Video demostrativo del funcionamiento de la aplicación desplegada en AWS con Auto Scaling Group, pruebas de carga y análisis de capacidad.

---

## 📊 Arquitectura de Entrega 3

### Arquitectura Escalable en AWS

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
        │  (1-5 instancias t3.small)    │
        │                               │
        │  ┌──────┐  ┌──────┐  ┌──────┐│
        │  │ Web  │  │ Web  │  │ Web  ││
        │  │  +   │  │  +   │  │  +   ││
        │  │Redis │  │Redis │  │Redis ││
        │  └──┬───┘  └──┬───┘  └──┬───┘│
        └─────┼─────────┼─────────┼─────┘
              │         │         │
              └─────────┼─────────┘
                        │
        ┌───────────────┼───────────────┐
        │               ↓               │
        │     ┌──────────────────┐      │
        │     │ Worker (Celery)  │      │
        │     │ Private Subnet   │      │
        │     └─────────┬────────┘      │
        │               │               │
        ├───────────────┼───────────────┤
        │               ↓               │
        │  ┌─────────┐    ┌──────────┐ │
        │  │   RDS   │    │ S3 Bucket│ │
        │  │Postgres │    │  Videos  │ │
        │  └─────────┘    └──────────┘ │
        └───────────────────────────────┘
```

### Componentes Principales

| Componente | Descripción | Tipo de Instancia |
|------------|-------------|-------------------|
| **Application Load Balancer** | Distribuye tráfico HTTP/HTTPS entre instancias web | - |
| **Auto Scaling Group** | Escala automáticamente de 1 a 5 instancias según CPU | t3.small |
| **Web Servers** | FastAPI + Gunicorn + Nginx + Redis (local) | t3.small (Multi-AZ) |
| **Worker** | Celery + moviepy para procesamiento de videos | t3.small (Private subnet) |
| **Amazon RDS** | PostgreSQL 16 administrado | db.t3.micro |
| **Amazon S3** | Almacenamiento escalable para videos | - |
| **VPC Multi-AZ** | Red privada en 2 zonas de disponibilidad | 10.0.0.0/16 |

### Mejoras vs Entregas Anteriores

| Aspecto | Entrega 1 | Entrega 2 | Entrega 3 ✅ |
|---------|-----------|-----------|-------------|
| **Despliegue** | Docker local | 3 EC2 manuales | CloudFormation (IaC) |
| **Load Balancing** | Nginx local | Ninguno | Application Load Balancer |
| **Escalabilidad** | 1 contenedor | 1 instancia fija | Auto Scaling (1-5) |
| **Almacenamiento** | Volumen Docker | NFS compartido | Amazon S3 |
| **Alta Disponibilidad** | No | Single-AZ | Multi-AZ |
| **Capacidad probada** | 5-10 usuarios | 10-20 usuarios | **150 usuarios concurrentes** |

---

## 📖 Documentación de Entrega 3

### Documentación Principal

| Documento | Descripción |
|-----------|-------------|
| **[Arquitectura AWS](docs/Entrega_3/arquitectura_aws.md)** | Arquitectura escalable completa con CloudFormation:<br>• Auto Scaling Group (1-5 instancias)<br>• Application Load Balancer<br>• Amazon S3 para videos<br>• Multi-AZ para alta disponibilidad<br>• Infraestructura como código<br>• Diagramas de arquitectura y flujos |
| **[Pruebas de Carga](capacity-planning/pruebas_de_carga_entrega3.md)** | Pruebas de capacidad con k6:<br>• **Escenario 1:** Capa Web - 150 VUs, 40,287 requests, 39.46 req/s<br>• **Escenario 2:** Upload y Procesamiento - 100% éxito<br>• Análisis de Auto Scaling bajo carga<br>• Comparación con Entrega 2 (650% mejora de capacidad)<br>• Identificación de umbrales de operación<br>• Recomendaciones de escalabilidad |
| **[Guía de Despliegue CloudFormation](docs/Entrega_3/deployment/README.md)** | Despliegue automatizado con CloudFormation:<br>• Stack de infraestructura completo<br>• Configuración de parámetros<br>• Variables de entorno y secretos<br>• Troubleshooting y validación<br>• Scripts de apoyo para pruebas |
| **[Reporte SonarQube](docs/Entrega_3/reporte_sonarqube.md)** | Análisis de calidad actualizado:<br>• Quality Gate: PASSED<br>• 0 bugs, 0 vulnerabilidades<br>• Coverage: 98.8%<br>• Soporte para S3 y presigned URLs<br>• Tests actualizados para S3 |

### Infraestructura como Código

- **[infrastructure.yaml](docs/Entrega_3/deployment/cloudformation/infrastructure.yaml)** - Template CloudFormation con:
  - VPC Multi-AZ (10.0.0.0/16)
  - Application Load Balancer
  - Auto Scaling Group (1-5 instancias)
  - Amazon RDS PostgreSQL
  - S3 Bucket para videos
  - Worker en subnet privada
  - Security Groups y IAM Roles

### Scripts de Pruebas de Carga

Ubicados en [`capacity-planning/scripts-entrega3/`](capacity-planning/scripts-entrega3/):

| Script | Descripción |
|--------|-------------|
| **[test_escenario1_capa_web.js](capacity-planning/scripts-entrega3/test_escenario1_capa_web.js)** | Test k6 para capa web (17 min, 5→150 VUs) |
| **[test_escenario2_upload_videos.js](capacity-planning/scripts-entrega3/test_escenario2_upload_videos.js)** | Test k6 para upload y procesamiento (3 min, 2 VUs) |
| **[graficas_escenario1.py](capacity-planning/scripts-entrega3/graficas_escenario1.py)** | Generación de gráficas Escenario 1 |
| **[generar_graficas_escenario2.py](capacity-planning/scripts-entrega3/generar_graficas_escenario2.py)** | Generación de gráficas Escenario 2 |
| **[setup_crear_usuarios_prueba.sh](capacity-planning/scripts-entrega3/setup_crear_usuarios_prueba.sh)** | Setup inicial de usuarios de prueba |
| **[README.md](capacity-planning/scripts-entrega3/README.md)** | Guía completa de uso de scripts |

---

## 🚀 Prueba Local con Docker Compose

Aunque la arquitectura principal está en AWS, puedes probar la aplicación localmente con Docker Compose.

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

# 2. Reconstruir imágenes (incluye boto3 para S3)
docker-compose down -v
docker-compose build --no-cache

# 3. Iniciar servicios
docker-compose up -d

# 4. Esperar ~30 segundos para que todos los servicios estén listos
sleep 30

# 5. Verificar estado
docker-compose ps
```

### Servicios Locales

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **API** | - | FastAPI (4 workers Gunicorn) |
| **Nginx** | 8080 | Reverse proxy y load balancer |
| **PostgreSQL** | 5433 | Base de datos |
| **Redis** | 6380 | Message broker para Celery |
| **Worker** | - | Celery para procesamiento de videos |

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

# Subir video
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
docker-compose exec -T api pytest tests/ -v

# Con reporte de cobertura
docker-compose exec -T api pytest tests/ --cov=app --cov-report=term

# Suite específica
docker-compose exec -T api pytest tests/api/test_videos.py -v
```

### Cobertura de Tests

- **Cobertura actual:** 98.8%
- **Tests totales:** 40+ tests pasando
- **Suites:** Autenticación, Videos, Endpoints Públicos, Health Check, S3 Integration

---

## 📊 Resultados de Pruebas de Carga (AWS)

### Escenario 1: Capa Web

- **Usuarios concurrentes máximos:** 150 VUs
- **Requests totales:** 40,287
- **Throughput máximo:** 39.46 req/s
- **Latencia p50:** 120.81 ms
- **Latencia p95:** 3,012.94 ms
- **Tasa de éxito:** 83%

**Conclusión:** El sistema soporta hasta 150 usuarios concurrentes con Auto Scaling activo.

### Escenario 2: Upload y Procesamiento

- **Tasa de éxito de upload:** 100%
- **Tiempo promedio de upload:** 994 ms
- **Videos procesados:** 2 (test mínimo)
- **Workers:** 1 instancia en subnet privada
- **Integración S3:** Funcional

**Conclusión:** Upload a S3 y cola de procesamiento funcionan correctamente.

### Comparación con Entrega 2

| Métrica | Entrega 2 | Entrega 3 | Mejora |
|---------|-----------|-----------|--------|
| Usuarios concurrentes | 20 | 150 | **650%** |
| Escalabilidad | Fija (1 EC2) | Auto (1-5 EC2) | Dinámica |
| Almacenamiento | NFS (bottleneck) | S3 | Ilimitado |
| Alta disponibilidad | No | Multi-AZ | Sí |

---

## 🏗️ Stack Tecnológico

### Backend
- **FastAPI** 0.118+ - Framework moderno para APIs
- **Python** 3.12 - Lenguaje de programación
- **Gunicorn + Uvicorn** - Servidor ASGI con 4 workers
- **SQLAlchemy** 2.0+ - ORM para PostgreSQL
- **Pydantic** 2.5+ - Validación de datos

### Procesamiento Asíncrono
- **Celery** 5.3+ - Cola de tareas distribuida
- **Redis** 7+ - Message broker
- **moviepy** 2.2+ - Procesamiento de videos (trim, resize, watermark)

### Almacenamiento
- **PostgreSQL** 16 - Base de datos relacional (RDS)
- **Amazon S3** - Almacenamiento de videos
- **boto3** - SDK de AWS para Python

### Infraestructura AWS
- **CloudFormation** - Infraestructura como código
- **EC2** t3.small - Instancias de cómputo
- **Application Load Balancer** - Distribución de carga
- **Auto Scaling Group** - Escalado automático
- **VPC** - Red privada virtual
- **Security Groups** - Firewall virtual

### Testing y Calidad
- **pytest** - Framework de testing
- **k6** - Herramienta de pruebas de carga
- **SonarQube** - Análisis de calidad de código
- **Coverage.py** - Medición de cobertura

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
│   │       ├── videos.py                   # Gestión de videos (CRUD)
│   │       └── public.py                   # Endpoints públicos (votos, rankings)
│   │
│   ├── core/                               # Núcleo de la aplicación
│   │   ├── __init__.py
│   │   ├── config.py                       # Configuración con Pydantic Settings
│   │   ├── security.py                     # JWT token management
│   │   └── storage.py                      # 🆕 Integración S3 con presigned URLs
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
│   ├── worker/                             # Procesamiento asíncrono
│   │   ├── __init__.py
│   │   ├── celery_app.py                   # Configuración de Celery
│   │   └── videos.py                       # 🆕 Tareas asíncronas (S3 + moviepy)
│   │
│   └── main.py                             # Punto de entrada de FastAPI
│
├── tests/                                  # Suite de tests (98.8% coverage)
│   ├── api/
│   │   ├── test_auth.py                    # Tests de autenticación (15 tests)
│   │   ├── test_videos.py                  # Tests de videos (14 tests)
│   │   ├── test_public.py                  # Tests de endpoints públicos (9 tests)
│   │   └── test_health.py                  # Tests de health check (2 tests)
│   └── conftest.py                         # Fixtures de pytest
│
├── docs/                                   # 📖 Documentación completa
│   ├── Entrega_1/                          # Entrega 1 (Docker local)
│   ├── Entrega_2/                          # Entrega 2 (3 EC2 + NFS)
│   └── Entrega_3/                          # ✅ Entrega 3 (Auto Scaling + S3)
│       ├── arquitectura_aws.md             # Arquitectura completa
│       ├── reporte_sonarqube.md            # Análisis de calidad
│       └── deployment/
│           ├── README.md                   # Guía de despliegue
│           └── cloudformation/
│               └── infrastructure.yaml     # 🔧 Template CloudFormation IaC
│
├── capacity-planning/                      # 📊 Pruebas de carga
│   ├── pruebas_de_carga_entrega3.md       # Reporte completo de pruebas
│   ├── scripts-entrega3/                   # Scripts de pruebas k6
│   │   ├── README.md                       # Guía de uso
│   │   ├── test_escenario1_capa_web.js    # Test web (17 min, 5→150 VUs)
│   │   ├── test_escenario2_upload_videos.js # Test upload (3 min, 2 VUs)
│   │   ├── graficas_escenario1.py          # Generador de gráficas E1
│   │   ├── generar_graficas_escenario2.py  # Generador de gráficas E2
│   │   └── setup_crear_usuarios_prueba.sh  # Setup de usuarios
│   └── results-entrega3/                   # Resultados de pruebas
│       ├── escenario1_output_final.log
│       ├── graficas_escenario1.png
│       ├── graficas_escenario2.png
│       └── comparacion_entrega2_vs_entrega3.png
│
├── collections/                            # Colección de Postman
│   ├── postman_collection.json             # Colección con 9 endpoints + tests
│   ├── postman_environment.json            # Variables de entorno
│   └── README.md                           # Guía de uso con Newman CLI
│
├── media/                                  # Archivos de video (volumen Docker)
│   ├── uploads/                            # Videos originales subidos
│   └── processed/                          # Videos procesados
│
├── .github/
│   └── workflows/
│       └── ci.yml                          # Pipeline de CI/CD
│
├── .env                                    # Variables de entorno
├── docker-compose.yml                      # Orquestación de servicios
├── Dockerfile                              # 🆕 Imagen para API y Worker (con boto3)
├── nginx.conf                              # Configuración de Nginx
├── pyproject.toml                          # 🆕 Dependencias con Poetry (incluye boto3)
├── .pre-commit-config.yaml                 # Hooks de pre-commit
└── README.md                               # Este archivo
```

### Módulos Clave de Entrega 3

#### `app/core/storage.py` - Sistema de Almacenamiento
```python
# Abstracción para soportar local y S3
class StorageBackend:
    - save_file()              # Guarda archivo (local o S3)
    - get_file_url()           # Obtiene URL (path local o presigned URL S3)
    - delete_file()            # Elimina archivo

# Configuración dinámica según STORAGE_BACKEND
STORAGE_BACKEND = "s3"  # En AWS
STORAGE_BACKEND = "local"  # En Docker local
```

#### `app/worker/videos.py` - Procesamiento Asíncrono
```python
# Tarea Celery para procesamiento de videos
@celery.task
def process_video(video_id):
    1. Descarga video de S3
    2. Procesa con moviepy:
       - Recorta a 30 segundos
       - Redimensiona a 720p
       - Agrega watermark
    3. Sube video procesado a S3
    4. Actualiza estado en PostgreSQL
```

#### `docs/Entrega_3/deployment/cloudformation/infrastructure.yaml`
```yaml
Resources:
  - VPC (10.0.0.0/16)
  - 2 Subnets públicas (Multi-AZ)
  - 1 Subnet privada (Worker)
  - Application Load Balancer
  - Auto Scaling Group (1-5 instancias)
  - RDS PostgreSQL (db.t3.micro)
  - S3 Bucket (videos)
  - Security Groups
  - IAM Roles (EC2 → S3 access)
  - CloudWatch Logs
```

---

## 📁 Ubicación de Archivos de Entrega 3

### Documentación

```
docs/Entrega_3/
├── arquitectura_aws.md                  # Arquitectura completa
├── reporte_sonarqube.md                 # Análisis de calidad
└── deployment/
    ├── README.md                        # Guía de despliegue
    └── cloudformation/
        └── infrastructure.yaml          # Template IaC
```

### Pruebas de Carga

```
capacity-planning/
├── pruebas_de_carga_entrega3.md        # Reporte completo
├── scripts-entrega3/
│   ├── README.md                        # Guía de scripts
│   ├── test_escenario1_capa_web.js     # Test web layer
│   ├── test_escenario2_upload_videos.js # Test upload
│   ├── graficas_escenario1.py           # Gráficas E1
│   ├── generar_graficas_escenario2.py   # Gráficas E2
│   └── setup_crear_usuarios_prueba.sh   # Setup usuarios
└── results-entrega3/
    ├── escenario1_output_final.log
    ├── graficas_escenario1.png
    ├── graficas_escenario2.png
    └── comparacion_entrega2_vs_entrega3.png
```

### Código Fuente

```
app/
├── api/routes/          # Endpoints
├── core/
│   ├── storage.py       # Integración S3 con presigned URLs
│   └── config.py        # Configuración (STORAGE_BACKEND=s3)
├── worker/videos.py     # Tareas Celery para procesamiento
└── main.py              # Punto de entrada FastAPI
```

---

## 🔗 Enlaces Útiles

- [Documentación Interactiva (Swagger)](http://localhost:8080/docs)
- [Documentación Alternativa (ReDoc)](http://localhost:8080/redoc)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [k6 Load Testing](https://k6.io/docs/)

---

## 👥 Equipo

Proyecto desarrollado para el curso **MISO4204 - Desarrollo en la Nube**
**Universidad de los Andes**

---

## 📄 Notas Importantes

### Diferencias entre Local y AWS

| Aspecto | Local (Docker) | AWS (Producción) |
|---------|----------------|------------------|
| Storage | Volúmenes Docker | Amazon S3 |
| Database | PostgreSQL container | Amazon RDS |
| Scaling | No | Auto Scaling Group (1-5) |
| Load Balancer | Nginx local | Application Load Balancer |
| Networking | Bridge network | VPC Multi-AZ |

### Configuración de Storage

En **local** (Docker):
```bash
STORAGE_BACKEND=local  # Usa /app/media
```

En **AWS**:
```bash
STORAGE_BACKEND=s3     # Usa S3 bucket
AWS_S3_BUCKET_NAME=anb-video-storage-bucket
AWS_REGION=us-east-1
```

---

**¿Necesitas ayuda?** Consulta la [documentación completa de Entrega 3](docs/Entrega_3/arquitectura_aws.md) o revisa las [pruebas de carga](capacity-planning/pruebas_de_carga_entrega3.md).
