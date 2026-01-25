#!/bin/bash
# Setup script for Google Drive service account authentication
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Google Drive Service Account Setup${NC}"
echo "===================================="
echo ""

# Check for service account key file
if [ -z "$1" ]; then
    echo -e "${RED}Error: Service account key file required${NC}"
    echo "Usage: $0 <path-to-service-account-key.json>"
    echo ""
    echo "To create a service account:"
    echo "1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts"
    echo "2. Create a new service account"
    echo "3. Grant it 'Viewer' role"
    echo "4. Create and download JSON key"
    exit 1
fi

SERVICE_ACCOUNT_KEY="$1"

if [ ! -f "$SERVICE_ACCOUNT_KEY" ]; then
    echo -e "${RED}Error: File not found: $SERVICE_ACCOUNT_KEY${NC}"
    exit 1
fi

# Validate JSON
if ! jq empty "$SERVICE_ACCOUNT_KEY" 2>/dev/null; then
    echo -e "${RED}Error: Invalid JSON in service account key file${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Service account key file is valid${NC}"

# Extract service account email
SERVICE_ACCOUNT_EMAIL=$(jq -r '.client_email' "$SERVICE_ACCOUNT_KEY")
echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL"

# Get folder ID
read -p "Enter Google Drive folder ID to watch: " FOLDER_ID

if [ -z "$FOLDER_ID" ]; then
    echo -e "${RED}Error: Folder ID is required${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}IMPORTANT: Share the Google Drive folder with this service account:${NC}"
echo "Email: $SERVICE_ACCOUNT_EMAIL"
echo "Permissions: Viewer (read-only)"
echo ""
read -p "Have you shared the folder? (yes/no): " shared

if [ "$shared" != "yes" ]; then
    echo "Please share the folder and run this script again"
    exit 0
fi

# Store in AWS Secrets Manager
echo ""
echo "Storing credentials in AWS Secrets Manager..."

SECRET_NAME="gdrive-webhook-credentials"

if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" &> /dev/null; then
    echo -e "${YELLOW}Secret already exists. Updating...${NC}"
    aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string "file://$SERVICE_ACCOUNT_KEY"
else
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Google Drive service account credentials for webhook pipeline" \
        --secret-string "file://$SERVICE_ACCOUNT_KEY"
fi

echo -e "${GREEN}✓ Credentials stored in Secrets Manager${NC}"

# Generate webhook token
echo ""
echo "Generating webhook token..."
WEBHOOK_TOKEN=$(openssl rand -hex 32)

WEBHOOK_SECRET_NAME="gdrive-webhook-config"
WEBHOOK_SECRET_VALUE="{\"webhook_token\":\"$WEBHOOK_TOKEN\"}"

if aws secretsmanager describe-secret --secret-id "$WEBHOOK_SECRET_NAME" &> /dev/null; then
    echo -e "${YELLOW}Webhook config already exists. Updating...${NC}"
    aws secretsmanager put-secret-value \
        --secret-id "$WEBHOOK_SECRET_NAME" \
        --secret-string "$WEBHOOK_SECRET_VALUE"
else
    aws secretsmanager create-secret \
        --name "$WEBHOOK_SECRET_NAME" \
        --description "Webhook token for Google Drive notifications" \
        --secret-string "$WEBHOOK_SECRET_VALUE"
fi

echo -e "${GREEN}✓ Webhook token generated and stored${NC}"

# Save folder ID to .env if it exists
if [ -f .env ]; then
    if grep -q "GDRIVE_FOLDER_ID" .env; then
        sed -i.bak "s/GDRIVE_FOLDER_ID=.*/GDRIVE_FOLDER_ID=$FOLDER_ID/" .env
    else
        echo "GDRIVE_FOLDER_ID=$FOLDER_ID" >> .env
    fi
    echo -e "${GREEN}✓ Updated .env file${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Configuration:"
echo "- Service account: $SERVICE_ACCOUNT_EMAIL"
echo "- Folder ID: $FOLDER_ID"
echo "- Credentials stored in: $SECRET_NAME"
echo "- Webhook config stored in: $WEBHOOK_SECRET_NAME"
echo ""
echo "Next: Run ./scripts/deploy.sh to deploy the infrastructure"
