#!/bin/bash

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
until curl -s http://localhost:4567/_localstack/health | grep -q "\"s3\": \"available\""; do
  echo "Waiting for LocalStack S3..."
  sleep 2
done

echo "LocalStack is ready!"

# Set LocalStack endpoint
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4567

# Create S3 bucket
echo "Creating S3 bucket: anb-videos-dev"
aws --endpoint-url=$AWS_ENDPOINT_URL s3 mb s3://anb-videos-dev 2>/dev/null || echo "Bucket already exists"

# Create SQS Dead Letter Queue first
echo "Creating SQS Dead Letter Queue: video-processing-dlq"
DLQ_URL=$(aws --endpoint-url=$AWS_ENDPOINT_URL sqs create-queue \
  --queue-name video-processing-dlq \
  --output text --query 'QueueUrl' 2>/dev/null || \
  aws --endpoint-url=$AWS_ENDPOINT_URL sqs get-queue-url \
  --queue-name video-processing-dlq \
  --output text --query 'QueueUrl')

echo "DLQ URL: $DLQ_URL"

# Get DLQ ARN
DLQ_ARN=$(aws --endpoint-url=$AWS_ENDPOINT_URL sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --output text --query 'Attributes.QueueArn')

echo "DLQ ARN: $DLQ_ARN"

# Create main SQS queue with DLQ configuration
echo "Creating SQS Queue: video-processing-queue"
REDRIVE_POLICY="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"3\"}"

aws --endpoint-url=$AWS_ENDPOINT_URL sqs create-queue \
  --queue-name video-processing-queue \
  --attributes "{\"RedrivePolicy\":\"$(echo $REDRIVE_POLICY | sed 's/"/\\"/g')\"}" \
  2>/dev/null || echo "Queue already exists"

QUEUE_URL=$(aws --endpoint-url=$AWS_ENDPOINT_URL sqs get-queue-url \
  --queue-name video-processing-queue \
  --output text --query 'QueueUrl')

echo "Queue URL: $QUEUE_URL"

echo ""
echo "LocalStack initialization complete!"
echo "S3 Bucket: anb-videos-dev"
echo "SQS Queue: $QUEUE_URL"
echo "SQS DLQ: $DLQ_URL"
