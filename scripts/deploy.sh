#!/bin/bash
# Deploy script for Google Drive to S3 webhook pipeline
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Google Drive to S3 Webhook Pipeline Deployment${NC}"
echo "=================================================="

# Check for required environment variables
if [ -z "$S3_BUCKET_NAME" ]; then
    echo -e "${RED}Error: S3_BUCKET_NAME environment variable is required${NC}"
    exit 1
fi

if [ -z "$GDRIVE_FOLDER_ID" ]; then
    echo -e "${RED}Error: GDRIVE_FOLDER_ID environment variable is required${NC}"
    exit 1
fi

# Get environment (default to dev)
ENVIRONMENT="${ENVIRONMENT:-dev}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: Terraform is not installed${NC}"
    exit 1
fi

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: Invalid AWS credentials${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS credentials valid${NC}"

# Package Lambda functions
echo "Packaging Lambda functions..."
cd src/lambda
pip install -r ../../requirements.txt -t . --upgrade
zip -r ../../lambda_package.zip . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*"
cd ../..
echo -e "${GREEN}✓ Lambda package created${NC}"

# Initialize Terraform
echo "Initializing Terraform..."
cd terraform
terraform init
echo -e "${GREEN}✓ Terraform initialized${NC}"

# Plan Terraform changes
echo "Planning Terraform changes..."
terraform plan \
    -var="environment=$ENVIRONMENT" \
    -var="s3_bucket_name=$S3_BUCKET_NAME" \
    -var="gdrive_folder_id=$GDRIVE_FOLDER_ID" \
    -out=tfplan
echo -e "${GREEN}✓ Terraform plan created${NC}"

# Ask for confirmation
echo ""
read -p "Apply these changes? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Apply Terraform
echo "Applying Terraform changes..."
terraform apply tfplan
echo -e "${GREEN}✓ Infrastructure deployed${NC}"

# Get outputs
WEBHOOK_HANDLER=$(terraform output -raw webhook_handler_function_name)
CHANNEL_RENEWAL=$(terraform output -raw channel_renewal_function_name)
API_ENDPOINT=$(terraform output -raw api_gateway_url)

echo ""
echo -e "${GREEN}Deployment Information:${NC}"
echo "======================="
echo "Webhook Handler: $WEBHOOK_HANDLER"
echo "Channel Renewal: $CHANNEL_RENEWAL"
echo "API Endpoint: $API_ENDPOINT"

# Update Lambda code
echo ""
echo "Updating Lambda function code..."
cd ..
aws lambda update-function-code \
    --function-name "$WEBHOOK_HANDLER" \
    --zip-file fileb://lambda_package.zip \
    --no-cli-pager

aws lambda update-function-code \
    --function-name "$CHANNEL_RENEWAL" \
    --zip-file fileb://lambda_package.zip \
    --no-cli-pager

echo -e "${GREEN}✓ Lambda code updated${NC}"

# Wait for Lambda updates
echo "Waiting for Lambda functions to be ready..."
aws lambda wait function-updated --function-name "$WEBHOOK_HANDLER"
aws lambda wait function-updated --function-name "$CHANNEL_RENEWAL"
echo -e "${GREEN}✓ Lambda functions ready${NC}"

# Trigger initial channel creation (for first deploy)
echo ""
echo "Triggering initial channel creation..."
aws lambda invoke \
    --function-name "$CHANNEL_RENEWAL" \
    --payload '{}' \
    /tmp/channel_response.json \
    --no-cli-pager || true

if [ -f /tmp/channel_response.json ]; then
    echo "Response:"
    cat /tmp/channel_response.json | jq . || cat /tmp/channel_response.json
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Store Google service account credentials:"
echo "   aws secretsmanager create-secret --name gdrive-webhook-credentials --secret-string file://service-account-key.json"
echo ""
echo "2. Generate and store webhook token:"
echo "   WEBHOOK_TOKEN=\$(openssl rand -hex 32)"
echo "   aws secretsmanager create-secret --name gdrive-webhook-config --secret-string \"{\\\"webhook_token\\\":\\\"\$WEBHOOK_TOKEN\\\"}\""
echo ""
echo "3. Webhook endpoint: $API_ENDPOINT/webhook"
echo ""
echo "4. Monitor at: https://console.aws.amazon.com/cloudwatch"
