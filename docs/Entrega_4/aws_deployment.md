# Guía de Despliegue en AWS - Entrega 4 (SQS + Worker Auto Scaling)

Guía completa para desplegar la aplicación ANB Rising Stars Showcase en AWS utilizando **Infrastructure as Code (CloudFormation)**, con Application Load Balancer, Auto Scaling Groups (Web y Workers), **Amazon SQS**, Dead Letter Queue, y **Worker Auto Scaling** basado en profundidad de cola.

## Índice
- [Cambios Respecto a Entrega 3](#cambios-respecto-a-entrega-3)
- [Arquitectura Objetivo](#arquitectura-objetivo)
- [Prerrequisitos](#prerrequisitos)
- [Paso 1: Preparación Inicial](#paso-1-preparación-inicial)
- [Paso 2: Despliegue con CloudFormation](#paso-2-despliegue-con-cloudformation)
- [Paso 3: Verificación de la Infraestructura](#paso-3-verificación-de-la-infraestructura)
- [Paso 4: Pruebas Funcionales](#paso-4-pruebas-funcionales)
- [Gestión del Stack](#gestión-del-stack)
- [Troubleshooting](#troubleshooting)

---

## Cambios Respecto a Entrega 3

| Aspecto | Entrega 3 (Celery/Redis) | Entrega 4 (SQS + Worker ASG) |
|---------|--------------------------|------------------------------|
| **Cola de mensajes** | Redis (port 6379 en Web Server) | Amazon SQS (managed service) |
| **Task Broker** | Celery con Redis backend | SQS directo con boto3 |
| **Workers** | 1 instancia EC2 fija | Auto Scaling Group (1-3 instancias) |
| **Escalabilidad workers** | Manual | **Automática** basada en queue depth |
| **Persistencia** | Volátil (Redis RAM) | Durable (4 días retention) |
| **Dead Letter Queue** | No | **Sí** (14 días retention) |
| **Polling** | Celery beat | **Long polling** (20 segundos) |
| **Multi-AZ workers** | No | **Sí** (us-east-1a, us-east-1b) |
| **Observabilidad** | Logs manuales | CloudWatch metrics nativas |
| **Costo cola** | $0 (Redis incluido en EC2) | ~$0.40/mes (1M requests gratis) |
| **Mantenimiento** | Gestionar Redis en Web Server | Totalmente gestionado por AWS |

### Nuevos Componentes en Entrega 4
- **Amazon SQS Queue**: Cola principal para mensajes de procesamiento
- **Dead Letter Queue (DLQ)**: Almacena mensajes fallidos después de 3 intentos
- **Worker Auto Scaling Group**: Escalado automático de workers (1-3 instancias)
- **Worker Scaling Policy**: Target tracking basado en `ApproximateNumberOfMessagesVisible`
- **Long Polling**: Configurado con 20 segundos para reducir costos
- **CloudWatch Metrics**: Métricas de SQS integradas

### Componentes Eliminados
- **Redis en Web Server**: No se instala Redis (puerto 6379)
- **Celery y dependencias**: Eliminado `celery[redis]` de requirements
- **Worker EC2 fijo**: Reemplazado por Worker ASG dinámico
- **Manual scaling**: Ya no se escala workers manualmente

### Componentes que Permanecen
- CloudFormation (IaC)
- Application Load Balancer (ALB)
- Web Server Auto Scaling Group
- Amazon S3
- Amazon RDS (PostgreSQL)
- IAM Roles (LabRole)

---

## Arquitectura Objetivo

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
        │  EC2 Web Server 1     │          │  EC2 Web Server 2-3   │
        │  (Auto Scaling Group) │          │  (Auto Scaling)       │
        │  ┌─────────────────┐  │          │  ┌─────────────────┐  │
        │  │ Nginx:8080→8000 │  │          │  │ Nginx:8080→8000 │  │
        │  │ Gunicorn        │  │          │  │ Gunicorn        │  │
        │  │ FastAPI         │  │          │  │ FastAPI         │  │
        │  │ boto3 (S3+SQS)  │  │          │  │ boto3 (S3+SQS)  │  │
        │  │ IAM: LabRole    │  │          │  │ IAM: LabRole    │  │
        │  └─────────────────┘  │          │  └─────────────────┘  │
        └───────────┬───────────┘          └───────────┬───────────┘
                    │                                  │
                    └───────────┬──────────────────────┘
                                │
                    ┌───────────┼───────────────────────┐
                    │           │                       │
                    ▼           ▼                       ▼
        ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────────┐
        │  Amazon S3        │  │  Amazon RDS       │  │  Amazon SQS         │
        │  - Originals/     │  │  (PostgreSQL 15)  │  │                     │
        │  - Processed/     │  │  db.t3.micro      │  │  ┌────────────────┐ │
        │  - SSE encryption │  │  20 GB gp3        │  │  │ Processing     │ │
        └───────────────────┘  └───────────────────┘  │  │ Queue          │ │
                │                       │              │  │ - Long Poll    │ │
                │                       │              │  │   20s          │ │
                │                       │              │  │ - Visibility   │ │
                │                       │              │  │   15 min       │ │
                │                       │              │  │ - Retention    │ │
                │                       │              │  │   4 days       │ │
                │                       │              │  └────────┬───────┘ │
                │                       │              │           │ After   │
                │                       │              │           │ 3 fails │
                │                       │              │           ▼         │
                │                       │              │  ┌────────────────┐ │
                │                       │              │  │ Dead Letter    │ │
                │                       │              │  │ Queue (DLQ)    │ │
                │                       │              │  │ - Retention    │ │
                │                       │              │  │   14 days      │ │
                │                       │              │  └────────────────┘ │
                │                       │              └──────────┬──────────┘
                │                       │                         │
                │                       │                         │ Long Poll
                │                       │                         │ (20s)
                │                       │                         │
                │                       │         ┌───────────────┴────────────┐
                │                       │         │                            │
                │                       │         ▼                            ▼
                │                       │  ┌──────────────┐         ┌──────────────┐
                │                       │  │ EC2 Worker 1 │         │ EC2 Worker   │
                │                       │  │ (us-east-1a) │         │ 2-3          │
                │                       │  │              │         │ (us-east-1b) │
                │                       │  │ ┌──────────┐ │         │ ┌──────────┐ │
                │                       │  │ │SQS Worker│ │         │ │SQS Worker│ │
                │                       │  │ │FFmpeg    │ │         │ │FFmpeg    │ │
                │                       │  │ │MoviePy   │ │         │ │MoviePy   │ │
                │                       │  │ │boto3     │ │         │ │boto3     │ │
                │                       │  │ │LabRole   │ │         │ │LabRole   │ │
                │                       │  │ └──────────┘ │         │ └──────────┘ │
                │                       │  └──────────────┘         └──────────────┘
                │                       │         │                        │
                │                       │         │  (Auto Scaling)        │
                │                       │         │  Min: 1, Max: 3        │
                │                       │         │  Target: 5 msgs/worker │
                │                       │         │                        │
                └───────────────────────┴─────────┴────────────────────────┘

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
- Web Servers: Min 1, Max 3, Target CPU > 10%
- Workers: Min 1, Max 3, Target: 5 messages/worker
- Cooldown: 300 segundos (ambos ASG)
```

### Componentes Principales
- **CloudFormation**: Template YAML (~1400 líneas, 30+ recursos)
- **Application Load Balancer**: Distribuye tráfico HTTP
- **Web Server ASG**: 1-3 instancias (t3.small)
- **Worker ASG**: 1-3 instancias (t3.small) - **NUEVO**
- **Amazon SQS**: Cola de mensajes con DLQ - **NUEVO**
- **Amazon S3**: Almacenamiento de videos
- **Amazon RDS**: PostgreSQL 15 (db.t3.micro)
- **IAM Roles**: LabRole de AWS Academy para S3 + SQS

---

## Prerrequisitos

### En tu Máquina Local
- AWS CLI instalado y configurado
- Git con acceso al repositorio
- Bash shell
- Herramientas: `curl`, `jq` (opcional)

### Configuración AWS CLI con AWS Academy

AWS Academy proporciona credenciales temporales que deben ser configuradas en cada sesión.

**Obtener credenciales de AWS Academy:**

1. Ir a tu curso de AWS Academy
2. Clic en **AWS Details**
3. Clic en **Show** en AWS CLI credentials
4. Copiar las 3 líneas que aparecen:
   ```
   aws_access_key_id=...
   aws_secret_access_key=...
   aws_session_token=...
   ```

**Configurar credenciales en tu máquina:**

```bash
# Verificar que AWS CLI está instalado
aws --version

# Editar el archivo de credenciales
nano ~/.aws/credentials

# Pegar las credenciales en el formato:
[default]
aws_access_key_id = ASIA...
aws_secret_access_key = ...
aws_session_token = ...

# Configurar región (si no lo has hecho)
aws configure set region us-east-1
aws configure set output json

# Verificar que las credenciales funcionan
aws sts get-caller-identity
```

**Nota importante**: Las credenciales de AWS Academy expiran después de varias horas. Si recibes errores de autenticación, debes obtener nuevas credenciales desde AWS Academy y actualizar el archivo `~/.aws/credentials`.

---

## Paso 1: Preparación Inicial

### 1.1 Crear Key Pair

**Crear vía AWS Console**:
1. Ir a **EC2** → **Key Pairs** → **Create key pair**
2. Name: `anb-video-keypair`
3. Key pair type: RSA
4. File format: `.pem`
5. Descargar y guardar el archivo
6. `chmod 400 anb-video-keypair.pem`

### 1.2 Obtener tu IP Pública

```bash
# Obtener tu IP pública
curl -s ifconfig.me
```

Anota tu IP: `_______________`

### 1.3 Configurar Parameters File

```bash
cd docs/Entrega_4/deployment/cloudformation

# Copiar el ejemplo
cp parameters.example.json parameters.json

# Editar el archivo
nano parameters.json
```

**Configurar estos valores en `parameters.json`**:

```json
[
  {
    "ParameterKey": "ProjectName",
    "ParameterValue": "anb-video"
  },
  {
    "ParameterKey": "KeyPairName",
    "ParameterValue": "anb-video-keypair"
  },
  {
    "ParameterKey": "DBPassword",
    "ParameterValue": "TU_PASSWORD_SEGURO_AQUI"
  },
  {
    "ParameterKey": "MyIPAddress",
    "ParameterValue": "TU_IP_PUBLICA/32"
  },
  {
    "ParameterKey": "GitHubRepo",
    "ParameterValue": "https://github.com/bendeckdavid/MISO4204-Desarrollo_Nube.git"
  },
  {
    "ParameterKey": "GitHubBranch",
    "ParameterValue": "main"
  },
  {
    "ParameterKey": "WebServerInstanceType",
    "ParameterValue": "t3.small"
  },
  {
    "ParameterKey": "WorkerInstanceType",
    "ParameterValue": "t3.small"
  }
]
```

**Campos a personalizar**:
- `DBPassword`: Password seguro para RDS (ej: `FastApiDb2025Pass`)
- `MyIPAddress`: Tu IP pública con `/32` (ej: `191.111.47.209/32`)
- `GitHubBranch`: `main` (rama con código SQS)

---

## Paso 2: Despliegue con CloudFormation

### 2.1 Opción A: Despliegue con Script Automatizado (Recomendado)

```bash
cd docs/Entrega_4/deployment/scripts

# Ejecutar el script de despliegue
./deploy-entrega4.sh
```

El script te guiará interactivamente:

```
========================================
  CloudFormation Stack Deployment
  Entrega 4 - SQS + Worker Auto Scaling
========================================

Stack name: anb-video-stack-entrega4

Checking if parameters.json exists...
✓ Found parameters.json

Do you want to review parameters before deployment? (y/n) [n]: n

Starting stack deployment...
✓ Stack creation initiated successfully

Waiting for stack to be created (this takes ~15-20 minutes)...
...
```

⏳ **Esperar ~20 minutos** mientras CloudFormation crea todos los recursos.

### 2.2 Opción B: Despliegue Manual con AWS CLI

```bash
cd docs/Entrega_4/deployment/cloudformation

# Validar el template primero
aws cloudformation validate-template \
  --template-body file://infrastructure.yaml \
  --region us-east-1

# Crear el stack
aws cloudformation create-stack \
  --stack-name anb-video-stack-entrega4 \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Esperar a que se complete
aws cloudformation wait stack-create-complete \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1

echo "Stack created successfully!"
```

### 2.3 Monitorear el Despliegue

**Opción 1: AWS Console**
1. Ir a **CloudFormation** en AWS Console
2. Seleccionar el stack `anb-video-stack-entrega4`
3. Ver la pestaña **Events** para seguir el progreso
4. Deberías ver recursos siendo creados en este orden:
   - VPC, Subnets, Internet Gateway
   - Security Groups
   - SQS Queues (Processing Queue y DLQ)
   - RDS Instance
   - S3 Bucket
   - ALB, Target Groups
   - Launch Templates
   - Auto Scaling Groups (Web y Workers)

**Opción 2: AWS CLI**
```bash
# Ver eventos del stack
aws cloudformation describe-stack-events \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1 \
  --max-items 20

# Ver recursos creados
aws cloudformation describe-stack-resources \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1
```

---

## Paso 3: Verificación de la Infraestructura

### 3.1 Obtener Outputs del Stack

```bash
# Ver todos los outputs
aws cloudformation describe-stacks \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'

# Guardar outputs en variables
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
  --output text)

RDS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
  --output text)

S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text)

SQS_QUEUE_URL=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`SQSQueueURL`].OutputValue' \
  --output text)

SQS_DLQ_URL=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`SQSDLQURL`].OutputValue' \
  --output text)

echo "ALB DNS: $ALB_DNS"
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "S3 Bucket: $S3_BUCKET"
echo "SQS Queue URL: $SQS_QUEUE_URL"
echo "SQS DLQ URL: $SQS_DLQ_URL"
```

Anota estos valores:
- **ALB DNS**: `_______________`
- **RDS Endpoint**: `_______________`
- **S3 Bucket**: `_______________`
- **SQS Queue URL**: `_______________`
- **SQS DLQ URL**: `_______________`

### 3.2 Verificar Recursos Creados

**Opción 1: Verificar desde AWS Console (Recomendado)**

1. **CloudFormation**:
   - Ir a **CloudFormation** en AWS Console
   - Seleccionar el stack `anb-video-stack-entrega4`
   - Pestaña **Resources**: Ver todos los 30+ recursos creados
   - Pestaña **Outputs**: Ver ALB DNS, RDS Endpoint, S3 Bucket, SQS URLs
   - Pestaña **Events**: Ver historial completo de creación

2. **EC2 → Load Balancers**:
   - Ver el ALB `anb-video-alb`
   - Estado debe ser "Active"
   - DNS name disponible

3. **EC2 → Auto Scaling Groups**:
   - Ver el Web Server ASG: `anb-video-web-asg`
     - Desired capacity: 1
     - Instances: Al menos 1 running
   - Ver el Worker ASG: `anb-video-worker-asg` **[NUEVO]**
     - Desired capacity: 1
     - Instances: Al menos 1 running

4. **EC2 → Instances**:
   - Ver instancias con tag `Project: anb-video`
   - Al menos 2 instancias running (1 Web Server, 1 Worker)

5. **SQS → Queues** **[NUEVO]**:
   - Ver `anb-video-processing-queue`
   - Ver `anb-video-processing-dlq`
   - Verificar configuración:
     - Long polling: 20 segundos
     - Visibility timeout: 900 segundos (15 min)
     - Message retention: 4 días

6. **RDS → Databases**:
   - Ver `anb-video-db`
   - Status: Available

7. **S3 → Buckets**:
   - Ver bucket `anb-video-*`
   - Con carpetas `originals/` y `processed/`

**Opción 2: Verificar con AWS CLI**

#### Verificar SQS Queues (NUEVO)
```bash
# Ver atributos de la cola principal
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names All

# Ver atributos de la DLQ
aws sqs get-queue-attributes \
  --queue-url $SQS_DLQ_URL \
  --attribute-names All
```

#### Verificar Worker Auto Scaling Group (NUEVO)
```bash
# Ver detalles del Worker ASG
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names anb-video-worker-asg \
  --query 'AutoScalingGroups[0].[AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,length(Instances)]' \
  --output table

# Ver política de escalado de workers
aws autoscaling describe-policies \
  --auto-scaling-group-name anb-video-worker-asg \
  --query 'ScalingPolicies[*].[PolicyName,PolicyType,TargetTrackingConfiguration.TargetValue]' \
  --output table
```

#### Verificar Web Server Auto Scaling Group
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names anb-video-web-asg \
  --query 'AutoScalingGroups[0].[AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,length(Instances)]' \
  --output table
```

#### Verificar Application Load Balancer
```bash
aws elbv2 describe-load-balancers \
  --names anb-video-alb \
  --query 'LoadBalancers[0].[LoadBalancerName,DNSName,State.Code]' \
  --output table
```

#### Verificar Instancias EC2
```bash
# Listar instancias del proyecto
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=anb-video" \
            "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].[Tags[?Key==`Name`].Value|[0],InstanceId,PrivateIpAddress,PublicIpAddress,State.Name]' \
  --output table
```

#### Verificar RDS
```bash
aws rds describe-db-instances \
  --db-instance-identifier anb-video-db \
  --query 'DBInstances[0].[DBInstanceIdentifier,DBInstanceStatus,Endpoint.Address,Engine,DBInstanceClass]' \
  --output table
```

#### Verificar S3 Bucket
```bash
aws s3 ls s3://$S3_BUCKET/
# Deberías ver:
#   PRE originals/
#   PRE processed/
```

### 3.3 Health Check del ALB

```bash
# Health check básico
curl http://$ALB_DNS/health

# Debería responder:
# {"status":"healthy","database":"connected","storage":"available"}
```

### 3.4 Verificar Target Groups

```bash
# Ver targets registrados en el Web Server Target Group
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names anb-video-web-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text) \
  --query 'TargetHealthDescriptions[*].[Target.Id, TargetHealth.State]' \
  --output table
```

Deberías ver al menos 1 target con `State: healthy`.

### 3.5 Verificar CloudWatch Metrics de SQS (NUEVO)

```bash
# Ver métricas de la cola SQS
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=anb-video-processing-queue \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --output table
```

---

## Paso 4: Pruebas Funcionales con Postman

### 4.1 Importar Colección de Postman

**Paso 1: Abrir Postman**

1. Abrir Postman en tu máquina local
2. Si no lo tienes instalado, descargarlo desde [postman.com](https://www.postman.com/downloads/)

**Paso 2: Importar la colección**

1. En Postman, clic en **Import**
2. Seleccionar **File**
3. Navegar a `docs/Entrega_4/collections/entrega4_postman_collection.json`
4. Clic en **Import**

**Paso 3: Importar el environment**

1. Clic en **Import** nuevamente
2. Seleccionar `docs/Entrega_4/collections/entrega4_environment.json`
3. Clic en **Import**

### 4.2 Configurar Environment con ALB DNS

**Importante**: Debes actualizar la variable `base_url` con el DNS del ALB que obtuviste en el paso anterior.

1. En Postman, seleccionar el environment importado (esquina superior derecha)
2. Clic en el ícono del ojo 👁️ → **Edit**
3. Actualizar la variable `base_url`:
   - **Initial Value**: `http://<ALB_DNS_AQUI>`
   - **Current Value**: `http://<ALB_DNS_AQUI>`
   - Ejemplo: `http://anb-video-alb-1931734891.us-east-1.elb.amazonaws.com`
4. Clic en **Save**

### 4.3 Ejecutar las Pruebas en Postman

La colección incluye los siguientes requests:

#### 1. Health Check
- **Endpoint**: `GET {{base_url}}/health`
- Sin autenticación
- Verifica que el ALB y las instancias están funcionando

Respuesta esperada:
```json
{
  "status": "healthy",
  "database": "connected",
  "storage": "available"
}
```

#### 2. Signup (Registrar Usuario)
- **Endpoint**: `POST {{base_url}}/api/auth/signup`
- Body incluye: username, email, password
- Guarda automáticamente el `access_token` en el environment

#### 3. Login
- **Endpoint**: `POST {{base_url}}/api/auth/login`
- Body incluye: username, password
- Actualiza el `access_token` en el environment

#### 4. Upload Video
- **Endpoint**: `POST {{base_url}}/api/videos`
- Headers: `Authorization: Bearer {{access_token}}`
- Body: Form-data con archivo de video
- **Importante**: Este request envía mensaje a SQS

Respuesta esperada:
```json
{
  "id": "uuid-del-video",
  "title": "Mi Video",
  "description": "Descripción",
  "processing_status": "pending",
  "original_url": "https://s3.../originals/...",
  "created_at": "2025-01-13T..."
}
```

#### 5. List Videos
- **Endpoint**: `GET {{base_url}}/api/videos`
- Headers: `Authorization: Bearer {{access_token}}`
- Ver todos tus videos y su estado de procesamiento

#### 6. Get Video by ID
- **Endpoint**: `GET {{base_url}}/api/videos/{{video_id}}`
- Headers: `Authorization: Bearer {{access_token}}`
- Ver detalles de un video específico

### 4.4 Verificar Procesamiento con SQS

Después de subir un video, puedes verificar el procesamiento:

```bash
# Ver mensajes en la cola
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible

# ApproximateNumberOfMessages: Mensajes esperando procesamiento
# ApproximateNumberOfMessagesNotVisible: Mensajes siendo procesados (visibility timeout activo)
```

**Escenarios esperados:**

1. **Inmediatamente después del upload**:
   ```
   ApproximateNumberOfMessages: 1
   ApproximateNumberOfMessagesNotVisible: 0
   ```

2. **Worker procesando el video**:
   ```
   ApproximateNumberOfMessages: 0
   ApproximateNumberOfMessagesNotVisible: 1
   ```

3. **Después del procesamiento exitoso**:
   ```
   ApproximateNumberOfMessages: 0
   ApproximateNumberOfMessagesNotVisible: 0
   ```

### 4.5 Verificar Video Procesado en S3

```bash
# Ver archivos en S3
aws s3 ls s3://$S3_BUCKET/originals/ --human-readable --recursive
aws s3 ls s3://$S3_BUCKET/processed/ --human-readable --recursive
```

---

## Gestión del Stack

### Actualizar el Stack

Si necesitas modificar el template o parámetros:

```bash
cd docs/Entrega_4/deployment/cloudformation

# Editar parameters.json o infrastructure.yaml
nano parameters.json

# Actualizar el stack
aws cloudformation update-stack \
  --stack-name anb-video-stack-entrega4 \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Esperar a que termine la actualización
aws cloudformation wait stack-update-complete \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1
```

### Eliminar el Stack

```bash
# ADVERTENCIA: Esto eliminará TODOS los recursos
# Asegúrate de hacer backup de datos importantes

# Paso 1: Vaciar el bucket S3 (requerido)
aws s3 rm s3://$S3_BUCKET --recursive

# Paso 2: Purgar las colas SQS (opcional, se eliminan automáticamente)
aws sqs purge-queue --queue-url $SQS_QUEUE_URL
aws sqs purge-queue --queue-url $SQS_DLQ_URL

# Paso 3: Eliminar el stack
aws cloudformation delete-stack \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1

# Paso 4: Monitorear la eliminación
aws cloudformation wait stack-delete-complete \
  --stack-name anb-video-stack-entrega4 \
  --region us-east-1

echo "Stack deleted successfully!"
```

---


## Recursos Adicionales

### Documentos Relacionados
- [arquitectura_aws.md](arquitectura_aws.md) - Arquitectura detallada con SQS
- [infrastructure.yaml](deployment/cloudformation/infrastructure.yaml) - CloudFormation template
- [deploy-entrega4.sh](deployment/scripts/deploy-entrega4.sh) - Script de despliegue

### AWS Console Links
- [CloudFormation Stacks](https://console.aws.amazon.com/cloudformation/)
- [SQS Queues](https://console.aws.amazon.com/sqs/)
- [EC2 Auto Scaling Groups](https://console.aws.amazon.com/ec2autoscaling/)
- [CloudWatch Metrics](https://console.aws.amazon.com/cloudwatch/)

---

**Documento actualizado**: 2025-01-13
**Versión**: 4.0 (Entrega 4 - SQS + Worker Auto Scaling)
**Autor**: Grupo 12
