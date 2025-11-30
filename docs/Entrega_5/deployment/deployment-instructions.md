# FastAPI Application deployment to AWS ECS Fargate with Auto-Scaling (1-3 containers)

---

## Prerequisites

Before starting, ensure you have:

1. **AWS Academy Lab Session Active**

   - Log into AWS Academy and start your lab session
   - Download AWS CLI credentials (click "AWS Details" → "AWS CLI: Show")
   - Configure credentials in `~/.aws/credentials` under `[default]` profile

2. **Docker Installed and Running**

   ```bash
   docker --version  # Should show Docker version
   docker info       # Should connect to Docker daemon
   ```

3. **AWS CLI Configured**

   ```bash
   aws sts get-caller-identity  # Should return your AWS account details
   ```

4. **Get Your AWS Account ID**

   ```bash
   export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   echo $AWS_ACCOUNT_ID  # Save this for later steps
   ```

5. **Verify LabRole Exists**
   ```bash
   aws iam get-role --role-name LabRole
   # Should return role details with ARN: arn:aws:iam::ACCOUNT_ID:role/LabRole
   ```

---

## Step 1: Create ECR Repositories and Push Docker Images

### 1.1 Create ECR Repositories

```bash
# Create repository for web and worker service
aws ecr create-repository --repository-name anb-web --region us-east-1 --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name anb-worker --region us-east-1 --image-scanning-configuration scanOnPush=true
```

**Expected Output:**

```json
{
  "repository": {
    "repositoryUri": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/anb-web",
    "repositoryName": "anb-web",
    ...
  }
}
```

Save the `repositoryUri` values for both repositories.

### 1.2 Authenticate Docker to ECR

```bash
# Get login password and authenticate Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com
```

**Expected Output:** `Login Succeeded`

### 1.3 Build and Tag Docker Images

```bash
# Navigate to project root
cd /Users/oscar/code/4204/MISO4204-Desarrollo_Nube

# Build web service image
docker build -f Dockerfile.web -t anb-web:latest --platform linux/amd64 .

# Build worker service image
docker build -f Dockerfile.worker -t anb-worker:latest --platform linux/amd64 .

# Tag images for ECR
docker tag anb-web:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-web:latest
docker tag anb-worker:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-worker:latest
```

### 1.4 Push Images to ECR

```bash
# Push web and worker service images
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-web:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/anb-worker:latest
```

**Expected Time:** 5-10 minutes (depending on network speed)

**Verify:**

```bash
# List images in ECR
aws ecr describe-images --repository-name anb-web --region us-east-1
aws ecr describe-images --repository-name anb-worker --region us-east-1
```

---

## Step 2: Create Parameters File

Create `docs/Entrega_5/deployment/cloudformation/parameters.json`:

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

**Generate SecretKey:**

```bash
openssl rand -hex 32
```

---

## Step 3: Deploy CloudFormation Stack to AWS Academy

### 3.1 Validate Template

```bash
aws cloudformation validate-template \
  --template-body file://docs/Entrega_5/deployment/cloudformation/infrastructure-fargate.yaml \
  --region us-east-1
```

**Expected:** No errors, returns template description.

### 3.2 Create Stack

```bash
aws cloudformation create-stack \
  --stack-name anb-video-stack-fargate \
  --template-body file://docs/Entrega_5/deployment/cloudformation/infrastructure-fargate.yaml \
  --parameters file://docs/Entrega_5/deployment/cloudformation/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

**Expected Output:**

```json
{
  "StackId": "arn:aws:cloudformation:us-east-1:ACCOUNT_ID:stack/anb-video-stack-fargate/..."
}
```

### 3.3 Monitor Stack Creation

```bash
# Watch stack events in real-time
aws cloudformation describe-stack-events --stack-name anb-video-stack-fargate --region us-east-1 --query 'StackEvents[0:20].[Timestamp,ResourceStatus,ResourceType,ResourceStatusReason]' --output table

# Check overall stack status
aws cloudformation describe-stacks --stack-name anb-video-stack-fargate --region us-east-1 --query 'Stacks[0].StackStatus' --output text
```

**Expected Timeline:**

- VPC/Subnets: 1-2 minutes
- RDS Database: 5-7 minutes
- ALB: 2-3 minutes
- ECS Cluster: 30 seconds
- ECS Services: 2-3 minutes
- **Total: 10-15 minutes**

**Expected Final Status:** `CREATE_COMPLETE`

### 3.4 Get ALB Endpoint

```bash
aws cloudformation describe-stacks --stack-name anb-video-stack-fargate --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`ALBURL`].OutputValue' --output text
```

**Save this URL** (e.g., `anb-video-alb-123456789.us-east-1.elb.amazonaws.com`)

---

## Step 4: Verify Deployment

### 4.1 Check ECS Services

```bash
# Check web service status
aws ecs describe-services --cluster anb-video-cluster --services anb-video-web-service --region us-east-1 --query 'services[0].[serviceName,status,runningCount,desiredCount]'

# Check worker service status
aws ecs describe-services --cluster anb-video-cluster --services anb-video-worker-service --region us-east-1 --query 'services[0].[serviceName,status,runningCount,desiredCount]'
```

**Expected:** `[ "anb-video-web-service", "ACTIVE", 1, 1]` and `[ "anb-video-worker-service", "ACTIVE", 1, 1]`

### 4.2 Check Task Health

```bash
# List running tasks
aws ecs list-tasks --cluster anb-video-cluster --region us-east-1

# Describe specific task
aws ecs describe-tasks --cluster anb-video-cluster --tasks TASK_ARN_HERE --region us-east-1
```

### 4.3 Test Health Endpoint

```bash
# Get ALB URL from CloudFormation outputs and test health endpoint
ALB_URL=$(aws cloudformation describe-stacks --stack-name anb-video-stack-fargate --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`ALBURL`].OutputValue' --output text)
curl ${ALB_URL}/health
```

**Expected:**

```json
{ "status": "healthy", "version": "1.0.0" }
```

### 4.4 Test User Registration and Login

```bash
# Register test user
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

**Expected:**

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

**Expected:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlNzA0Yjg1OS04NmQwLTQ0NzItODlkZi05YTRhOWM3N2Y0ZDUiLCJleHAiOjE3NjQxMDI0ODN9.nDbIWM43t-g14RJhKIzKxZBv7x8APL_CcdMOmz--w78",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

### 4.5 Check CloudWatch Logs

```bash
# Web service logs
aws logs tail /ecs/anb-video-web --follow --region us-east-1

# Worker service logs
aws logs tail /ecs/anb-video-worker --follow --region us-east-1
```

---

## Step 5: Test Auto-Scaling Behavior

### 5.1 Create Test Users

```bash
# Use existing script to create test users
bash capacity-planning/scripts-entrega5/setup_crear_usuarios_prueba.sh
```

This creates `test1@anb.com` to `test5@anb.com` with password `Test1234!`

### 5.2 Test Web Service CPU Scaling

Use k6 load testing tool:

```bash
# Install k6 if not already installed (macOS)
brew install k6

# Update ALB URL in test script
export ALB_URL="http://anb-video-alb-1627965266.us-east-1.elb.amazonaws.com"

# Run load tests
k6 run capacity-planning/scripts-entrega5/test_escenario1_web.js \
  --vus 50 \
  --duration 5m

bash capacity-planning/scripts-entrega5/test_escenario2_worker.sh
```

### 5.3 Test Worker Service SQS Scaling

```bash
# Upload multiple videos to fill SQS queue
python3 capacity-planning/scripts-entrega5/upload_videos_python.py \
  --url ${ALB_URL} \
  --user test1@anb.com \
  --password Test1234! \
  --count 20
```

---

## Cost Estimate (AWS Academy - Free Tier)

AWS Academy provides credits, but be aware of resource usage:

| Resource             | Count            | Usage               | Estimated Cost    |
| -------------------- | ---------------- | ------------------- | ----------------- |
| ECS Fargate (Web)    | 1-3 tasks        | 0.5 vCPU, 1 GB      | $15-45/month      |
| ECS Fargate (Worker) | 1-3 tasks        | 1 vCPU, 3 GB        | $36-108/month     |
| RDS PostgreSQL       | 1 instance       | db.t3.micro         | $12/month         |
| ALB                  | 1                | Standard            | $16/month         |
| S3                   | 1 bucket         | Storage + requests  | $1-5/month        |
| SQS                  | 2 queues         | Requests            | $0.40/month       |
| ECR                  | 2 repos          | Storage             | $1/month          |
| CloudWatch Logs      | Multiple streams | Storage + ingestion | $5-10/month       |
| **Total**            |                  |                     | **$86-197/month** |

---
