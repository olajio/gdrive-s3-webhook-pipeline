# Setup Guide: Customer Care Call Processing System

> Complete step-by-step instructions for deploying the AI-powered call processing pipeline.

**Related Documentation:**
- [README.md](README.md) - Project overview and quick start
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture deep dive
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Development workflow and stages

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Google Cloud Setup](#2-google-cloud-setup)
3. [AWS Setup](#3-aws-setup)
4. [Infrastructure Deployment](#4-infrastructure-deployment)
5. [Secrets Configuration](#5-secrets-configuration)
6. [Webhook Registration](#6-webhook-registration)
7. [Frontend Setup](#7-frontend-setup)
8. [Testing the Pipeline](#8-testing-the-pipeline)
9. [Production Checklist](#9-production-checklist)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### 1.1 Required Accounts

- **Google Cloud Platform** account with billing enabled
- **AWS** account with administrator access
- **GitHub** account (for source control)

### 1.2 Development Tools

Install the following tools on your development machine:

```bash
# macOS (using Homebrew)
brew install node python@3.11 terraform awscli jq
brew install --cask google-cloud-sdk

# Verify installations
node --version      # v18+
python3 --version   # 3.11+
terraform --version # 1.0+
aws --version       # 2.x
gcloud --version    # Google Cloud SDK
```

**Alternative Installation Methods for Google Cloud SDK:**

<details>
<summary>Linux (Debian/Ubuntu)</summary>

```bash
# Add Cloud SDK distribution URI
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Import Google Cloud public key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg

# Update and install
sudo apt-get update && sudo apt-get install google-cloud-sdk
```
</details>

<details>
<summary>Linux (Quick Install Script)</summary>

```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL  # Restart your shell
```
</details>

<details>
<summary>Amazon Linux / RHEL / CentOS</summary>

```bash
sudo tee -a /etc/yum.repos.d/google-cloud-sdk.repo << EOM
[google-cloud-cli]
name=Google Cloud CLI
baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el8-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOM

sudo yum install google-cloud-cli
```
</details>

<details>
<summary>Windows</summary>

```powershell
# Download and run the installer from:
# https://cloud.google.com/sdk/docs/install

# Or using Chocolatey:
choco install gcloudsdk
```
</details>

**Initialize Google Cloud SDK:**

```bash
gcloud init
```

This will:
1. Authenticate your account (opens browser for sign-in)
2. Set up your default project
3. Configure default compute region/zone

**Alternative:** You can also authenticate separately with:
```bash
gcloud auth login  # Just authenticate without full initialization
```

### 1.3 Clone the Repository

```bash
git clone https://github.com/olajio/customer-care-call-processor.git
cd customer-care-call-processor
```

### 1.4 Install Python Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Google Cloud Setup

### 2.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" → "New Project"
3. Enter project name: `customer-care-call-processor`
4. Click "Create"
5. Note the Project ID (shown on the project details page)

### 2.2 Authenticate with Google Cloud

**Before using any gcloud commands, you must authenticate:**

```bash
# Authenticate with your Google account
gcloud auth login
```

This will:
1. Open a browser window for you to sign in with your Google account
2. Grant the gcloud CLI permission to access your Google Cloud resources
3. Save your credentials locally for future use

**Note:** If the browser doesn't open automatically (common on remote systems), copy the URL shown in the terminal and open it manually in a browser.

### 2.3 Add Environment Tag to Project

**Google Cloud requires projects to have an `environment` tag for proper resource management.**

**Using Google Cloud Console (Recommended)**

First, create the tag key and values:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **"IAM & Admin"** > **"Tags"** ([Open Tags page](https://console.cloud.google.com/iam-admin/tags))
3. If the `environment` tag key doesn't exist:
   - Click **"Create"**
   - In the **Tag key** box, enter: `environment`
   - Click **"Add value"** and enter: `Development`
   - Optionally add more values: `Test`, `Staging`, `Production`
   - Click **"Create tag key"**

Then, attach the tag to your project:

4. Navigate to **"Manage Resources"** ([Open Manage Resources](https://console.cloud.google.com/cloud-resource-manager))
5. Click on your project
6. Click **"Tags"**
7. In the Tags panel, click **"Select scope"** and choose the organization or project containing your tags, then click **"Open"**
8. Click **"Add tag"**
9. In the **Key** field, select `environment`
10. In the **Value** field, select `Development` (or your chosen environment)
11. Click **"Save"**, then **"Confirm"** in the dialog

> For full details on attaching tags, see the Google Cloud documentation:
> [Attaching tags to resources](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#attaching)

**Tag Options:**
- `Development` - Development/testing environments
- `Test` - QA and testing environments
- `Staging` - Pre-production staging
- `Production` - Production environments

**Verify the tag was applied:**

You can verify in the Console by navigating to **Manage Resources** — the tag should appear under the **Tags** column for your project.

Alternatively, use the gcloud CLI:

```bash
# List tag bindings on the project
gcloud resource-manager tags bindings list \
  --parent=//cloudresourcemanager.googleapis.com/projects/YOUR_PROJECT_ID
```

> For more on listing tags, see the Google Cloud documentation:
> [Listing tags](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#listing_tags)

<details>
<summary><b>Alternative: Using gcloud CLI</b> (requires tag key and value to exist first)</summary>

If the tag key and values have already been created (e.g., via the Console steps above), you can attach a tag to your project using the CLI:

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# List available tag keys to find the tag key ID
gcloud resource-manager tags keys list \
  --parent=projects/YOUR_PROJECT_ID

# List tag values for the 'environment' key (use the tagKeys/TAGKEY_ID from above)
gcloud resource-manager tags values list \
  --parent=tagKeys/TAGKEY_ID

# Bind the tag value to your project (use the tagValues/TAGVALUE_ID from above)
gcloud resource-manager tags bindings create \
  --tag-value=tagValues/TAGVALUE_ID \
  --parent=//cloudresourcemanager.googleapis.com/projects/YOUR_PROJECT_ID
```

> For the full CLI reference for attaching tags, see:
> [Attaching tags to resources](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#attaching)

</details>

**Common Issues:**
- **Tag key doesn't exist** - Create it first via Google Cloud Console (steps 1-3 above)
- **Permission denied** - Ensure your account has "Owner" or "Tag Admin" role
- **Unrecognized arguments error** - Tag key may not be set up; use Console first

### 2.4 Enable Required APIs

```bash
# Ensure your project is set
gcloud config set project YOUR_PROJECT_ID

# Verify the correct project is selected
gcloud config get-value project

# Enable required APIs
gcloud services enable drive.googleapis.com
gcloud services enable serviceusage.googleapis.com
```

**Common Issues:**
- **Error: "You do not currently have an active account selected"** → Run `gcloud auth login` first
- **Error: "Project not found"** → Verify the project ID is correct
- **Error: "Permission denied"** → Ensure your Google account has Owner or Editor role on the project

### 2.5 Create Service Account

```bash
# Create service account
gcloud iam service-accounts create call-processor-webhook \
  --display-name="Call Processor Webhook Service Account"

# Note the email (format: call-processor-webhook@PROJECT_ID.iam.gserviceaccount.com)
```

### 2.6 Generate Service Account Key

```bash
# Generate key file
gcloud iam service-accounts keys create ./credentials/service-account-key.json \
  --iam-account=call-processor-webhook@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

⚠️ **Security Warning**: Keep this file secure! Never commit it to version control.

### 2.7 Create and Share Google Drive Folder

1. Go to [Google Drive](https://drive.google.com)
2. Create a folder: `Customer Call Recordings`
3. Right-click → Share → Add the service account email
4. Grant "Editor" permission
5. Note the folder ID from the URL: `drive.google.com/drive/folders/FOLDER_ID_HERE`

### 2.8 Test Service Account Access

```bash
python scripts/test_drive_access.py --folder-id YOUR_FOLDER_ID
```

Expected output: `✓ Successfully accessed folder: Customer Call Recordings`

---

## 3. AWS Setup

### 3.1 Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### 3.2 Verify AWS Access

```bash
aws sts get-caller-identity
```

### 3.3 Enable Amazon Bedrock Model Access

1. Go to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to "Model access" in the left sidebar
3. Click "Manage model access"
4. Select "Anthropic" → "Claude 3.5 Sonnet v2"
5. Request access and wait for approval (usually instant)

---

## 4. Infrastructure Deployment

### 4.1 Configure Terraform Variables

Create `terraform/terraform.tfvars`:

```hcl
# Required variables
aws_region     = "us-east-1"
environment    = "dev"
s3_bucket_name = "customer-care-call-processor-dev"
gdrive_folder_id = "YOUR_GOOGLE_DRIVE_FOLDER_ID"

# Optional: Email for alerts
alert_email = "your-email@example.com"

# Optional: Custom domain prefix for Cognito
cognito_domain_prefix = "your-company-calls"
```

### 4.2 Initialize Terraform

```bash
cd terraform
terraform init
```

### 4.3 Review Deployment Plan

```bash
terraform plan -out=tfplan
```

Review the output carefully. You should see resources for:
- S3 bucket
- DynamoDB tables (3)
- Lambda functions (10)
- Step Functions state machine
- API Gateway (REST + WebSocket)
- Cognito User Pool
- IAM roles and policies

### 4.4 Deploy Infrastructure

```bash
terraform apply tfplan
```

This takes 5-10 minutes. Note the outputs displayed at the end.

### 4.5 Save Terraform Outputs

```bash
terraform output -json > ../config/terraform-outputs.json
```

---

## 5. Secrets Configuration

### 5.1 Store Google Service Account Credentials

```bash
aws secretsmanager create-secret \
  --name google-drive-credentials \
  --secret-string file://../credentials/service-account-key.json
```

### 5.2 Generate and Store Webhook Token

```bash
# Generate secure token
WEBHOOK_TOKEN=$(openssl rand -hex 32)

# Store in Secrets Manager
aws secretsmanager create-secret \
  --name customer-care-call-processor-webhook-config \
  --secret-string "{\"webhook_token\":\"$WEBHOOK_TOKEN\"}"

# Save token for later use
echo $WEBHOOK_TOKEN > ../credentials/webhook-token.txt
```

---

## 6. Webhook Registration

### 6.1 Get API Gateway URL

```bash
API_URL=$(terraform output -raw api_gateway_url)
echo "Webhook URL: ${API_URL}/webhook"
```

### 6.2 Register Google Drive Webhook

```bash
cd ..
python scripts/register_webhook.py \
  --folder-id YOUR_GOOGLE_DRIVE_FOLDER_ID \
  --webhook-url "${API_URL}/webhook" \
  --token-file credentials/webhook-token.txt
```

Expected output:
```
✓ Webhook channel created successfully
  Channel ID: channel-abc123
  Expiration: 2024-01-22T10:30:00Z
  Resource ID: res-xyz789
```

### 6.3 Verify Webhook Registration

Upload a test file to your Google Drive folder and check:

1. **CloudWatch Logs**:
   ```bash
   aws logs tail /aws/lambda/customer-care-call-processor-webhook-handler-dev --follow
   ```

2. **DynamoDB**:
   ```bash
   aws dynamodb scan --table-name customer-care-call-processor-summaries-dev
   ```

---

## 7. Frontend Setup

### 7.1 Create Frontend Application

```bash
cd ..
npx create-vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 7.2 Install Dependencies

```bash
npm install \
  @aws-amplify/auth \
  aws-amplify \
  @tanstack/react-query \
  react-router-dom \
  axios \
  date-fns \
  tailwindcss \
  @headlessui/react \
  @heroicons/react
```

### 7.3 Configure Environment Variables

Create `frontend/.env`:

```env
VITE_API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/dev
VITE_WEBSOCKET_URL=wss://your-ws-id.execute-api.us-east-1.amazonaws.com/dev
VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_COGNITO_REGION=us-east-1
```

Get these values from Terraform outputs:
```bash
cd ../terraform
terraform output cognito_user_pool_id
terraform output cognito_client_id
terraform output api_gateway_url
terraform output websocket_endpoint
```

### 7.4 Start Development Server

```bash
cd ../frontend
npm run dev
```

Open http://localhost:5173

---

## 8. Testing the Pipeline

### 8.1 Create Test Users

```bash
# Create a caseworker
aws cognito-idp admin-create-user \
  --user-pool-id YOUR_USER_POOL_ID \
  --username caseworker@example.com \
  --user-attributes Name=email,Value=caseworker@example.com Name=name,Value="Test Caseworker" \
  --temporary-password "TempPass123!"

# Add to caseworkers group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id YOUR_USER_POOL_ID \
  --username caseworker@example.com \
  --group-name caseworkers
```

### 8.2 Upload Test Audio File

1. Go to your Google Drive folder
2. Upload an audio file (MP3, WAV, etc.)
3. Name it: `test_call_recording.mp3`

### 8.3 Monitor Processing Pipeline

**Watch Step Functions:**
```bash
# Get latest execution
aws stepfunctions list-executions \
  --state-machine-arn $(terraform output -raw step_function_arn) \
  --max-results 1
```

**Check CloudWatch Logs:**
```bash
# Webhook handler
aws logs tail /aws/lambda/customer-care-call-processor-webhook-handler-dev --follow

# Transcribe Lambda
aws logs tail /aws/lambda/customer-care-call-processor-start-transcribe-dev --follow

# Summary generator
aws logs tail /aws/lambda/customer-care-call-processor-generate-summary-dev --follow
```

### 8.4 Verify Results

```bash
# Check DynamoDB for completed summary
aws dynamodb scan \
  --table-name customer-care-call-processor-summaries-dev \
  --filter-expression "#s = :status" \
  --expression-attribute-names '{"#s": "status"}' \
  --expression-attribute-values '{":status": {"S": "COMPLETED"}}'
```

---

## 9. Production Checklist

### 9.1 Pre-Production Steps

- [ ] Change `environment` to `prod` in terraform.tfvars
- [ ] Enable versioning on S3 bucket
- [ ] Enable point-in-time recovery on DynamoDB
- [ ] Configure production Cognito callback URLs
- [ ] Set up CloudWatch alarms
- [ ] Configure SNS alert subscriptions
- [ ] Review IAM policies (principle of least privilege)
- [ ] Enable AWS Config for compliance

### 9.2 Security Hardening

```hcl
# Add to terraform.tfvars for production
enable_api_gateway_logging = true
log_retention_days = 90  # Increase for compliance
dynamodb_billing_mode = "PROVISIONED"  # For cost predictability
```

### 9.3 Monitoring Setup

```bash
# Subscribe to alerts
aws sns subscribe \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --protocol email \
  --notification-endpoint your-team@example.com
```

---

## 10. Troubleshooting

### 10.1 Webhook Not Receiving Events

**Symptoms**: No logs in webhook handler Lambda

**Solutions**:
1. Verify Google Drive folder is shared with service account
2. Check webhook channel hasn't expired
3. Verify API Gateway URL is correct
4. Check CloudWatch Logs for API Gateway

```bash
aws logs filter-log-events \
  --log-group-name /aws/apigateway/customer-care-call-processor-dev \
  --start-time $(date -v-1H +%s000)
```

### 10.2 Transcription Failing

**Symptoms**: Step Functions stuck at transcription step

**Solutions**:
1. Check audio file format is supported
2. Verify S3 bucket permissions
3. Check Transcribe service limits

```bash
aws transcribe list-transcription-jobs \
  --status FAILED \
  --max-results 5
```

### 10.3 Bedrock Summarization Errors

**Symptoms**: Summary generation fails

**Solutions**:
1. Verify Bedrock model access is enabled
2. Check model ID is correct
3. Review token limits

```bash
# Check Bedrock access
aws bedrock list-foundation-models \
  --by-provider anthropic \
  --query 'modelSummaries[*].modelId'
```

### 10.4 WebSocket Not Connecting

**Symptoms**: Frontend not receiving real-time updates

**Solutions**:
1. Check WebSocket URL is correct
2. Verify Cognito token is valid
3. Check WebSocket Lambda logs

```bash
aws logs tail /aws/lambda/customer-care-call-processor-ws-connect-dev --follow
```

### 10.5 Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `AccessDenied` on S3 | IAM permissions | Check Lambda execution role |
| `ValidationException` on Bedrock | Token limit exceeded | Truncate long transcripts |
| `ExpiredTokenException` | Cognito token expired | Refresh token in frontend |
| `ResourceNotFoundException` | DynamoDB table missing | Verify Terraform deployment |

---

## Next Steps

After successful deployment:

1. **Customize the Frontend** - See [Frontend Development Guide](docs/frontend-guide.md)
2. **Add Custom Analysis** - Extend the Bedrock prompt for domain-specific insights
3. **Set Up CI/CD** - Configure GitHub Actions for automated deployments
4. **Scale for Production** - Review capacity planning in [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Support

For issues and questions:
- Open a GitHub issue
- Check existing issues for solutions
- Review CloudWatch Logs for debugging

---

*Last Updated: February 2025*
