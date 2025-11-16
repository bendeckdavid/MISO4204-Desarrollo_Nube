#!/bin/bash

###############################################################################
# ANB Rising Stars - Entrega 4 Deployment Script
# This script deploys the complete infrastructure with SQS and Worker ASG
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="anb-video-stack-entrega4"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUDFORMATION_DIR="$SCRIPT_DIR/../cloudformation"
TEMPLATE_FILE="$CLOUDFORMATION_DIR/infrastructure.yaml"
PARAMETERS_FILE="$CLOUDFORMATION_DIR/parameters.json"
PARAMETERS_EXAMPLE="$CLOUDFORMATION_DIR/parameters.example.json"
REGION="us-east-1"

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to get parameter value
get_parameter() {
    local param_name=$1
    local default_value=$2
    local prompt_message=$3
    local no_echo=$4

    if [ "$no_echo" = "true" ]; then
        read -s -p "$prompt_message [$default_value]: " value
        echo
    else
        read -p "$prompt_message [$default_value]: " value
    fi

    if [ -z "$value" ]; then
        echo "$default_value"
    else
        echo "$value"
    fi
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_message "$RED" "ERROR: AWS CLI is not installed"
    print_message "$YELLOW" "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if running in AWS Academy (check for vocareum session)
if aws sts get-caller-identity &> /dev/null; then
    print_message "$GREEN" "✓ AWS credentials configured"
else
    print_message "$RED" "ERROR: AWS credentials not configured"
    print_message "$YELLOW" "For AWS Academy, make sure you've started your lab and copied the credentials"
    exit 1
fi

print_message "$GREEN" "====================================="
print_message "$GREEN" "ANB Rising Stars - Entrega 4 Deploy"
print_message "$GREEN" "====================================="
print_message "$YELLOW" "Features: SQS Queue + Worker Auto Scaling + Multi-AZ"
echo

# Check if parameters file exists
if [ -f "$PARAMETERS_FILE" ]; then
    print_message "$GREEN" "Found existing $PARAMETERS_FILE"
    read -p "Use existing parameters file? (y/n) [y]: " use_existing
    if [ "$use_existing" != "n" ]; then
        USE_PARAMS_FILE=true
    else
        USE_PARAMS_FILE=false
    fi
else
    print_message "$YELLOW" "No parameters file found. You can:"
    echo "  1. Create $PARAMETERS_FILE manually (copy from $PARAMETERS_EXAMPLE)"
    echo "  2. Provide parameters interactively now"
    echo
    read -p "Do you have a $PARAMETERS_FILE ready? (y/n) [n]: " has_file
    if [ "$has_file" = "y" ]; then
        print_message "$RED" "ERROR: $PARAMETERS_FILE not found"
        exit 1
    fi
    USE_PARAMS_FILE=false
fi

if [ "$USE_PARAMS_FILE" = "false" ]; then
    # Get deployment parameters interactively
    print_message "$YELLOW" "Please provide the following parameters:"
    echo

    # Key Pair Name
    KEY_PAIR=$(get_parameter "KeyPairName" "anb-key-pair" "EC2 Key Pair Name")

    # DB Password
    DB_PASSWORD=$(get_parameter "DBPassword" "" "RDS Database Password (min 8 chars)" "true")
    if [ ${#DB_PASSWORD} -lt 8 ]; then
        print_message "$RED" "ERROR: Password must be at least 8 characters"
        exit 1
    fi

    # My IP Address (automatically detect or ask)
    MY_IP=$(curl -s https://checkip.amazonaws.com)
    if [ -z "$MY_IP" ]; then
        print_message "$YELLOW" "Could not automatically detect your IP"
        MY_IP_CIDR=$(get_parameter "MyIPAddress" "" "Your IP address for SSH (format: x.x.x.x/32)")
        if [ -z "$MY_IP_CIDR" ]; then
            print_message "$RED" "ERROR: MyIPAddress is required"
            exit 1
        fi
    else
        print_message "$GREEN" "Detected your IP: $MY_IP"
        MY_IP_CIDR="${MY_IP}/32"
        read -p "Use this IP for SSH access? (y/n) [y]: " use_detected
        if [ "$use_detected" = "n" ]; then
            MY_IP_CIDR=$(get_parameter "MyIPAddress" "$MY_IP_CIDR" "Your IP address for SSH (format: x.x.x.x/32)")
        fi
    fi

    # GitHub Branch - Default to entrega4-testing
    GITHUB_BRANCH=$(get_parameter "GitHubBranch" "entrega4-testing" "GitHub branch to deploy")

    echo
    print_message "$YELLOW" "Deployment Configuration:"
    echo "  Stack Name: $STACK_NAME"
    echo "  Region: $REGION"
    echo "  Key Pair: $KEY_PAIR"
    echo "  SSH Access: $MY_IP_CIDR"
    echo "  GitHub Branch: $GITHUB_BRANCH"
    echo
    print_message "$GREEN" "New Features (Entrega 4):"
    echo "  ✓ SQS Queue for video processing"
    echo "  ✓ Dead Letter Queue (DLQ) for failed messages"
    echo "  ✓ Worker Auto Scaling (1-3 instances)"
    echo "  ✓ Multi-AZ deployment (us-east-1a, us-east-1b)"
    echo "  ✓ Target Tracking based on SQS queue depth"
    echo

    read -p "Continue with deployment? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        print_message "$YELLOW" "Deployment cancelled"
        exit 0
    fi
else
    # Using parameters file - just show confirmation
    print_message "$GREEN" "Using parameters from $PARAMETERS_FILE"
    echo
    read -p "Continue with deployment? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        print_message "$YELLOW" "Deployment cancelled"
        exit 0
    fi
fi

# Check if stack exists
print_message "$YELLOW" "Checking if stack already exists..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
    print_message "$YELLOW" "Stack $STACK_NAME already exists"
    read -p "Do you want to update it? (y/n): " update_confirm
    if [ "$update_confirm" = "y" ]; then
        ACTION="update-stack"
    else
        print_message "$YELLOW" "Deployment cancelled"
        exit 0
    fi
else
    ACTION="create-stack"
fi

# Deploy CloudFormation stack
print_message "$GREEN" "Starting CloudFormation deployment..."
echo

if [ "$USE_PARAMS_FILE" = "true" ]; then
    # Deploy using parameters file
    aws cloudformation $ACTION \
        --stack-name "$STACK_NAME" \
        --template-body "file://$TEMPLATE_FILE" \
        --region "$REGION" \
        --parameters "file://$PARAMETERS_FILE" \
        --capabilities CAPABILITY_NAMED_IAM \
        --tags \
            Key=Project,Value="ANB Rising Stars" \
            Key=Entrega,Value="Entrega4" \
            Key=Course,Value="MISO4204"
else
    # Deploy using interactive parameters
    aws cloudformation $ACTION \
        --stack-name "$STACK_NAME" \
        --template-body "file://$TEMPLATE_FILE" \
        --region "$REGION" \
        --parameters \
            ParameterKey=KeyPairName,ParameterValue="$KEY_PAIR" \
            ParameterKey=DBPassword,ParameterValue="$DB_PASSWORD" \
            ParameterKey=MyIPAddress,ParameterValue="$MY_IP_CIDR" \
            ParameterKey=GitHubBranch,ParameterValue="$GITHUB_BRANCH" \
        --capabilities CAPABILITY_NAMED_IAM \
        --tags \
            Key=Project,Value="ANB Rising Stars" \
            Key=Entrega,Value="Entrega4" \
            Key=Course,Value="MISO4204"
fi

if [ $? -eq 0 ]; then
    print_message "$GREEN" "✓ CloudFormation stack deployment initiated"
    echo
    print_message "$YELLOW" "Waiting for stack to complete..."
    print_message "$YELLOW" "This will take approximately 15-20 minutes..."
    echo
    print_message "$YELLOW" "You can monitor progress in the AWS Console:"
    print_message "$YELLOW" "https://console.aws.amazon.com/cloudformation/home?region=$REGION#/stacks"
    echo

    # Wait for stack to complete
    aws cloudformation wait stack-${ACTION%-stack}-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"

    if [ $? -eq 0 ]; then
        print_message "$GREEN" "✓ Stack deployment completed successfully!"
        echo

        # Get outputs
        print_message "$GREEN" "===== Stack Outputs ====="
        aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
            --output table

        echo
        print_message "$GREEN" "===== SQS Queue Information ====="
        QUEUE_URL=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`VideoProcessingQueueURL`].OutputValue' \
            --output text 2>/dev/null || echo "Not found")

        DLQ_URL=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`VideoProcessingDLQURL`].OutputValue' \
            --output text 2>/dev/null || echo "Not found")

        echo "  Queue URL: $QUEUE_URL"
        echo "  DLQ URL: $DLQ_URL"

        echo
        print_message "$GREEN" "===== Next Steps ====="
        echo "1. Wait 5-10 minutes for instances to complete initialization"
        echo "2. Access your application at the ALB URL shown above"
        echo "3. Test the health endpoint: curl http://<ALB-DNS>/health"
        echo "4. Upload a video and check SQS queue for messages"
        echo "5. Monitor Worker Auto Scaling in AWS Console:"
        echo "   - CloudWatch: Queue depth metrics"
        echo "   - EC2 Auto Scaling: Worker instance count (1-3)"
        echo "6. Check DLQ for any failed messages"
        echo
        print_message "$YELLOW" "IMPORTANT: Remember to delete the stack when done:"
        print_message "$YELLOW" "  aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
    else
        print_message "$RED" "✗ Stack deployment failed"
        print_message "$YELLOW" "Check the AWS Console for error details"
        exit 1
    fi
else
    print_message "$RED" "✗ Failed to initiate stack deployment"
    exit 1
fi
