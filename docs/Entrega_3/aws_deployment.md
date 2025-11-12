# Guía de Despliegue en AWS - Entrega 3 (CloudFormation + Auto Scaling)

Guía completa para desplegar la aplicación ANB Rising Stars Showcase en AWS utilizando **Infrastructure as Code (CloudFormation)**, con Application Load Balancer, Auto Scaling Group, Amazon S3, y IAM Roles.

## Índice
- [Cambios Respecto a Entrega 2](#cambios-respecto-a-entrega-2)
- [Arquitectura Objetivo](#arquitectura-objetivo)
- [Prerrequisitos](#prerrequisitos)
- [Paso 1: Preparación Inicial](#paso-1-preparación-inicial)
- [Paso 2: Despliegue con CloudFormation](#paso-2-despliegue-con-cloudformation)
- [Paso 3: Verificación de la Infraestructura](#paso-3-verificación-de-la-infraestructura)
- [Paso 4: Pruebas Funcionales](#paso-4-pruebas-funcionales)
- [Paso 5: Pruebas de Auto Scaling](#paso-5-pruebas-de-auto-scaling)
- [Gestión del Stack](#gestión-del-stack)
- [Troubleshooting](#troubleshooting)

---

## Cambios Respecto a Entrega 2

| Aspecto | Entrega 2 (Manual) | Entrega 3 (IaC + Auto Scaling) |
|---------|-------------------|--------------------------------|
| **Despliegue** | Scripts bash manuales (3 EC2s) | CloudFormation template YAML |
| **Tiempo** | ~30-40 minutos (manual) | ~15 minutos (automatizado) |
| **Web Servers** | 1 instancia EC2 fija | Auto Scaling Group (1-3 instancias) |
| **Balanceo de carga** | Sin balanceador | Application Load Balancer |
| **Almacenamiento** | NFS en EC2 (File Server) | Amazon S3 |
| **Acceso a S3** | N/A | IAM Roles (LabRole en Academy) |
| **Alta disponibilidad** | Single-AZ | Multi-AZ (ALB + ASG) |
| **Escalabilidad** | Manual | Automática (Target Tracking - CPU) |
| **Eliminación** | Terminar EC2s manualmente | `aws cloudformation delete-stack` |

### Nuevos Componentes
- AWS CloudFormation (IaC)
- Application Load Balancer (ALB)
- Auto Scaling Group (ASG)
- Amazon S3 (reemplaza NFS)
- IAM Roles (LabRole en AWS Academy)
- Launch Template
- Target Groups
- Scaling Policies

### Componentes Eliminados
- File Server EC2 (reemplazado por S3)
- NFS configuration
- Configuración manual de 3 EC2s

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
        │  EC2 Web Server 1     │          │  EC2 Web Server 2-5   │
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
- Max Capacity: 3
- Desired Capacity: 1 (ajustado dinámicamente)
- Scaling Policy: Target Tracking (CPU > 10%)
- Cooldown: 300 segundos
```

### Componentes Principales
- **CloudFormation**: Template YAML (~1200 líneas, 25+ recursos)
- **Application Load Balancer**: Distribuye tráfico HTTP
- **Auto Scaling Group**: 1-3 Web Servers (t3.small)
- **Amazon S3**: Almacenamiento de videos (reemplaza NFS)
- **Amazon RDS**: PostgreSQL 16 (db.t3.micro)
- **IAM Roles**: LabRole de AWS Academy para acceso a S3
- **1 Worker EC2**: t3.small para procesamiento con Celery

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
2. Name: `anb-key-pair`
3. Key pair type: RSA
4. File format: `.pem`
5. Descargar y guardar el archivo
6. `chmod 400 anb-key-pair.pem`

### 1.2 Obtener tu IP Pública

```bash
# Obtener tu IP pública
curl -s ifconfig.me
```

Anota tu IP: `_______________`

### 1.3 Configurar Parameters File

```bash
cd docs/Entrega_3/deployment/cloudformation

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
    "ParameterValue": "anb-key-pair"
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

---

## Paso 2: Despliegue con CloudFormation

### 2.1 Opción A: Despliegue con Script Automatizado (Recomendado)

```bash
cd docs/Entrega_3/deployment/scripts

# Ejecutar el script de despliegue
./deploy-entrega3.sh
```

El script te guiará interactivamente:

```
========================================
  CloudFormation Stack Deployment
========================================

Stack name: anb-video-stack

Checking if parameters.json exists...
✓ Found parameters.json

Do you want to review parameters before deployment? (y/n) [n]: n

Starting stack deployment...
✓ Stack creation initiated successfully

Waiting for stack to be created (this takes ~15 minutes)...
...
```

⏳ **Esperar ~20 minutos** mientras CloudFormation crea todos los recursos.

### 2.2 Monitorear el Despliegue

**Opción 1: AWS Console**
1. Ir a **CloudFormation** en AWS Console
2. Seleccionar el stack `anb-video-stack`
3. Ver la pestaña **Events** para seguir el progreso

**Opción 2: AWS CLI**
```bash
# Ver eventos del stack
aws cloudformation describe-stack-events \
  --stack-name anb-video-stack \
  --region us-east-1 \
  --max-items 20

# Ver recursos creados
aws cloudformation describe-stack-resources \
  --stack-name anb-video-stack \
  --region us-east-1
```

---

## Paso 3: Verificación de la Infraestructura

### 3.1 Obtener Outputs del Stack

```bash
# Ver todos los outputs
aws cloudformation describe-stacks \
  --stack-name anb-video-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'

# Guardar outputs en variables
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
  --output text)

RDS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
  --output text)

S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name anb-video-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text)

echo "ALB DNS: $ALB_DNS"
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "S3 Bucket: $S3_BUCKET"
```

Anota estos valores:
- **ALB DNS**: `_______________`
- **RDS Endpoint**: `_______________`
- **S3 Bucket**: `_______________`

### 3.2 Verificar Recursos Creados

**Opción 1: Verificar desde AWS Console (Recomendado)**

La forma más sencilla de verificar que todos los recursos se crearon correctamente es desde la consola de AWS:

1. **CloudFormation**:
   - Ir a **CloudFormation** en AWS Console
   - Seleccionar el stack `anb-video-stack`
   - Pestaña **Resources**: Ver todos los 25+ recursos creados
   - Pestaña **Outputs**: Ver ALB DNS, RDS Endpoint, S3 Bucket
   - Pestaña **Events**: Ver historial completo de creación

2. **EC2 → Load Balancers**:
   - Ver el ALB `anb-video-alb`
   - Estado debe ser "Active"
   - DNS name disponible

3. **EC2 → Auto Scaling Groups**:
   - Ver el ASG `anb-video-web-asg`
   - Desired capacity: 1
   - Instances: Al menos 1 running

4. **EC2 → Instances**:
   - Ver instancias con tag `Project: anb-video`
   - Al menos 2 instancias running (1 Web Server, 1 Worker)

5. **RDS → Databases**:
   - Ver `anb-video-db`
   - Status: Available

6. **S3 → Buckets**:
   - Ver bucket `anb-video-videos-*`
   - Con carpetas `uploads/` y `processed/`

**Opción 2: Verificar con AWS CLI**

#### Verificar VPC y Subnets
```bash
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=anb-video-vpc" \
  --query 'Vpcs[0].[VpcId,CidrBlock]' \
  --output table
```

#### Verificar Application Load Balancer
```bash
aws elbv2 describe-load-balancers \
  --names anb-video-alb \
  --query 'LoadBalancers[0].[LoadBalancerName,DNSName,State.Code]' \
  --output table
```

#### Verificar Auto Scaling Group
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names anb-video-web-asg \
  --query 'AutoScalingGroups[0].[AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,length(Instances)]' \
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
#   PRE uploads/
#   PRE processed/
```

### 3.3 Health Check del ALB

```bash
# Health check básico
curl http://$ALB_DNS/health

# Debería responder:
# {"status":"healthy","timestamp":"2025-11-09T..."}
```

### 3.4 Verificar Target Group

```bash
# Ver targets registrados en el Target Group
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names anb-video-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)
```

Deberías ver al menos 1 target con `State: healthy`.

---

## Paso 4: Pruebas Funcionales con Postman

### 4.1 Importar Colección de Postman

**Paso 1: Abrir Postman**

1. Abrir Postman en tu máquina local
2. Si no lo tienes instalado, descargarlo desde [postman.com](https://www.postman.com/downloads/)

**Paso 2: Importar la colección**

1. En Postman, clic en **Import**
2. Seleccionar **File**
3. Navegar a `docs/Entrega_3/collections/postman_collection.json`
4. Clic en **Import**

**Paso 3: Importar el environment**

1. Clic en **Import** nuevamente
2. Seleccionar `docs/Entrega_3/collections/postman_environment.json`
3. Clic en **Import**

### 4.2 Configurar Environment con ALB DNS

**Importante**: Debes actualizar la variable `base_url` con el DNS del ALB que obtuviste en el paso anterior.

1. En Postman, seleccionar el environment importado (esquina superior derecha)
2. Clic en el ícono del ojo 👁️ → **Edit**
3. Actualizar la variable `base_url`:
   - **Initial Value**: `http://<ALB_DNS_AQUI>`
   - **Current Value**: `http://<ALB_DNS_AQUI>`
   - Ejemplo: `http://anb-video-alb-1234567890.us-east-1.elb.amazonaws.com`
4. Clic en **Save**

### 4.3 Ejecutar las Pruebas en Postman

La colección incluye los siguientes requests:

#### 1. Health Check
- **Endpoint**: `GET {{base_url}}/health`
- Sin autenticación
- Verifica que el ALB y las instancias están funcionando

Respuesta esperada:
```json
{"status":"healthy","timestamp":"2025-11-09T12:34:56.789Z"}
```

### 4.3 Registrar Usuario

```bash
curl -X POST $API_URL/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password1": "Test123!@#",
    "password2": "Test123!@#",
    "first_name": "Test",
    "last_name": "User",
    "city": "Bogota",
    "country": "Colombia"
  }'
```

Respuesta esperada:
```json
{
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci...",
  "user": {
    "id": "...",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User"
  }
}
```

### 4.4 Login y Obtener Token

```bash
curl -X POST $API_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#"
  }'
```

Guardar el token:
```bash
export TOKEN="<tu_access_token_aqui>"
```

### 4.5 Subir Video de Prueba

```bash
# Crear un video de prueba pequeño (o usar uno que tengas)
# Ejemplo: descargar video de muestra
wget https://file-examples.com/storage/fe1e01696d97c09069ac60b/2017/04/file_example_MP4_480_1_5MG.mp4 -O test-video.mp4

# Subir el video
curl -X POST $API_URL/api/videos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-video.mp4;type=video/mp4" \
  -F "title=Video Prueba CloudFormation" \
  -F "description=Prueba de Auto Scaling en AWS"
```

Respuesta esperada:
```json
{
  "id": "...",
  "title": "Video Prueba CloudFormation",
  "status": "pending",
  "created_at": "2025-11-09T..."
}
```

### 4.6 Verificar Procesamiento

```bash
# Listar videos
curl -X GET $API_URL/api/videos/ \
  -H "Authorization: Bearer $TOKEN"
```

Espera ~30-60 segundos y consulta de nuevo. El `status` debería cambiar a `"processed"`.

### 4.7 Verificar S3

```bash
# Ver archivos en S3
aws s3 ls s3://$S3_BUCKET/uploads/ --human-readable
aws s3 ls s3://$S3_BUCKET/processed/ --human-readable
```

---

## Paso 5: Pruebas de Auto Scaling

### 5.1 Ejecutar Prueba de Estrés

**Nota sobre el threshold de CPU**:
- Configuramos el Auto Scaling con un **threshold de 10%** de CPU (en lugar del típico 70%)
- Esto es **intencional para facilitar las pruebas** y demostrar el Auto Scaling en acción
- Con 10%, es más fácil y rápido activar el escalado sin necesitar herramientas de carga muy agresivas
- En producción, se recomienda usar 70% o más

**Ejecutar el script de estrés**:

```bash
cd docs/Entrega_3/deployment/scripts

# Ejecutar el script de prueba de estrés
./stress-test-autoscaling.sh
```

El script enviará múltiples oleadas de requests para elevar la CPU por encima del 10% y activar el Auto Scaling.

**También puedes ver el Auto Scaling desde AWS Console**:
1. Ir a **EC2** → **Auto Scaling Groups**
2. Seleccionar `anb-video-web-asg`
3. Pestaña **Activity**: Ver las actividades de escalado en tiempo real
4. Pestaña **Monitoring**: Ver métricas de CPU en CloudWatch
5. Ver cómo el Desired Capacity cambia de 1 a 2-3 instancias

### 5.2 Monitorear Auto Scaling en Tiempo Real

**Terminal 1 - Monitorear CloudWatch Metrics**:
```bash
watch -n 10 'aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=anb-video-web-asg \
  --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average \
  --query "Datapoints | sort_by(@, &Timestamp)[-5:] | [*].[Timestamp, Average]" \
  --output table'
```

**Terminal 2 - Monitorear ASG Activities**:
```bash
watch -n 3 'aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name anb-video-web-asg \
  --max-records 3 \
  --query "Activities[*].[StartTime, StatusCode, Description]" \
  --output table'
```

**Terminal 3 - Monitorear Instancias**:
```bash
watch -n 3 'aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names anb-video-web-asg \
  --query "AutoScalingGroups[0].[DesiredCapacity, length(Instances), Instances[*].[InstanceId, HealthStatus]]" \
  --output table'
```

### 5.3 Verificar Escalado

Después de 1-2 minutos de carga alta, deberías ver:

```bash
# Ver capacidad deseada
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names anb-video-web-asg \
  --query 'AutoScalingGroups[0].{Desired: DesiredCapacity, Min: MinSize, Max: MaxSize, Current: length(Instances)}' \
  --output table
```

Ejemplo de respuesta:
```
-------------------------------------
| DescribeAutoScalingGroups        |
+----------+-------+-----+----------+
| Current  | Desired | Max | Min    |
+----------+-------+-----+----------+
| 2        | 2      | 3   | 1      |
+----------+-------+-----+----------+
```

### 5.4 Verificar Health Checks

```bash
# Ver salud de los targets en el ALB
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names anb-video-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text) \
  --query 'TargetHealthDescriptions[*].[Target.Id, TargetHealth.State, TargetHealth.Description]' \
  --output table
```

---

## Gestión del Stack

### Actualizar el Stack

Si necesitas modificar el template o parámetros:

```bash
cd docs/Entrega_3/deployment/cloudformation

# Editar parameters.json o infrastructure.yaml
nano parameters.json

# Actualizar el stack
aws cloudformation update-stack \
  --stack-name anb-video-stack \
  --template-body file://infrastructure.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Esperar a que termine la actualización
aws cloudformation wait stack-update-complete \
  --stack-name anb-video-stack \
  --region us-east-1
```

### Eliminar el Stack

```bash
# ADVERTENCIA: Esto eliminará TODOS los recursos
# Asegúrate de hacer backup de datos importantes

aws cloudformation delete-stack \
  --stack-name anb-video-stack \
  --region us-east-1

# Monitorear la eliminación
aws cloudformation wait stack-delete-complete \
  --stack-name anb-video-stack \
  --region us-east-1

echo "Stack deleted successfully!"
```

**Nota**: El bucket de S3 se eliminará automáticamente ya que el template tiene `DeletionPolicy: Delete`.

---

## Recursos Adicionales

### Documentos Relacionados
- [arquitectura_aws.md](arquitectura_aws.md) - Arquitectura detallada
- [infrastructure.yaml](deployment/cloudformation/infrastructure.yaml) - CloudFormation template
- [deploy-entrega3.sh](deployment/scripts/deploy-entrega3.sh) - Script de despliegue
- [stress-test-autoscaling.sh](deployment/scripts/stress-test-autoscaling.sh) - Pruebas de Auto Scaling

---

**Documento actualizado**: 2025-11-09
**Versión**: 3.0 (Entrega 3 - CloudFormation)
**Autor**: Grupo 12
