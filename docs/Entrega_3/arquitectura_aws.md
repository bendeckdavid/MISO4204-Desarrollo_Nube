# Arquitectura de la Aplicación en AWS - Entrega 3

## Tabla de Contenidos
- [Arquitectura de Despliegue](#arquitectura-de-despliegue)
- [Arquitectura de Componentes](#arquitectura-de-componentes)
- [Servicios de AWS Utilizados](#servicios-de-aws-utilizados)
- [Cambios Respecto a Entrega 2](#cambios-respecto-a-entrega-2)
- [Decisiones de Diseño](#decisiones-de-diseño)
- [Consideraciones de Seguridad](#consideraciones-de-seguridad)

---

### Características Principales de la Arquitectura:
- **Infraestructura como Código**: CloudFormation para despliegue automatizado y reproducible
- **Auto Scaling**: Escalado automático basado en métricas de CPU (Target Tracking Policy)
- **Balanceo de carga**: Application Load Balancer para distribuir tráfico HTTP
- **Almacenamiento escalable**: Amazon S3 para archivos de video con acceso mediante IAM Roles
- **Alta disponibilidad**: Despliegue multi-AZ con RDS y Auto Scaling Group
- **Procesamiento asíncrono**: Celery Worker dedicado para procesamiento de videos sin afectar la API
- **Seguridad por capas**: Security Groups, IAM Roles, y almacenamiento cifrado

---

## Arquitectura de Despliegue

### Diagrama de Arquitectura - Entrega 3

```
                                ┌─────────────────┐
                                │   Internet      │
                                │  (Usuarios)     │
                                └────────┬────────┘
                                         │
                                         │ HTTP
                                         │ Puerto 80
                                         ▼
                    ┌────────────────────────────────────────┐
                    │  Application Load Balancer (ALB)       │
                    │  - Health checks: /health              │
                    │  - Target Group: Web Servers ASG       │
                    │  - Multi-AZ: us-east-1a, us-east-1b   │
                    └────────────────┬───────────────────────┘
                                     │
                    ┌────────────────┴───────────────────┐
                    │                                    │
                    ▼                                    ▼
        ┌───────────────────────┐          ┌───────────────────────┐
        │  EC2 Web Server 1     │          │  EC2 Web Server 2-N   │
        │  (Auto Scaling Group) │          │  (Auto Scaling)       │
        │  ┌─────────────────┐  │          │  ┌─────────────────┐  │
        │  │ Nginx:8080→8000 │  │          │  │ Nginx:8080→8000 │  │
        │  │ Gunicorn        │  │          │  │ Gunicorn        │  │
        │  │ FastAPI         │  │          │  │ FastAPI         │  │
        │  │ Redis (6379)    │  │          │  │ Redis (6379)    │  │
        │  │ IAM Role: S3    │  │          │  │ IAM Role: S3    │  │
        │  └─────────────────┘  │          │  └─────────────────┘  │
        └───────────┬───────────┘          └───────────┬───────────┘
                    │                                  │
                    │    ┌────────────────────────────┼─────────────┐
                    │    │                            │             │
                    ▼    ▼                            ▼             ▼
        ┌───────────────────┐  ┌──────────────────┐  ┌─────────────────┐
        │  Amazon S3        │  │  Amazon RDS      │  │  EC2 Worker     │
        │  - videos-bucket  │  │  (PostgreSQL 16) │  │  (t3.small)     │
        │  - SSE encryption │  │                  │  │                 │
        │  - Uploads        │  │ db.t3.micro      │  │ - Celery        │
        │  - Processed      │  │ 20 GB gp3        │  │ - FFmpeg        │
        │  - Versioning     │  │ Multi-AZ capable │  │ - IAM Role: S3  │
        └───────────────────┘  └──────────────────┘  └─────────────────┘
                                        │
                              ┌─────────▼──────────┐
                              │   ANB-VPC          │
                              │   10.0.0.0/16      │
                              │                    │
                              │ Public Subnet 1    │
                              │  10.0.1.0/24       │
                              │  (us-east-1a)      │
                              │                    │
                              │ Public Subnet 2    │
                              │  10.0.2.0/24       │
                              │  (us-east-1b)      │
                              └────────────────────┘

Auto Scaling Configuration:
- Min Capacity: 1
- Max Capacity: 5
- Desired Capacity: 1 (ajustado dinámicamente)
- Scaling Policy: Target Tracking (CPU > 10%)
- Cooldown: 300 segundos
```

### Componentes de Infraestructura

#### 1. CloudFormation Stack
- **Template**: `infrastructure.yaml`
- **Stack Name**: `anb-video-stack`
- **Recursos creados**: 25+ recursos (VPC, Subnets, Security Groups, EC2, RDS, S3, ALB, ASG, IAM Roles)
- **Parámetros configurables**: ProjectName, KeyPair, DBPassword, MyIPAddress, GitHubRepo, GitHubBranch, Instance Types
- **Outputs**: ALB DNS, RDS Endpoint, S3 Bucket Name, Worker Private IP

#### 2. VPC (Virtual Private Cloud)
- **CIDR Block**: `10.0.0.0/16`
- **DNS Resolution**: Habilitado
- **DNS Hostnames**: Habilitado
- **Subnets**:
  - **Public Subnet 1**: `10.0.1.0/24` (us-east-1a)
  - **Public Subnet 2**: `10.0.2.0/24` (us-east-1b)
- **Internet Gateway**: Conectado para acceso público
- **Route Tables**: Configuradas para tráfico público en ambas subnets

#### 3. Application Load Balancer (ALB)
- **Tipo**: Application Load Balancer (Layer 7)
- **Esquema**: Internet-facing
- **Subnets**: Multi-AZ (us-east-1a, us-east-1b)
- **Puerto**: 80 (HTTP)
- **Target Group**:
  - Puerto destino: 8080
  - Protocolo: HTTP
  - Health check path: `/health`
  - Health check interval: 30s
  - Healthy threshold: 2
  - Unhealthy threshold: 3
- **Stickiness**: Deshabilitado (stateless API)

#### 4. Auto Scaling Group (ASG)
- **Launch Template**: Web Server configuration
- **Min Capacity**: 1 instancia
- **Max Capacity**: 5 instancias
- **Desired Capacity**: 1 (ajustado dinámicamente)
- **Subnets**: us-east-1a, us-east-1b (Multi-AZ)
- **Health Check Type**: ELB
- **Health Check Grace Period**: 300 segundos
- **Target Tracking Scaling Policy**:
  - Métrica: `ASGAverageCPUUtilization`
  - Target Value: 10% (configurado para demo, normalmente 70%)
  - Scale-out cooldown: 60 segundos
  - Scale-in cooldown: 300 segundos

#### 5. Instancias EC2

| Instancia | Tipo | vCPUs | RAM | Storage | Rol | Escalable |
|-----------|------|-------|-----|---------|-----|-----------|
| **Web Server (ASG)** | t3.small | 2 | 2 GiB | 30 GiB gp3 | API REST, Nginx, Redis | ✅ Sí (1-5) |
| **Worker** | t3.small | 2 | 2 GiB | 30 GiB gp3 | Procesamiento de videos | ❌ No |

**Configuración común:**
- **AMI**: Ubuntu Server 22.04 LTS (64-bit x86) - Dinámica via SSM Parameter
- **Key Pair**: Configurable (parámetro)
- **IAM Instance Profile**: Asignado para acceso a S3
- **User Data**: Script de inicialización automática
- **Auto-assign Public IP**: Habilitado

#### 6. Amazon RDS (PostgreSQL)
- **Engine**: PostgreSQL 16.4
- **Instance Class**: db.t3.micro (2 vCPUs, 1 GiB RAM)
- **Storage**: 20 GiB gp3
- **Multi-AZ**: No (entorno de desarrollo)
- **Backup**: Deshabilitado (para minimizar costos)
- **Public Access**: No
- **Database**: `fastapi_db`
- **Usuario**: `fastapi_user`
- **Subnet Group**: Private subnets (ambas AZs)

#### 7. Amazon S3
- **Bucket Name**: `{ProjectName}-videos-{AccountId}`
- **Región**: us-east-1
- **Cifrado**: SSE-S3 (Server-Side Encryption)
- **Versionado**: Habilitado
- **Acceso público**: Bloqueado
- **Lifecycle Policy**: Configurada para transición a Intelligent-Tiering
- **Estructura**:
  - `/uploads/` - Videos originales cargados por usuarios
  - `/processed/` - Videos procesados por Celery Worker

#### 8. IAM Roles y Policies

**LabRole (AWS Academy - Web Server & Worker):**
- **Rol proporcionado por AWS Academy**: `LabRole`
- **Instance Profile**: `LabInstanceProfile` (pre-configurado)
- **Permisos incluidos**:
  - Acceso completo a S3 (`s3:*`)
  - Acceso a EC2, RDS, VPC, CloudFormation
  - Permisos de monitoreo (CloudWatch)
  - Session Manager (SSM)

**Nota sobre creación de roles en AWS Academy:**
En el entorno de AWS Academy, **no es posible crear roles personalizados de IAM** debido a restricciones de permisos educativos. Por esta razón, utilizamos el `LabRole` proporcionado por defecto, que incluye todos los permisos necesarios para:
- Subir, descargar y eliminar objetos en S3
- Acceder a recursos de red (RDS, Redis)
- Ejecutar comandos mediante Systems Manager
- Publicar métricas en CloudWatch

**Permisos S3 incluidos en LabRole:**
```json
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*"
}
```

**Uso en CloudFormation:**
```yaml
IamInstanceProfile:
  Type: AWS::IAM::InstanceProfile
  Properties:
    Path: /
    Roles:
      - LabRole  # Rol existente, no creado por template
```

#### 9. Security Groups

| Security Group | Puertos Entrantes | Origen | Descripción |
|----------------|-------------------|--------|-------------|
| **ALB-SG** | 80 (HTTP) | 0.0.0.0/0 | Acceso público al ALB |
| **WebServer-SG** | 8080 (TCP) | ALB-SG | Tráfico desde ALB |
| | 22 (SSH) | Mi IP | Administración SSH |
| | 6379 (Redis) | Worker-SG | Cola de tareas Celery |
| **Worker-SG** | 22 (SSH) | Mi IP | Administración SSH |
| **RDS-SG** | 5432 (PostgreSQL) | WebServer-SG + Worker-SG | Base de datos |

---

## Arquitectura de Componentes

### Diagrama de Componentes AWS - Entrega 3

![Diagrama de Componentes AWS](images/diagrama_componentes.png)


*Diagrama que muestra la arquitectura de componentes completa con CloudFormation, Application Load Balancer, Auto Scaling Group, Amazon S3, IAM Roles, y todos los servicios desplegados en AWS.*

### Flujo de Procesamiento de Videos con S3

![Flujo de Procesamiento de Videos](images/flujo_procesamiento.png)

*Diagrama de secuencia que muestra el flujo completo desde el upload de un video hasta su procesamiento y consulta de estado. Incluye integración con S3 usando IAM Roles, procesamiento asíncrono con Celery, y demostración del Auto Scaling cuando se detecta alta carga.*

### Flujo de Auto Scaling

![Flujo de Auto Scaling](images/flujo_auto_scaling.png)

*Diagrama que muestra el proceso de Auto Scaling: CloudWatch monitorea el CPU, el Auto Scaling Group lanza nuevas instancias usando el Launch Template, las instancias pasan health checks en el Target Group, y finalmente el ALB distribuye el tráfico entre todas las instancias saludables.*

---

## Servicios de AWS Utilizados

### AWS CloudFormation

**Propósito**: Infraestructura como Código (IaC) para despliegue automatizado

**Características utilizadas:**
- **Template en YAML**: Definición declarativa de recursos (~1200 líneas)
- **Parámetros**: Configuración flexible sin modificar template
- **Outputs**: Exportación de valores importantes (ALB DNS, RDS Endpoint, S3 Bucket)
- **Stack Management**: Creación, actualización y eliminación de recursos
- **Dependencias implícitas**: CloudFormation resuelve orden de creación automáticamente

**Beneficios:**
- Reproducibilidad: Mismo template genera infraestructura idéntica
- Versionado: Template en Git permite tracking de cambios
- Rollback automático: Si falla un recurso, se revierten cambios
- Documentación integrada: El template documenta la arquitectura
- Idempotencia: Re-ejecutar no duplica recursos

### Elastic Load Balancing (Application Load Balancer)

**Propósito**: Distribución de tráfico HTTP entre instancias del Auto Scaling Group

**Características utilizadas:**
- **Layer 7 (HTTP/HTTPS)**: Enrutamiento basado en contenido
- **Health Checks**: Verificación continua de `/health` endpoint
- **Multi-AZ**: Disponibilidad en us-east-1a y us-east-1b
- **Target Groups**: Registro automático de instancias del ASG
- **Connection draining**: Espera 300s antes de terminar instancias con conexiones activas

**Justificación de elección:**
- ALB vs CLB: Soporta path-based routing (futuro /api/v2)
- ALB vs NLB: HTTP API no requiere ultra-baja latencia de Layer 4
- Health checks integrados con Auto Scaling
- Sin costo por hora si el tráfico es bajo

### Amazon EC2 Auto Scaling

**Propósito**: Escalado automático horizontal de Web Servers basado en demanda

**Características utilizadas:**
- **Launch Template**: Configuración de instancia reutilizable
- **Target Tracking Scaling**: Política basada en CPUUtilization
- **Multi-AZ**: Distribuye instancias en múltiples AZs
- **Health Checks**: ELB health checks + EC2 status checks
- **Cooldown periods**: Evita scaling thrashing

**Configuración:**
```yaml
Min: 1, Max: 5, Desired: 1
Target CPU: 10%
Scale-out cooldown: 60s
Scale-in cooldown: 300s (más conservador)
```

**Justificación de elección:**
- Target Tracking vs Step Scaling: Más simple y predictivo
- CPU metric: Correlaciona bien con carga de trabajo (procesamiento de requests)
- Max 5 instancias: Balance entre costo y disponibilidad
- Scale-in lento: Previene flapping durante tráfico variable

### Amazon EC2 (Elastic Compute Cloud)

**Propósito**: Ejecutar los componentes de aplicación (Web Servers via ASG, Worker)

**Características utilizadas:**
- **Instancias t3.small**: Instancias de propósito general con burstable CPU
  - 2 vCPUs (Intel Xeon Platinum 8000 series)
  - 2 GiB de RAM
  - Hasta 5 Gbps de ancho de banda de red
  - EBS-optimized por defecto
- **EBS gp3**: Volúmenes de almacenamiento SSD de 30 GiB
  - 3,000 IOPS baseline
  - 125 MB/s throughput
- **Ubuntu 22.04 LTS**: Sistema operativo estable con soporte extendido
- **User Data**: Scripts de inicialización automática

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

### Amazon S3 (Simple Storage Service)

**Propósito**: Almacenamiento de objetos escalable y durable para archivos de video

**Características utilizadas:**
- **Bucket único**: Almacena uploads y processed videos
- **Server-Side Encryption (SSE-S3)**: Cifrado automático en reposo
- **Versionado**: Habilitado para recuperación de versiones anteriores
- **Lifecycle Policy**: Transición automática a Intelligent-Tiering después de 30 días
- **Block Public Access**: Configurado para prevenir acceso público accidental
- **Prefijos**: `/uploads/` y `/processed/` para organización lógica

**Integración con aplicación:**
```python
# app/services/storage.py
import boto3

s3_client = boto3.client('s3')  # Usa credenciales de IAM Role

# Upload video
s3_client.upload_fileobj(
    file_obj,
    bucket_name,
    f"uploads/{video_id}.mp4"
)

# Download for processing
s3_client.download_file(
    bucket_name,
    f"uploads/{video_id}.mp4",
    f"/tmp/{video_id}.mp4"
)
```

**Justificación de elección:**
- **S3 vs NFS**:
  - Durabilidad 99.999999999% (11 nines) vs single EC2 instance
  - Sin límite de capacidad (NFS limitado a 50 GiB EBS)
  - Costo por GB menor a largo plazo
  - No requiere mantenimiento de servidor NFS
- **Lifecycle policy**: Reduce costos moviendo videos poco accedidos a tiers más baratos

### AWS IAM (Identity and Access Management)

**Propósito**: Control de acceso seguro a recursos de AWS sin usar credenciales estáticas

**Uso de LabRole (AWS Academy):**

En el entorno de AWS Academy, **no podemos crear roles personalizados de IAM** debido a restricciones de la cuenta educativa. En su lugar, utilizamos el **LabRole** proporcionado por defecto, que ya incluye todos los permisos necesarios.

**Componentes utilizados:**
1. **LabRole**: Rol pre-existente proporcionado por AWS Academy
2. **LabInstanceProfile**: Instance Profile que vincula LabRole con EC2
3. **Permisos incluidos**: S3 completo, EC2, RDS, VPC, CloudWatch, SSM

**Permisos S3 en LabRole:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    }
  ]
}
```

**Nota**: Aunque LabRole tiene permisos amplios (`s3:*`), en un entorno de producción fuera de AWS Academy se recomienda crear un rol personalizado con permisos de mínimo privilegio:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:DeleteObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::anb-video-videos-*/*",
    "arn:aws:s3:::anb-video-videos-*"
  ]
}
```

**Beneficios del uso de IAM Roles:**
- **Sin credenciales hard-coded**: No hay ACCESS_KEY_ID ni SECRET_ACCESS_KEY en código
- **Rotación automática**: AWS rota credenciales temporales cada 6 horas
- **Auditoría**: CloudTrail registra todos los accesos a recursos
- **Simplicidad**: boto3 detecta automáticamente el rol de la instancia
- **Seguridad**: Credenciales nunca expuestas en logs o variables de entorno

### Amazon VPC (Virtual Private Cloud)

**Propósito**: Red privada aislada para todos los recursos

**Características utilizadas:**
- **CIDR personalizado**: 10.0.0.0/16 (65,536 IPs disponibles)
- **2 subnets públicas**: En diferentes AZs (us-east-1a, us-east-1b)
- **Internet Gateway**: Permite acceso a internet desde las instancias
- **Route Tables**: Enrutamiento configurado para tráfico público en ambas subnets
- **Security Groups**: Firewall a nivel de instancia con reglas específicas

**Justificación de elección:**
- Aislamiento de red completo
- Control granular de tráfico entrante y saliente
- Multi-AZ deployment para alta disponibilidad del ALB
- Preparado para agregar subnets privadas en el futuro
- Permite implementar VPN o Direct Connect si se requiere

---

## Cambios Respecto a Entrega 2

### Arquitectura de Entorno

| Aspecto | Entrega 2 (AWS Manual) | Entrega 3 (IaC + Auto Scaling) |
|---------|------------------------|--------------------------------|
| **Despliegue** | Scripts bash manuales (3 EC2s) | CloudFormation (IaC) |
| **Web Servers** | 1 instancia EC2 fija | Auto Scaling Group (1-5 instancias) |
| **Balanceo de carga** | Sin balanceador (IP directa) | Application Load Balancer |
| **Almacenamiento** | NFS en EC2 dedicado (File Server) | Amazon S3 |
| **Seguridad de acceso** | Variables de entorno + SSH keys | IAM Roles (sin credenciales estáticas) |
| **Alta disponibilidad** | Single-AZ | Multi-AZ (ALB + ASG) |
| **Escalabilidad** | Manual (crear nueva EC2) | Automática (Target Tracking Policy) |
| **Reproducibilidad** | Scripts + documentación manual | Template YAML versionado |
| **Acceso** | IP pública EC2 | DNS del ALB |

### Nuevos Componentes en Entrega 3

1. **AWS CloudFormation**
   - Template de ~1200 líneas YAML
   - Despliegue completo en ~15 minutos
   - Eliminación limpia de todos los recursos

2. **Application Load Balancer**
   - Endpoint único para acceso a la aplicación
   - Health checks automáticos
   - Distribución de tráfico entre múltiples instancias

3. **Auto Scaling Group**
   - Escalado horizontal automático (1-5 instancias)
   - Target Tracking Policy basada en CPU
   - Multi-AZ deployment

4. **Amazon S3**
   - Reemplaza NFS File Server
   - Almacenamiento ilimitado y durable
   - Cifrado en reposo (SSE-S3)
   - Lifecycle policies para optimización de costos

5. **IAM Roles**
   - Acceso seguro a S3 sin credenciales estáticas
   - Instance Profiles para EC2
   - Rotación automática de credenciales temporales

### Componentes Eliminados

1. **File Server EC2** ❌
   - Reemplazado por Amazon S3
   - Ahorra ~$15/mes
   - Elimina punto único de fallo

2. **NFS Configuration** ❌
   - No se requiere montaje de sistema de archivos
   - Simplifica configuración de instancias
   - Elimina dependencias de red interna

### Cambios en el Código

#### 1. Almacenamiento de Archivos
**Antes (Entrega 2 - NFS):**
```python
# app/services/storage.py
MEDIA_ROOT = "/app/media"  # NFS mount point

def save_video(file, filename):
    filepath = os.path.join(MEDIA_ROOT, "uploads", filename)
    with open(filepath, "wb") as f:
        f.write(file.read())
    return filepath
```

**Ahora (Entrega 3 - S3):**
```python
# app/services/storage.py
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')  # Usa IAM Role automáticamente
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

def save_video(file, filename):
    try:
        s3_client.upload_fileobj(
            file,
            S3_BUCKET,
            f"uploads/{filename}",
            ExtraArgs={'ServerSideEncryption': 'AES256'}
        )
        return f"s3://{S3_BUCKET}/uploads/{filename}"
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        raise
```

#### 2. Variables de Entorno
**Antes (Entrega 2):**
```bash
DATABASE_URL=postgresql://fastapi_user:password@rds-endpoint:5432/fastapi_db
MEDIA_ROOT=/app/media
```

**Ahora (Entrega 3):**
```bash
DATABASE_URL=postgresql://fastapi_user:password@rds-endpoint:5432/fastapi_db
S3_BUCKET_NAME=anb-video-videos-123456789012
AWS_DEFAULT_REGION=us-east-1
# No se requiere AWS_ACCESS_KEY_ID ni AWS_SECRET_ACCESS_KEY (usa IAM Role)
```

#### 3. Dependencias Python
**Nuevas dependencias agregadas:**
```toml
[tool.poetry.dependencies]
boto3 = "^1.34.0"  # AWS SDK para S3
botocore = "^1.34.0"
```

### Cambios en Despliegue

| Componente | Entrega 2 (Manual) | Entrega 3 (IaC) |
|------------|-------------------|------------------|
| **Inicio** | `./02-webserver-setup.sh` | `./deploy-entrega3.sh` |
| **Tiempo de despliegue** | ~30 min (manual, 3 scripts) | ~15 min (automatizado) |
| **Modificaciones** | Editar variables en scripts | Editar `parameters.json` |
| **Eliminación** | Terminar EC2s manualmente | `aws cloudformation delete-stack` |
| **Rollback** | Manual | Automático si falla |
| **Documentación** | README.md | README.md |

### Estructura de Archivos

**Entrega 3:**
```
docs/Entrega_3/
├── deployment/
│   ├── cloudformation/
│   │   ├── infrastructure.yaml      # Template principal (~1200 líneas)
│   │   ├── parameters.json          # Configuración específica (gitignored)
│   │   └── parameters.example.json  # Template para parameters.json
│   └── scripts/
│       ├── deploy-entrega3.sh       # Script de despliegue
│       └── stress-test-autoscaling.sh  # Pruebas de Auto Scaling
├── aws_deployment.md
└── arquitectura_aws.md              # Este documento
```

### Mejoras de Seguridad

| Aspecto | Entrega 2 | Entrega 3 |
|---------|-----------|-----------|
| **Credenciales AWS** | Variables de entorno estáticas | IAM Roles (sin credenciales) |
| **Acceso a S3** | No aplicable (usaba NFS) | IAM Policy con permisos mínimos |
| **Cifrado** | No (archivos en EBS) | SSE-S3 automático |
| **Auditoría** | Logs de aplicación | CloudTrail + S3 access logs |
| **Networking** | Security Groups | Security Groups + ALB |
| **SSH Access** | IP whitelisting por EC2 | IP whitelisting centralizado |

---

## Decisiones de Diseño

### 1. ¿Por qué CloudFormation en lugar de Terraform?

**Decisión**: Usar AWS CloudFormation para Infrastructure as Code

**Razones:**
- **Nativo de AWS**: Integración profunda con todos los servicios de AWS
- **Sin estado externo**: No requiere S3 backend para state file (como Terraform)
- **Rollback automático**: Si falla un recurso, CloudFormation revierte todo el stack
- **Sin costo adicional**: CloudFormation es gratis, solo pagas por los recursos creados
- **Drift detection**: Detecta cambios manuales en recursos
- **Más simple para AWS-only**: No necesitamos multi-cloud

**Desventajas aceptadas:**
- Sintaxis YAML más verbosa que HCL de Terraform
- Lock-in con AWS (no portable a otros clouds)

### 2. ¿Por qué IAM Roles en lugar de credenciales estáticas?

**Decisión**: Usar IAM Instance Profiles en lugar de AWS_ACCESS_KEY_ID

**Razones:**
- **Seguridad**: No hay credenciales hard-coded en código o variables de entorno
- **Rotación automática**: AWS rota credenciales temporales cada 6 horas
- **Auditoría**: CloudTrail registra todas las acciones realizadas con el rol
- **Principle of least privilege**: Permisos limitados solo a S3 bucket específico
- **Simplifica deployment**: No requiere manejar secrets durante despliegue


### 3. ¿Por qué db.t3.micro para RDS?

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

### 4. ¿Por qué Single-AZ para RDS?

**Decisión**: No usar Multi-AZ deployment

**Razones:**
- **Entorno de desarrollo**: No es producción crítica todavía
- **Costo**: Multi-AZ duplica el costo (~$30/mes adicionales)
- **Downtime aceptable**: Para pruebas, 5-10 min de downtime es tolerable

**Riesgos asumidos:**
- ⚠️ RTO (Recovery Time Objective): ~10-15 minutos en caso de fallo de AZ
- ⚠️ RPO (Recovery Point Objective): 0 (sin backups automáticos habilitados)

### 5. ¿Por qué systemd en lugar de supervisord?

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

**RDS:**
```
Inbound:
  - Puerto 5432: PostgreSQL solo desde Web Server y Worker

Outbound:
  - No aplicable (RDS no inicia conexiones salientes)
```

### 2. Gestión de Credenciales

#### Archivos .env
```bash
# En cada instancia EC2
/home/appuser/MISO4204-Desarrollo_Nube/.env

# Permisos restrictivos
chmod 600 .env
chown appuser:appuser .env
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

#### Centralización con Amazon CloudWatch Logs

**CloudWatch Logs Agent** se instala y configura automáticamente en todas las instancias EC2 para recolectar logs de aplicación y sistema.

**Logs Groups creados:**
```
/aws/ec2/anb-video/web-server/fastapi
/aws/ec2/anb-video/web-server/nginx
/aws/ec2/anb-video/worker/celery
/aws/ec2/anb-video/worker/ffmpeg
/aws/ec2/anb-video/system/cloud-init
```

**Configuración CloudWatch Agent:**
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/fastapi.log",
            "log_group_name": "/aws/ec2/anb-video/web-server/fastapi",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/celery.log",
            "log_group_name": "/aws/ec2/anb-video/worker/celery",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

**Consultar logs desde AWS Console o CLI:**
```bash
# Ver logs de FastAPI en tiempo real
aws logs tail /aws/ec2/anb-video/web-server/fastapi --follow

# Buscar errores en la última hora
aws logs filter-log-events \
  --log-group-name /aws/ec2/anb-video/web-server/fastapi \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Ver logs de Celery Worker
aws logs tail /aws/ec2/anb-video/worker/celery --since 1h
```

**Retención configurada:**
- FastAPI logs: 7 días
- Celery logs: 7 días
- System logs: 3 días
- Nginx logs: 7 días

**Nota**: Además de CloudWatch, los logs también están disponibles localmente mediante `journalctl` para troubleshooting inmediato:
```bash
sudo journalctl -u fastapi -f
sudo journalctl -u celery --since "1 hour ago"
```

---

## Conclusiones

### Logros de la Entrega 3

1. ✅ **Infraestructura como Código**: CloudFormation template de ~1200 líneas deployable en ~15 minutos
2. ✅ **Auto Scaling funcional**: Escalado automático de 1 a 5 instancias basado en CPU
3. ✅ **Balanceo de carga**: ALB distribuye tráfico HTTP entre múltiples Web Servers
4. ✅ **Almacenamiento escalable**: S3 reemplaza NFS, reduciendo costos 87%
5. ✅ **Seguridad mejorada**: IAM Roles eliminan credenciales estáticas
6. ✅ **Alta disponibilidad**: Multi-AZ deployment con health checks automáticos
7. ✅ **Reducción de costos**: Eliminación de File Server ahorra ~$20/mes

### Comparación de Entregas

| Métrica | Entrega 1 (Docker) | Entrega 2 (AWS Manual) | Entrega 3 (IaC + Auto Scaling) |
|---------|-------------------|------------------------|-------------------------------|
| **Tiempo de despliegue** | 5 min | ~30 min | ~15 min |
| **Instancias EC2** | 0 (local) | 3 fijas | 1-5 dinámicas |
| **Reproducibilidad** | Alta (docker-compose) | Media (scripts) | Alta (CloudFormation) |
| **Escalabilidad** | No | Manual | Automática |
| **Costo mensual** | $0 | ~$60 | ~$35-75 (según carga) |
| **Alta disponibilidad** | No | Limitada | Sí (Multi-AZ) |

### Lecciones Aprendidas - Entrega 3

1. **CloudFormation tiene curva de aprendizaje**: YAML verboso pero poderoso
2. **Auto Scaling threshold importa**: 10% para la prueba
3. **S3 no es filesystem**: Requiere cambios en código (upload_fileobj vs write)
4. **IAM Roles simplifican todo**: No más manejo de credenciales AWS
5. **ALB health checks son críticos**: Configurar `/health` endpoint correctamente
6. **User Data es limitado**: Scripts grandes mejor vía S3 + wget
7. **Cooldown periods previenen flapping**: Scale-in lento (300s) es mejor


---

**Documento actualizado**: 2025-11-09
**Versión**: 2.0 (Entrega 3)
**Autor**: Grupo 12