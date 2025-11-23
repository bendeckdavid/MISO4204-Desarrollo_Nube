#!/bin/bash

# Script to deploy and test ECS Fargate simulation with LocalStack
# This mimics the actual Fargate deployment process locally

set -e

echo "========================================="
echo "ECS Fargate Local Deployment (LocalStack)"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker images exist
echo -e "${YELLOW}[1/7] Checking Docker images...${NC}"
if ! docker images | grep -q "anb-web.*latest"; then
    echo -e "${RED}Error: anb-web:latest image not found${NC}"
    echo "Building anb-web image..."
    docker build -t anb-web:latest -f Dockerfile.web .
fi

if ! docker images | grep -q "anb-worker.*latest"; then
    echo -e "${YELLOW}Warning: anb-worker:latest image not found, building...${NC}"
    docker build -t anb-worker:latest -f Dockerfile.worker .
fi

echo -e "${GREEN}✓ Docker images ready${NC}"
echo ""

# Stop existing deployment
echo -e "${YELLOW}[2/7] Stopping existing deployment...${NC}"
docker-compose -f docker-compose.fargate.yml down -v 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned up${NC}"
echo ""

# Start services
echo -e "${YELLOW}[3/7] Starting Fargate services...${NC}"
docker-compose -f docker-compose.fargate.yml up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Wait for LocalStack
echo -e "${YELLOW}[4/7] Waiting for LocalStack to be ready...${NC}"
sleep 5
until curl -s http://localhost:4567/_localstack/health | grep -q "\"s3\": \"available\""; do
  echo "Waiting for LocalStack S3..."
  sleep 2
done
echo -e "${GREEN}✓ LocalStack ready${NC}"
echo ""

# Initialize LocalStack resources
echo -e "${YELLOW}[5/7] Initializing S3 and SQS resources...${NC}"

# Set LocalStack endpoint
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4567

# Create S3 bucket
aws --endpoint-url=$AWS_ENDPOINT_URL s3 mb s3://anb-videos-dev 2>/dev/null || echo "Bucket already exists"

# Create SQS Dead Letter Queue
DLQ_URL=$(aws --endpoint-url=$AWS_ENDPOINT_URL sqs create-queue \
  --queue-name video-processing-dlq \
  --output text --query 'QueueUrl' 2>/dev/null || \
  aws --endpoint-url=$AWS_ENDPOINT_URL sqs get-queue-url \
  --queue-name video-processing-dlq \
  --output text --query 'QueueUrl')

# Get DLQ ARN
DLQ_ARN=$(aws --endpoint-url=$AWS_ENDPOINT_URL sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --output text --query 'Attributes.QueueArn')

# Create main SQS queue with DLQ
REDRIVE_POLICY="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"3\"}"

aws --endpoint-url=$AWS_ENDPOINT_URL sqs create-queue \
  --queue-name video-processing-queue \
  --attributes "{\"RedrivePolicy\":\"$(echo $REDRIVE_POLICY | sed 's/"/\\"/g')\"}" \
  2>/dev/null || echo "Queue already exists"

QUEUE_URL=$(aws --endpoint-url=$AWS_ENDPOINT_URL sqs get-queue-url \
  --queue-name video-processing-queue \
  --output text --query 'QueueUrl')

echo -e "${GREEN}✓ S3 Bucket: anb-videos-dev${NC}"
echo -e "${GREEN}✓ SQS Queue: $QUEUE_URL${NC}"
echo -e "${GREEN}✓ SQS DLQ: $DLQ_URL${NC}"
echo ""

# Wait for services to be healthy
echo -e "${YELLOW}[6/7] Waiting for services to become healthy...${NC}"
sleep 10

# Check web service health
MAX_RETRIES=30
RETRY_COUNT=0
until curl -s http://localhost:8090/health | grep -q "healthy" || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
  echo "Waiting for web services... (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
  sleep 2
  RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo -e "${RED}✗ Web services failed to become healthy${NC}"
  echo "Checking logs..."
  docker-compose -f docker-compose.fargate.yml logs web
  exit 1
fi

echo -e "${GREEN}✓ Web services healthy${NC}"
echo ""

# Display status
echo -e "${YELLOW}[7/7] Deployment Status${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker-compose -f docker-compose.fargate.yml ps
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${GREEN}========================================="
echo "✓ Fargate Deployment Complete!"
echo "=========================================${NC}"
echo ""
echo "Available Endpoints:"
echo "  • ALB (Load Balanced): http://localhost:8090"
echo "  • Web Instance 1:      http://localhost:8001"
echo "  • Web Instance 2:      http://localhost:8002"
echo "  • LocalStack:          http://localhost:4567"
echo "  • Database:            localhost:5434"
echo ""
echo "Architecture:"
echo "  ┌─────────────┐      ┌──────────────┐"
echo "  │     ALB     │─────▶│ Web Service  │ (2 instances)"
echo "  │   (Nginx)   │      │  (Fargate)   │"
echo "  └─────────────┘      └──────────────┘"
echo "                              │"
echo "                              ▼"
echo "                       ┌──────────────┐"
echo "                       │  PostgreSQL  │"
echo "                       └──────────────┘"
echo "                              │"
echo "                              ▼"
echo "  ┌─────────────┐      ┌──────────────┐"
echo "  │  LocalStack │◀────▶│    Worker    │ (1 instance)"
echo "  │  (S3+SQS)   │      │  (Fargate)   │"
echo "  └─────────────┘      └──────────────┘"
echo ""
echo "Test Commands:"
echo "  # Health check"
echo "  curl http://localhost:8090/health"
echo ""
echo "  # View logs"
echo "  docker-compose -f docker-compose.fargate.yml logs -f web"
echo "  docker-compose -f docker-compose.fargate.yml logs -f worker"
echo ""
echo "  # Stop deployment"
echo "  docker-compose -f docker-compose.fargate.yml down"
echo ""
