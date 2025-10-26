# Arquitectura de la Aplicación en AWS

## Tabla de Contenidos
- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Arquitectura de Despliegue](#arquitectura-de-despliegue)
- [Arquitectura de Componentes](#arquitectura-de-componentes)
- [Servicios de AWS Utilizados](#servicios-de-aws-utilizados)
- [Cambios Respecto a Entrega 1](#cambios-respecto-a-entrega-1)
- [Decisiones de Diseño](#decisiones-de-diseño)
- [Consideraciones de Seguridad](#consideraciones-de-seguridad)
- [Escalabilidad y Mejoras Futuras](#escalabilidad-y-mejoras-futuras)

---

## Resumen Ejecutivo

La aplicación **ANB Rising Stars Showcase** ha sido migrada exitosamente desde un entorno de contenedores Docker local a una arquitectura de nube pública en Amazon Web Services (AWS). Esta migración busca aprovechar la infraestructura escalable y confiable de AWS para proporcionar mayor disponibilidad, rendimiento y capacidad de crecimiento.

### Características Principales de la Arquitectura:
- **Desacoplamiento de componentes**: Cada servicio se ejecuta en su propia instancia EC2, permitiendo escalado independiente
- **Alta disponibilidad**: Uso de servicios administrados (Amazon RDS) para garantizar persistencia de datos
- **Procesamiento asíncrono**: Celery Worker dedicado para procesamiento de videos sin afectar la API
- **Almacenamiento compartido**: NFS para acceso concurrente a archivos desde múltiples instancias
- **Seguridad por capas**: Security Groups configurados con principio de mínimo privilegio

---

## Arquitectura de Despliegue

### Diagrama de Despliegue

```
                                    ┌─────────────────┐
                                    │   Internet      │
                                    │  (Usuarios)     │
                                    └────────┬────────┘
                                             │
                                             │ HTTPS/HTTP
                                             │ Puerto 8080
                                             ▼
                        ┌────────────────────────────────────┐
                        │      EC2 Web Server (t3.small)     │
                        │  ┌──────────────────────────────┐  │
                        │  │ Nginx (Reverse Proxy)        │  │
                        │  │ Puerto: 8080 → 8000         │  │
                        │  └──────────────────────────────┘  │
                        │  ┌──────────────────────────────┐  │
                        │  │ Gunicorn (4 workers)         │  │
                        │  │ FastAPI Application          │  │
                        │  │ Puerto: 8000                 │  │
                        │  └──────────────────────────────┘  │
                        │  ┌──────────────────────────────┐  │
                        │  │ Redis (Broker)               │  │
                        │  │ Puerto: 6379                 │  │
                        │  └──────────────────────────────┘  │
                        │  ┌──────────────────────────────┐  │
                        │  │ NFS Client Mount             │  │
                        │  │ /app/media → File Server     │  │
                        │  └──────────────────────────────┘  │
                        └───────────┬────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
    ┌───────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │ EC2 File Server   │  │  Amazon RDS      │  │  EC2 Worker      │
    │   (t3.small)      │  │  (PostgreSQL 16) │  │  (t3.small)      │
    │                   │  │                  │  │                  │
    │ - NFS Server      │  │ db.t3.micro      │  │ - Celery Worker  │
    │ - /shared/media/  │  │ 20 GB gp3        │  │ - FFmpeg         │
    │   ├─ uploads/     │  │                  │  │ - NFS Client     │
    │   └─ processed/   │  │ Puerto: 5432     │  │                  │
    └───────────────────┘  └──────────────────┘  └──────────────────┘
            │                       │                      │
            └───────────────────────┴──────────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │    ANB-VPC        │
                          │  10.0.0.0/16      │
                          │                   │
                          │ Public Subnet 1   │
                          │  10.0.1.0/24      │
                          │                   │
                          │ Public Subnet 2   │
                          │  10.0.2.0/24      │
                          └───────────────────┘
```

### Componentes de Infraestructura

#### 1. VPC (Virtual Private Cloud)
- **CIDR Block**: `10.0.0.0/16`
- **DNS Resolution**: Habilitado
- **DNS Hostnames**: Habilitado
- **Subnets**:
  - **Public Subnet 1**: `10.0.1.0/24` (us-east-1a)
  - **Public Subnet 2**: `10.0.2.0/24` (us-east-1b)
- **Internet Gateway**: Conectado para acceso público

#### 2. Instancias EC2

| Instancia | Tipo | vCPUs | RAM | Storage | Rol |
|-----------|------|-------|-----|---------|-----|
| **Web Server** | t3.small | 2 | 2 GiB | 50 GiB gp3 | API REST, Nginx, Redis |
| **Worker** | t3.small | 2 | 2 GiB | 50 GiB gp3 | Procesamiento de videos |
| **File Server** | t3.small | 2 | 2 GiB | 50 GiB gp3 | NFS, almacenamiento compartido |

**Configuración común:**
- **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
- **Key Pair**: anb-key-pair
- **Subnet**: ANB-Public-Subnet-1
- **Auto-assign Public IP**: Habilitado

#### 3. Amazon RDS (PostgreSQL)
- **Engine**: PostgreSQL 16.4
- **Instance Class**: db.t3.micro (2 vCPUs, 1 GiB RAM)
- **Storage**: 20 GiB gp3
- **Multi-AZ**: No (entorno de desarrollo)
- **Backup**: Deshabilitado (para minimizar costos)
- **Public Access**: No
- **Database**: `fastapi_db`
- **Usuario**: `fastapi_user`

#### 4. Security Groups

| Security Group | Puertos Entrantes | Origen | Descripción |
|----------------|-------------------|--------|-------------|
| **ANB-WebServer-SG** | 8080 (TCP) | 0.0.0.0/0 | API pública |
| | 22 (SSH) | Mi IP | Administración |
| | 6379 (Redis) | Worker SG | Cola de tareas |
| **ANB-Worker-SG** | 22 (SSH) | Mi IP | Administración |
| **ANB-FileServer-SG** | 2049 (NFS) | Web + Worker SG | Acceso NFS |
| | 22 (SSH) | Mi IP | Administración |
| **ANB-RDS-SG** | 5432 (PostgreSQL) | Web + Worker SG | Base de datos |

---

## Arquitectura de Componentes

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Server (EC2)                         │
│                                                                 │
│  ┌────────────┐    ┌─────────────────────────────────────┐    │
│  │   Nginx    │───▶│         Gunicorn                    │    │
│  │  (Port 80) │    │  ┌───────────────────────────────┐  │    │
│  └────────────┘    │  │  Uvicorn Worker 1             │  │    │
│         │          │  │  ┌─────────────────────────┐  │  │    │
│         │          │  │  │   FastAPI Application   │  │  │    │
│         │          │  │  │  ┌──────────────────┐   │  │  │    │
│         │          │  │  │  │ API Routes       │   │  │  │    │
│         │          │  │  │  │ - /api/auth/*    │   │  │  │    │
│         │          │  │  │  │ - /api/videos/*  │   │  │  │    │
│         │          │  │  │  │ - /api/public/*  │   │  │  │    │
│         │          │  │  │  └──────────────────┘   │  │  │    │
│         │          │  │  │  ┌──────────────────┐   │  │  │    │
│         │          │  │  │  │ Security (JWT)   │   │  │  │    │
│         │          │  │  │  └──────────────────┘   │  │  │    │
│         │          │  │  │  ┌──────────────────┐   │  │  │    │
│         │          │  │  │  │ SQLAlchemy ORM   │   │  │  │    │
│         │          │  │  │  └──────────────────┘   │  │  │    │
│         │          │  │  └─────────────────────────┘  │  │    │
│         │          │  └───────────────────────────────┘  │    │
│         │          │  │  Uvicorn Worker 2-4 (similar)   │    │
│         │          │  └─────────────────────────────────┘    │
│         │          └─────────────────────────────────────┘    │
│         │                         │           │                │
│         │                         │           │                │
│  ┌──────▼──────┐         ┌────────▼────┐  ┌──▼──────────┐    │
│  │   Redis     │◀────────│ Celery Tasks│  │  NFS Mount  │    │
│  │ (Port 6379) │         │   Producer  │  │  /app/media │    │
│  └─────────────┘         └─────────────┘  └─────────────┘    │
│         │                                         │            │
└─────────┼─────────────────────────────────────────┼────────────┘
          │                                         │
          │                                         │
          │         ┌───────────────────┐           │
          └────────▶│   File Server     │◀──────────┘
                    │  (NFS Server)     │
                    │                   │
          ┌────────▶│  /shared/media/   │◀──────────┐
          │         │    ├─ uploads/    │           │
          │         │    └─ processed/  │           │
          │         └───────────────────┘           │
          │                                         │
          │                                         │
┌─────────┼─────────────────────────────────────────┼────────────┐
│         │              Worker (EC2)               │            │
│         │                                         │            │
│  ┌──────▼────────┐                        ┌───────▼──────┐    │
│  │  Celery       │                        │  NFS Mount   │    │
│  │  Worker       │                        │  /app/media  │    │
│  │               │                        └──────────────┘    │
│  │  ┌─────────┐  │                                            │
│  │  │ Task    │  │         ┌─────────────────┐                │
│  │  │ Consumer│  │────────▶│     FFmpeg      │                │
│  │  └─────────┘  │         │ Video Processing│                │
│  │               │         │ - Trim (30s)    │                │
│  │  Concurrency: │         │ - Resize (720p) │                │
│  │  2 workers    │         │ - Watermark     │                │
│  └───────────────┘         └─────────────────┘                │
│         │                                                      │
└─────────┼──────────────────────────────────────────────────────┘
          │
          │
    ┌─────▼──────┐
    │  Amazon    │
    │    RDS     │
    │ PostgreSQL │
    │            │
    │ ┌────────┐ │
    │ │ users  │ │
    │ ├────────┤ │
    │ │ videos │ │
    │ ├────────┤ │
    │ │ votes  │ │
    │ └────────┘ │
    └────────────┘
```

### Flujo de Procesamiento de Videos

```
Usuario                Web Server          Redis/Celery        Worker          NFS/File Server
  │                        │                    │                │                    │
  │  1. POST /videos/upload│                    │                │                    │
  ├───────────────────────▶│                    │                │                    │
  │                        │                    │                │                    │
  │                        │ 2. Guardar archivo │                │                    │
  │                        ├────────────────────┴────────────────┴───────────────────▶│
  │                        │                    │                │        uploads/    │
  │                        │◀───────────────────┴────────────────┴─────────────────────│
  │                        │                    │                │                    │
  │                        │ 3. Crear registro  │                │                    │
  │                        │     en DB          │                │                    │
  │                        │ (status=pending)   │                │                    │
  │                        │                    │                │                    │
  │                        │ 4. Encolar tarea   │                │                    │
  │                        ├───────────────────▶│                │                    │
  │                        │  process_video()   │                │                    │
  │                        │                    │                │                    │
  │  5. Response 202       │                    │                │                    │
  │◀───────────────────────│                    │                │                    │
  │  {id, status:pending}  │                    │                │                    │
  │                        │                    │                │                    │
  │                        │                    │ 6. Dequeue     │                    │
  │                        │                    ├───────────────▶│                    │
  │                        │                    │                │                    │
  │                        │                    │                │ 7. Leer archivo    │
  │                        │                    │                ├───────────────────▶│
  │                        │                    │                │    uploads/        │
  │                        │                    │                │◀───────────────────│
  │                        │                    │                │                    │
  │                        │                    │                │ 8. FFmpeg:         │
  │                        │                    │                │   - Trim 30s       │
  │                        │                    │                │   - Resize 720p    │
  │                        │                    │                │   - Watermark      │
  │                        │                    │                │                    │
  │                        │                    │                │ 9. Guardar         │
  │                        │                    │                │    procesado       │
  │                        │                    │                ├───────────────────▶│
  │                        │                    │                │   processed/       │
  │                        │                    │                │                    │
  │                        │ 10. Actualizar DB  │                │                    │
  │                        │◀────────────────────────────────────│                    │
  │                        │  (status=completed)│                │                    │
  │                        │                    │                │                    │
  │  11. GET /videos/{id}  │                    │                │                    │
  ├───────────────────────▶│                    │                │                    │
  │                        │                    │                │                    │
  │  12. Response 200      │                    │                │                    │
  │◀───────────────────────│                    │                │                    │
  │  {status:completed,    │                    │                │                    │
  │   processed_url}       │                    │                │                    │
```

---

## Servicios de AWS Utilizados

### Amazon EC2 (Elastic Compute Cloud)

**Propósito**: Ejecutar los componentes de aplicación (Web Server, Worker, File Server)

**Características utilizadas:**
- **Instancias t3.small**: Instancias de propósito general con burstable CPU
  - 2 vCPUs (Intel Xeon Platinum 8000 series)
  - 2 GiB de RAM
  - Hasta 5 Gbps de ancho de banda de red
  - EBS-optimized por defecto
- **EBS gp3**: Volúmenes de almacenamiento SSD de 50 GiB
  - 3,000 IOPS baseline
  - 125 MB/s throughput
- **Ubuntu 22.04 LTS**: Sistema operativo estable con soporte extendido

**Justificación de elección:**
- t3.small proporciona suficiente capacidad para la carga de trabajo actual
- Burstable CPU permite manejar picos de tráfico ocasionales
- Costo-efectivo para entornos de desarrollo y pruebas
- EBS gp3 ofrece mejor rendimiento que gp2 al mismo precio

### Amazon RDS (Relational Database Service)

**Propósito**: Base de datos PostgreSQL administrada

**Características utilizadas:**
- **PostgreSQL 16.4**: Última versión estable con mejoras de rendimiento
- **db.t3.micro**: Instancia pequeña suficiente para el workload actual
  - 2 vCPUs
  - 1 GiB RAM
- **20 GiB gp3 storage**: Almacenamiento SSD con burstable IOPS
- **Single-AZ deployment**: Para minimizar costos en desarrollo
- **Automated backups disabled**: Reducción de costos en ambiente de pruebas

**Justificación de elección:**
- Elimina la necesidad de administrar PostgreSQL manualmente
- Parches de seguridad automáticos
- Fácil escalado vertical cuando sea necesario
- Aislamiento de red mediante Security Groups
- Preparado para habilitar Multi-AZ en producción

### Amazon VPC (Virtual Private Cloud)

**Propósito**: Red privada aislada para todos los recursos

**Características utilizadas:**
- **CIDR personalizado**: 10.0.0.0/16 (65,536 IPs disponibles)
- **2 subnets públicas**: En diferentes AZs para preparar alta disponibilidad futura
- **Internet Gateway**: Permite acceso a internet desde las instancias
- **Route Tables**: Enrutamiento configurado para tráfico público
- **Security Groups**: Firewall a nivel de instancia con reglas específicas

**Justificación de elección:**
- Aislamiento de red completo
- Control granular de tráfico entrante y saliente
- Preparado para agregar subnets privadas en el futuro
- Permite implementar VPN o Direct Connect si se requiere

### Network File System (NFS)

**Propósito**: Almacenamiento compartido entre Web Server y Worker

**Implementación:**
- Servidor NFS en EC2 dedicado (no se usa Amazon EFS por requisito del proyecto)
- Exporta `/shared/media` con permisos de lectura/escritura
- Montado en `/app/media` en Web Server y Worker

**Justificación de elección:**
- Protocolo estándar, bien documentado
- Bajo overhead de red para archivos grandes (videos)
- Administración directa del almacenamiento
- Sin costos adicionales de servicio administrado

---

## Cambios Respecto a Entrega 1

### Arquitectura de Entorno

| Aspecto | Entrega 1 (Docker Local) | Entrega 2 (AWS) |
|---------|--------------------------|-----------------|
| **Infraestructura** | Laptop local | Cloud público (AWS) |
| **Orquestación** | Docker Compose | Instancias EC2 individuales |
| **Networking** | Bridge network interno | VPC con Security Groups |
| **Base de datos** | PostgreSQL en contenedor | Amazon RDS PostgreSQL |
| **Almacenamiento** | Volumen Docker local | NFS en EC2 dedicado |
| **Escalabilidad** | Limitada por hardware local | Horizontal y vertical en cloud |
| **Acceso** | localhost:8080 | IP pública + DNS (potencial) |
| **Costo** | $0 (recursos locales) | ~$50-80/mes (desarrollo) |

### Cambios en el Código

#### 1. Configuración de Base de Datos
**Antes (Entrega 1):**
```python
DATABASE_URL=postgresql://fastapi_user:fastapi_password@db:5432/fastapi_db
```

**Ahora (Entrega 2):**
```python
DATABASE_URL=postgresql://fastapi_user:password@anb-postgres-db.xxxxx.us-east-1.rds.amazonaws.com:5432/fastapi_db
```

#### 2. Configuración de Redis
**Antes:**
```python
CELERY_BROKER_URL=redis://redis:6379/0
```

**Ahora:**
```python
CELERY_BROKER_URL=redis://<WEBSERVER_PRIVATE_IP>:6379/0
```

#### 3. Rutas de Archivos
**Antes:**
```python
MEDIA_ROOT=/media
```

**Ahora:**
```python
MEDIA_ROOT=/app/media  # Montado desde NFS
```

#### 4. Python Version
**Antes:**
```toml
python = "^3.12"
```

**Ahora:**
```toml
python = "^3.11"  # Compatible con Ubuntu 22.04 LTS
```

### Cambios en Despliegue

| Componente | Docker Compose | AWS Manual |
|------------|----------------|------------|
| **Inicio** | `docker-compose up -d` | Scripts bash + systemd |
| **Logs** | `docker-compose logs -f` | `journalctl -u <service>` |
| **Restart** | `docker-compose restart` | `systemctl restart <service>` |
| **Networking** | Automático (bridge) | Manual (Security Groups) |
| **Dependencias** | `depends_on` en YAML | Scripts de configuración secuencial |
| **Health Checks** | Built-in Docker | Manual con systemd |

### Nuevos Componentes

1. **Scripts de Despliegue Automatizado**
   - `deployment/ec2-setup/01-fileserver-setup.sh`
   - `deployment/ec2-setup/02-webserver-setup.sh`
   - `deployment/ec2-setup/03-worker-setup.sh`

2. **Servicios systemd**
   - `fastapi.service` (Web Server)
   - `celery.service` (Worker)
   - `redis.service` (Broker)

3. **Configuración de NFS**
   - `/etc/exports` en File Server
   - `/etc/fstab` en Web Server y Worker

### Mejoras de Seguridad

| Aspecto | Entrega 1 | Entrega 2 |
|---------|-----------|-----------|
| **Firewall** | iptables local | AWS Security Groups |
| **Acceso SSH** | No aplicable | Key pair + IP whitelisting |
| **Credenciales DB** | En archivo .env local | Variables de entorno en EC2 |
| **Aislamiento** | Contenedores | Instancias EC2 separadas |
| **Redis** | Puerto interno | Puerto restringido por SG |

---

## Decisiones de Diseño

### 1. ¿Por qué separar en 3 instancias EC2?

**Decisión**: Usar 3 instancias separadas para Web Server, Worker y File Server

**Razones:**
- **Aislamiento de recursos**: El procesamiento de videos (CPU-intensivo) no afecta la API
- **Escalado independiente**: Se puede agregar más Workers sin tocar el Web Server
- **Resiliencia**: Fallo en Worker no tumba la API (aunque videos no se procesen)
- **Troubleshooting**: Más fácil depurar problemas cuando están aislados
- **Cumplimiento de requisitos**: El proyecto específicamente requiere 3 instancias separadas

**Alternativas consideradas:**
- ❌ Todo en 1 instancia: Más barato pero viola requisitos y limita escalabilidad
- ❌ Web + Worker juntos: Problemas de recursos compartidos

### 2. ¿Por qué NFS en EC2 en lugar de Amazon EFS?

**Decisión**: Implementar NFS en una instancia EC2 dedicada

**Razones:**
- **Requisito del proyecto**: Explícitamente indica "No utilice el servicio Amazon EFS"
- **Control total**: Administración completa de permisos, exports y configuración
- **Costo**: EC2 t3.small es más económico que EFS para volúmenes pequeños
- **Aprendizaje**: Mayor comprensión de conceptos de networking y almacenamiento

**Trade-offs:**
- ✅ Más barato para workloads pequeños
- ✅ Control total de configuración
- ❌ Single point of failure (no es distribuido como EFS)
- ❌ Requiere administración manual

### 3. ¿Por qué Redis en Web Server en lugar de ElastiCache?

**Decisión**: Instalar Redis en la misma instancia EC2 del Web Server

**Razones:**
- **Simplicidad**: Una dependencia menos que configurar
- **Costo**: ElastiCache tiene costo adicional (~$15-20/mes para cache.t3.micro)
- **Baja latencia**: Redis y FastAPI en la misma instancia = latencia mínima
- **Workload pequeño**: El volumen de tareas no justifica un broker dedicado

**Trade-offs:**
- ✅ Sin costo adicional
- ✅ Latencia ultra-baja
- ❌ Comparte recursos con la API
- ❌ Si el Web Server se cae, se pierden las tareas encoladas

**Mejora futura**: Migrar a ElastiCache cuando el volumen de videos aumente significativamente

### 4. ¿Por qué db.t3.micro para RDS?

**Decisión**: Usar la instancia RDS más pequeña disponible

**Razones:**
- **Workload actual**: 10-50 usuarios concurrentes no requieren más capacidad
- **Costo-efectivo**: ~$15/mes vs ~$30/mes para db.t3.small
- **Burstable performance**: T3 puede manejar picos temporales
- **Fácil escalado**: Se puede cambiar a instancia mayor sin downtime significativo

**Métricas de decisión:**
```
Concurrent connections: ~20-50
Query load: Lectura-intensivo (rankings, listados)
Writes: Bajos (uploads, votos ocasionales)
Database size: < 5 GB en primeros 6 meses
```

### 5. ¿Por qué Single-AZ para RDS?

**Decisión**: No usar Multi-AZ deployment

**Razones:**
- **Entorno de desarrollo**: No es producción crítica todavía
- **Costo**: Multi-AZ duplica el costo (~$30/mes adicionales)
- **Downtime aceptable**: Para pruebas, 5-10 min de downtime es tolerable
- **Plan de migración**: Se activará Multi-AZ antes de ir a producción

**Riesgos asumidos:**
- ⚠️ RTO (Recovery Time Objective): ~10-15 minutos en caso de fallo de AZ
- ⚠️ RPO (Recovery Point Objective): 0 (sin backups automáticos habilitados)

### 6. ¿Por qué Python 3.11 en lugar de 3.12?

**Decisión**: Cambiar la versión mínima de Python de 3.12 a 3.11

**Razones:**
- **Disponibilidad en Ubuntu 22.04 LTS**: Viene con Python 3.11 por defecto
- **Estabilidad**: LTS garantiza soporte hasta 2027
- **Compatibilidad**: Todas las dependencias son compatibles con 3.11
- **Evitar compilación**: No es necesario compilar Python desde source

### 7. ¿Por qué systemd en lugar de supervisord?

**Decisión**: Usar systemd para gestionar servicios

**Razones:**
- **Nativo en Ubuntu**: Ya instalado y configurado
- **Logging integrado**: `journalctl` proporciona logs centralizados
- **Auto-restart**: Configuración simple con `Restart=always`
- **Boot persistence**: Servicios inician automáticamente con `systemctl enable`

---

## Consideraciones de Seguridad

### 1. Security Groups (Firewall)

#### Principio de Mínimo Privilegio
Cada instancia solo tiene abiertos los puertos estrictamente necesarios:

**Web Server:**
```
Inbound:
  - Puerto 8080: Acceso público a la API
  - Puerto 22: SSH solo desde IP del administrador
  - Puerto 6379: Redis solo desde Worker

Outbound:
  - All traffic (necesario para apt, pip, git, etc.)
```

**Worker:**
```
Inbound:
  - Puerto 22: SSH solo desde IP del administrador

Outbound:
  - All traffic (necesario para conectar a Redis, RDS, NFS)
```

**File Server:**
```
Inbound:
  - Puerto 2049: NFS solo desde Web Server y Worker
  - Puerto 22: SSH solo desde IP del administrador

Outbound:
  - All traffic (updates de sistema)
```

**RDS:**
```
Inbound:
  - Puerto 5432: PostgreSQL solo desde Web Server y Worker

Outbound:
  - No aplicable (RDS no inicia conexiones salientes)
```

### 2. Gestión de Credenciales

#### Variables de Entorno
Las credenciales sensibles NUNCA se hardcodean:

```bash
# ❌ MAL
DATABASE_URL=postgresql://user:password@host/db

# ✅ BIEN
DATABASE_URL=${RDS_ENDPOINT}
```

#### Archivos .env
```bash
# En cada instancia EC2
/home/appuser/MISO4204-Desarrollo_Nube/.env

# Permisos restrictivos
chmod 600 .env
chown appuser:appuser .env
```

#### Secretos NO en Git
```gitignore
.env
.env.*
*.pem
*.key
```

### 3. Acceso SSH

#### Key Pairs
- **Generación**: Key pair creado en AWS Console
- **Distribución**: Archivo `.pem` NUNCA se sube a Git
- **Permisos**: `chmod 400 anb-key-pair.pem`
- **Ubicación**: Solo en laptop del administrador

#### IP Whitelisting
```bash
# Security Group SSH rule
Source: <MI_IP>/32  # NO 0.0.0.0/0
```

### 4. Usuario No-Root

Todos los servicios corren como usuario `appuser`:

```bash
# Crear usuario sin privilegios
sudo useradd -m -s /bin/bash appuser

# Servicios systemd
[Service]
User=appuser
Group=appuser
```

**Beneficios:**
- Limita daño en caso de compromiso
- Mejora auditoría (logs específicos por usuario)
- Previene modificaciones accidentales del sistema

### 5. Updates de Seguridad

#### Automatización Parcial
```bash
# En cada instancia EC2
sudo apt update
sudo apt upgrade -y  # Aplicar parches de seguridad
```

#### Dependencias Python
```bash
# Revisar vulnerabilidades conocidas
poetry check

# Actualizar paquetes con vulnerabilidades
poetry update <paquete>
```

### 6. Logs y Auditoría

#### Centralización con journald
```bash
# Ver logs de servicios
sudo journalctl -u fastapi -f
sudo journalctl -u celery --since "1 hour ago"

# Logs de SSH
sudo journalctl -u ssh
```

#### Retención
```bash
# /etc/systemd/journald.conf
SystemMaxUse=1G
MaxRetentionSec=1month
```

---

## Escalabilidad y Mejoras Futuras

### Limitaciones Actuales

1. **Single Point of Failure (SPOF)**
   - Web Server único: Si cae, toda la API es inaccesible
   - File Server único: Si cae, no se pueden subir/procesar videos
   - Redis en Web Server: Si se reinicia, se pierden tareas encoladas

2. **Capacidad Limitada**
   - 1 Web Server: ~50-100 usuarios concurrentes
   - 1 Worker: ~4-6 videos en paralelo (con concurrency=2)
   - db.t3.micro: ~50 conexiones simultáneas

3. **Sin Alta Disponibilidad**
   - RDS Single-AZ: ~10-15 min de downtime en fallo de zona
   - Sin backups automáticos: Pérdida de datos en fallo catastrófico

### Roadmap de Escalabilidad

#### Fase 1: Escalado Horizontal Básico (Corto Plazo)

```
                    ┌─────────────────┐
                    │  Elastic Load   │
                    │    Balancer     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │Web Server 1│  │Web Server 2│  │Web Server 3│
     └────────────┘  └────────────┘  └────────────┘
```

**Cambios:**
1. Agregar **Application Load Balancer** (ALB)
   - Distribuir tráfico entre múltiples Web Servers
   - Health checks automáticos
   - Sticky sessions para WebSocket (futuro)

2. Separar **Redis a instancia dedicada** o **ElastiCache**
   - Evitar SPOF del broker
   - Mejor rendimiento

3. Agregar **2-3 Workers adicionales**
   - Procesar más videos en paralelo
   - Reducir tiempo de espera de usuarios

**Costo estimado:** +$80-120/mes

#### Fase 2: Alta Disponibilidad (Mediano Plazo)

```
        ┌───────────────────────────────────┐
        │         CloudFront CDN            │
        │  (Distribución global de videos)  │
        └──────────────┬────────────────────┘
                       │
        ┌──────────────▼────────────────┐
        │    Application Load Balancer  │
        │       (Multi-AZ)              │
        └──────────────┬────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │                           │
    ┌────▼────┐                 ┌────▼────┐
    │  AZ 1   │                 │  AZ 2   │
    │         │                 │         │
    │ Web x2  │                 │ Web x2  │
    │ Worker  │                 │ Worker  │
    └─────────┘                 └─────────┘
         │                           │
         └────────────┬──────────────┘
                      │
              ┌───────▼────────┐
              │   RDS Multi-AZ │
              │   Primary + DR │
              └────────────────┘
```

**Cambios:**
1. **RDS Multi-AZ**
   - Sincronización automática a AZ secundaria
   - Failover automático en < 2 minutos
   - RTO: ~2 min, RPO: ~0 segundos

2. **Auto Scaling Groups**
   - Escalar Web Servers automáticamente según CPU/memoria
   - Min: 2, Max: 6, Desired: 2

3. **Amazon S3 + CloudFront**
   - Migrar videos procesados a S3
   - Servir videos desde CDN global
   - Reducir carga en File Server

4. **ElastiCache Redis Cluster**
   - Modo cluster con réplicas
   - Automatic failover

**Costo estimado:** +$200-300/mes

#### Fase 3: Arquitectura Global (Largo Plazo)

```
                    ┌──────────────────┐
                    │   Route 53 DNS   │
                    │  Geolocation     │
                    │  Routing         │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
              ▼                             ▼
    ┌──────────────────┐          ┌──────────────────┐
    │  US-EAST (Main)  │          │  SA-EAST (BR)    │
    │                  │          │                  │
    │  ALB + ASG       │          │  ALB + ASG       │
    │  RDS Multi-AZ    │          │  RDS Read Replica│
    │  ElastiCache     │          │  ElastiCache     │
    └──────────────────┘          └──────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │   S3 Global     │
                    │ Cross-Region    │
                    │  Replication    │
                    └─────────────────┘
```

**Cambios:**
1. **Multi-Region Deployment**
   - Región principal: us-east-1 (Virginia)
   - Región secundaria: sa-east-1 (São Paulo)
   - Latencia reducida para usuarios de LATAM

2. **RDS Read Replicas**
   - Lectura local en cada región
   - Escrituras centralizadas en us-east-1

3. **S3 Cross-Region Replication**
   - Videos disponibles en todas las regiones
   - Resiliencia ante desastre regional

4. **Kubernetes (EKS)**
   - Migrar de instancias EC2 a contenedores orquestados
   - Deployment más ágil
   - Mejor utilización de recursos

**Costo estimado:** +$500-800/mes

### Tabla Comparativa de Fases

| Aspecto | Actual | Fase 1 | Fase 2 | Fase 3 |
|---------|--------|--------|--------|--------|
| **Disponibilidad** | 95% | 98% | 99.5% | 99.9% |
| **RTO** | Manual (~1h) | 15 min | 2 min | < 1 min |
| **RPO** | No backups | 5 min | 0 | 0 |
| **Usuarios concurrentes** | 50-100 | 200-300 | 500-1000 | 5000+ |
| **Videos/hora** | ~10-20 | ~50-100 | ~200-500 | ~1000+ |
| **Latencia (p95)** | 200ms | 150ms | 100ms | 50ms |
| **Costo mensual** | $60 | $160 | $360 | $860 |

### Métricas para Decidir Escalar

#### Cuándo aplicar Fase 1:
- CPU de Web Server > 70% sostenido por > 1 hora
- Cola de Celery > 20 tareas pendientes por > 30 minutos
- Usuarios concurrentes > 80 de forma regular
- Tiempo de respuesta p95 > 500ms

#### Cuándo aplicar Fase 2:
- Downtime histórico > 1 hora/mes
- Usuarios concurrentes > 250
- Requerimiento contractual de SLA 99%+
- Videos procesados > 500/día

#### Cuándo aplicar Fase 3:
- Usuarios en múltiples países con alta latencia
- Requerimiento de disaster recovery regional
- Volumen > 10,000 videos/mes
- Revenue justifica la inversión

---

## Conclusiones

### Logros de la Migración

1. ✅ **Infraestructura cloud desplegada**: 3 instancias EC2 + RDS configurados y operativos
2. ✅ **Desacoplamiento de componentes**: Mayor resiliencia y escalabilidad independiente
3. ✅ **Base de datos administrada**: Reducción de overhead operacional con RDS
4. ✅ **Automatización de despliegue**: Scripts bash reproducibles para cada componente
5. ✅ **Seguridad mejorada**: Security Groups, usuarios no-root, credenciales protegidas

### Lecciones Aprendidas

1. **Configuración de red es crítica**: Los Security Groups deben configurarse correctamente antes de instalar servicios
2. **NFS requiere planificación**: Las IPs privadas deben conocerse antes de configurar exports
3. **systemd es poderoso**: Simplifica la gestión de servicios y proporciona logging robusto
4. **Variables de entorno son clave**: Facilitan la configuración entre entornos (dev/staging/prod)
5. **Testing incremental**: Verificar cada componente antes de pasar al siguiente ahorra tiempo

### Próximos Pasos

1. **Implementar monitoring**: CloudWatch para métricas de EC2, RDS y application logs
2. **Configurar alarmas**: Notificaciones de CPU, memoria, disco, errores de aplicación
3. **Backups automáticos**: Habilitar en RDS y snapshots de EBS
4. **Pruebas de carga**: Validar límites de capacidad actuales
5. **Documentar runbooks**: Procedimientos para incidentes comunes
6. **CI/CD pipeline**: GitHub Actions para deploy automático a AWS

---

**Documento actualizado**: 2025-10-26
**Versión**: 2.0
**Autor**: Equipo ANB Rising Stars
