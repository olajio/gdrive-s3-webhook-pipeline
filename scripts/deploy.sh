#!/bin/bash
# ==================================================
# Customer Care Call Processing System - Deploy Script
# ==================================================
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║       Customer Care Call Processing System - Deployment          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for required environment variables
if [ -z "$S3_BUCKET_NAME" ]; then
    echo -e "${RED}Error: S3_BUCKET_NAME environment variable is required${NC}"
    echo "  Example: export S3_BUCKET_NAME=customer-care-call-processor-dev"
    exit 1
fi

if [ -z "$GDRIVE_FOLDER_ID" ]; then
    echo -e "${RED}Error: GDRIVE_FOLDER_ID environment variable is required${NC}"
    echo "  Example: export GDRIVE_FOLDER_ID=1ABC123def456"
    exit 1
fi

# Get environment (default to dev)
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "AWS Region:  ${YELLOW}$AWS_REGION${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI installed${NC}"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: Terraform is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Terraform installed${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 installed${NC}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: Invalid AWS credentials${NC}"
    exit 1
fi
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS credentials valid (Account: $AWS_ACCOUNT)${NC}"
echo ""

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Package Lambda functions
echo -e "${BLUE}Packaging Lambda functions...${NC}"
cd src/lambda

# Create deployment packages
for dir in webhook processing api websocket; do
    if [ -d "$dir" ]; then
        cd "$dir"
        zip -r "$PROJECT_ROOT/terraform/${dir}_package.zip" *.py -x "__pycache__/*" > /dev/null
        cd ..
        echo -e "  ${GREEN}✓ Packaged $dir${NC}"
    fi
done

# Package shared utilities
zip -r "$PROJECT_ROOT/terraform/utils_package.zip" utils.py -x "__pycache__/*" > /dev/null
echo -e "  ${GREEN}✓ Packaged utils${NC}"
cd "$PROJECT_ROOT"
echo ""

# Initialize Terraform
echo -e "${BLUE}Initializing Terraform...${NC}"
cd terraform
terraform init -upgrade > /dev/null
echo -e "${GREEN}✓ Terraform initialized${NC}"
echo ""

# Create terraform.tfvars if not exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}Creating terraform.tfvars...${NC}"
    cat > terraform.tfvars <<EOF
# Customer Care Call Processing System Configuration
aws_region       = "$AWS_REGION"
environment      = "$ENVIRONMENT"
s3_bucket_name   = "$S3_BUCKET_NAME"
gdrive_folder_id = "$GDRIVE_FOLDER_ID"
EOF
    echo -e "${GREEN}✓ terraform.tfvars created${NC}"
fi

# Plan Terraform changes
echo -e "${BLUE}Planning infrastructure changes...${NC}"
terraform plan \
    -var="environment=$ENVIRONMENT" \
    -var="s3_bucket_name=$S3_BUCKET_NAME" \
    -var="gdrive_folder_id=$GDRIVE_FOLDER_ID" \
    -out=tfplan \
    > /dev/null
echo -e "${GREEN}✓ Terraform plan created${NC}"
echo ""

# Show what will be created
echo -e "${BLUE}Resources to be created/modified:${NC}"
terraform show -no-color tfplan | grep -E "^\s*#" | head -20
echo ""

# Ask for confirmation
echo -e "${YELLOW}Review the plan above.${NC}"
read -p "Apply these changes? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi
echo ""

# Apply Terraform
echo -e "${BLUE}Applying infrastructure changes...${NC}"
terraform apply -auto-approve tfplan
echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# Get outputs
echo -e "${BLUE}Deployment Outputs:${NC}"
echo "═══════════════════════════════════════════════════════════════════"

API_ENDPOINT=$(terraform output -raw api_gateway_url 2>/dev/null || echo "N/A")
WEBHOOK_ENDPOINT=$(terraform output -raw webhook_endpoint 2>/dev/null || echo "N/A")
WEBSOCKET_ENDPOINT=$(terraform output -raw websocket_endpoint 2>/dev/null || echo "N/A")
STEP_FUNCTION_ARN=$(terraform output -raw step_function_arn 2>/dev/null || echo "N/A")
S3_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "N/A")
COGNITO_POOL_ID=$(terraform output -raw cognito_user_pool_id 2>/dev/null || echo "N/A")
COGNITO_CLIENT_ID=$(terraform output -raw cognito_client_id 2>/dev/null || echo "N/A")

echo ""
echo -e "REST API:          ${GREEN}$API_ENDPOINT${NC}"
echo -e "Webhook Endpoint:  ${GREEN}$WEBHOOK_ENDPOINT${NC}"
echo -e "WebSocket:         ${GREEN}$WEBSOCKET_ENDPOINT${NC}"
echo -e "Step Function:     ${GREEN}$STEP_FUNCTION_ARN${NC}"
echo -e "S3 Bucket:         ${GREEN}$S3_BUCKET${NC}"
echo -e "Cognito Pool ID:   ${GREEN}$COGNITO_POOL_ID${NC}"
echo -e "Cognito Client:    ${GREEN}$COGNITO_CLIENT_ID${NC}"
echo ""
echo "═══════════════════════════════════════════════════════════════════"

# Save outputs to file
echo ""
echo -e "${BLUE}Saving outputs...${NC}"
cd "$PROJECT_ROOT"
mkdir -p config
terraform -chdir=terraform output -json > config/terraform-outputs.json
echo -e "${GREEN}✓ Outputs saved to config/terraform-outputs.json${NC}"

# Next steps
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "1. Store Google credentials in Secrets Manager:"
echo "   aws secretsmanager create-secret \\"
echo "     --name google-drive-credentials \\"
echo "     --secret-string file://credentials/service-account-key.json"
echo ""
echo "2. Register Google Drive webhook:"
echo "   python scripts/register_webhook.py \\"
echo "     --folder-id $GDRIVE_FOLDER_ID \\"
echo "     --webhook-url $WEBHOOK_ENDPOINT"
echo ""
echo "3. Create Cognito admin user:"
echo "   aws cognito-idp admin-create-user \\"
echo "     --user-pool-id $COGNITO_POOL_ID \\"
echo "     --username admin@example.com \\"
echo "     --user-attributes Name=email,Value=admin@example.com"
echo ""
echo "4. Start frontend development:"
echo "   See SETUP_GUIDE.md Section 7 for React frontend setup"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${GREEN}Deployment complete!${NC}"
