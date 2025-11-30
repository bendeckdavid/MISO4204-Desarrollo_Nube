# Despliegue de la aplicación FastAPI en AWS ECS Fargate con Auto-Scaling (1-3 contenedores)

---

## Prerrequisitos

Antes de comenzar, asegúrate de tener:

1. **Sesión de laboratorio de AWS Academy activa**

   - Inicia sesión en AWS Academy y empieza tu sesión de laboratorio
   - Descarga las credenciales del AWS CLI (haz clic en "AWS Details" → "AWS CLI: Show")
   - Configura las credenciales en `~/.aws/credentials` bajo el perfil `[default]`

2. **Docker instalado y en ejecución**

   ```bash
   docker --version  # Debe mostrar la versión de Docker
   docker info       # Debe conectarse al daemon de Docker
   ```

3. **AWS CLI configurado**

   ```bash
   aws sts get-caller-identity  # Debe devolver los detalles de tu cuenta de AWS
   ```

4. **Obtén tu ID de cuenta de AWS**

   ```bash
   export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   echo $AWS_ACCOUNT_ID  # Guarda esto para pasos posteriores
   ```

5. **Verifica que exista LabRole**
   ```bash
   aws iam get-role --role-name LabRole
   # Debe devolver los detalles del rol con ARN: arn:aws:iam::ACCOUNT_ID:role/LabRole
   ```

---

## Paso 1: Crear repositorios ECR y subir imágenes Docker

### 1.1 Crear repositorios ECR

```bash
# Crear repositorios para los servicios web y worker
aws ecr create-repository --repository-name anb-web --region us-east-1 --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name anb-worker --region us-east-1 --image-scanning-configuration scanOnPush=true
```

**Salida esperada:**

```json
{
  "repository": {
    "repositoryUri": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/anb-web",
    "repositoryName": "anb-web",
    ...
  }
}
```

Guarda los valores de `repositoryUri` para ambos repositorios.

### 1.2 Autenticar Docker contra ECR

```bash
# Obtener la contraseña de login y autenticar Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com
```

**Salida esperada:** `Login Succeeded`

### 1.3 Construir y etiquetar imágenes Docker

```bash
# Ir a la raíz del proyecto
cd /Users/oscar/code/4204/MISO4204-Desarrollo_Nube

# Construir imagen del servicio web
docker build -f Dockerfile.web -t anb-web:latest --platform linux/amd64 .

# Construir imagen del servicio worker
docker build -f Dockerfile.worker -t anb-worker:latest --platform linux/amd64 .

# Etiquetar imágenes para ECR
docker tag anb-web:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-web:latest
docker tag anb-worker:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-worker:latest
```

### 1.4 Subir imágenes a ECR

```bash
# Subir imágenes de los servicios web y worker
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-web:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-worker:latest
```

**Tiempo estimado:** 5-10 minutos (según velocidad de red)

**Verificar:**

```bash
# Listar imágenes en ECR
aws ecr describe-images --repository-name anb-web --region us-east-1
aws ecr describe-images --repository-name anb-worker --region us-east-1
```

---

## Paso 2: Crear archivo de parámetros

Crea `docs/Entrega_5/deployment/cloudformation/parameters.json`:

```json
[
  { "ParameterKey": "ProjectName", "ParameterValue": "anb-video" },
  {
    "ParameterKey": "DBPassword",
    "ParameterValue": "YOUR_SECURE_PASSWORD_HERE"
  },
  {
    "ParameterKey": "SecretKey",
    "ParameterValue": "YOUR_64_CHAR_HEX_SECRET_HERE"
  },
  {
    "ParameterKey": "GitHubRepo",
    "ParameterValue": "https://github.com/bendeckdavid/MISO4204-Desarrollo_Nube.git"
  },
  { "ParameterKey": "GitHubBranch", "ParameterValue": "main" }
]
```

**Generar SecretKey:**

```bash
openssl rand -hex 32
```

---

## Paso 3: Desplegar el stack de CloudFormation en AWS Academy

### 3.1 Validar la plantilla

```bash
aws cloudformation validate-template \
  --template-body file://docs/Entrega_5/deployment/cloudformation/infrastructure-fargate.yaml \
  --region us-east-1
```

**Esperado:** Sin errores, devuelve la descripción de la plantilla.

### 3.2 Crear el stack

```bash
aws cloudformation create-stack \
  --stack-name anb-video-stack-fargate \
  --template-body file://docs/Entrega_5/deployment/cloudformation/infrastructure-fargate.yaml \
  --parameters file://docs/Entrega_5/deployment/cloudformation/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

**Salida esperada:**

```json
{
  "StackId": "arn:aws:cloudformation:us-east-1:ACCOUNT_ID:stack/anb-video-stack-fargate/..."
}
```

### 3.3 Monitorizar la creación del stack

```bash
# Ver eventos del stack en tiempo real
aws cloudformation describe-stack-events --stack-name anb-video-stack-fargate --region us-east-1 --query 'StackEvents[0:20].[Timestamp,ResourceStatus,ResourceType,ResourceStatusReason]' --output table

# Comprobar estado general del stack
aws cloudformation describe-stacks --stack-name anb-video-stack-fargate --region us-east-1 --query 'Stacks[0].StackStatus' --output text
```

**Cronograma esperado:**

- VPC/Subnets: 1-2 minutos
- Base de datos RDS: 5-7 minutos
- ALB: 2-3 minutos
- Cluster ECS: 30 segundos
- Servicios ECS: 2-3 minutos
- **Total: 10-15 minutos**

**Estado final esperado:** `CREATE_COMPLETE`

### 3.4 Obtener el endpoint del ALB

```bash
aws cloudformation describe-stacks --stack-name anb-video-stack-fargate --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`ALBURL`].OutputValue' --output text
```

**Guarda esta URL** (por ejemplo, `anb-video-alb-123456789.us-east-1.elb.amazonaws.com`)

---

## Paso 4: Verificar el despliegue

### 4.1 Comprobar servicios ECS

```bash
# Estado del servicio web
aws ecs describe-services --cluster anb-video-cluster --services anb-video-web-service --region us-east-1 --query 'services[0].[serviceName,status,runningCount,desiredCount]'

# Estado del servicio worker
aws ecs describe-services --cluster anb-video-cluster --services anb-video-worker-service --region us-east-1 --query 'services[0].[serviceName,status,runningCount,desiredCount]'
```

**Esperado:** `[ "anb-video-web-service", "ACTIVE", 1, 1]` y `[ "anb-video-worker-service", "ACTIVE", 1, 1]`

### 4.2 Comprobar salud de las tareas

```bash
# Listar tareas en ejecución
aws ecs list-tasks --cluster anb-video-cluster --region us-east-1

# Describir una tarea específica
aws ecs describe-tasks --cluster anb-video-cluster --tasks TASK_ARN_HERE --region us-east-1
```

### 4.3 Probar endpoint de salud

```bash
# Obtener URL del ALB desde los outputs de CloudFormation y probar el endpoint de salud
ALB_URL=$(aws cloudformation describe-stacks --stack-name anb-video-stack-fargate --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`ALBURL`].OutputValue' --output text)
curl ${ALB_URL}/health
```

**Esperado:**

```json
{ "status": "healthy", "version": "1.0.0" }
```

### 4.4 Probar registro y login de usuario

```bash
# Registrar usuario de prueba
curl -X POST ${ALB_URL}/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "password1": "Test1234!",
    "password2": "Test1234!",
    "city": "Bogotá",
    "country": "CO"
  }'
```

**Esperado:**

```json
{
  "id": "e704b859-86d0-4472-89df-9a4a9c77f4d5",
  "first_name": "Test",
  "last_name": "User",
  "email": "test@example.com",
  "city": "Bogotá",
  "country": "CO"
}
```

```bash
# Login
curl -X POST ${ALB_URL}/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!"
    }'
```

**Esperado:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlNzA0Yjg1OS04NmQwLTQ0NzItODlkZi05YTRhOWM3N2Y0ZDUiLCJleHAiOjE3NjQxMDI0ODN9.nDbIWM43t-g14RJhKIzKxZBv7x8APL_CcdMOmz--w78",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

### 4.5 Ver logs en CloudWatch

```bash
# Logs del servicio web
aws logs tail /ecs/anb-video-web --follow --region us-east-1

# Logs del servicio worker
aws logs tail /ecs/anb-video-worker --follow --region us-east-1
```

---
