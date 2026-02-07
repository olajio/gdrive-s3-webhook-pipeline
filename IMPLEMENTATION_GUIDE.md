# Implementation Guide: Enterprise Customer Care Call Processing System

Your quick-start, end-to-end checklist to deploy the AI-powered call transcription and summarization pipeline.

**📖 For comprehensive step-by-step instructions including detailed prerequisite setup, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

**🏗️ For complete system architecture, see [ARCHITECTURE.md](ARCHITECTURE.md)**

**📑 For detailed implementation stages, see [02_build_process_steps.md](02_build_process_steps.md)**

---

## Quick Start Overview

| Step | Description | Time |
|------|-------------|------|
| 1 | Clone repository | 1 min |
| 2 | Configure environment | 5 min |
| 3 | Google Cloud setup | 15 min |
| 4 | Deploy infrastructure | 10 min |
| 5 | Register webhook | 5 min |
| 6 | Validate deployment | 5 min |

---

## 0) Prerequisites

**⚠️ IMPORTANT:** If you're setting up for the first time, see [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

**Quick Checklist (assumes tools are already installed):**

**AWS Services Required:**
- Lambda, API Gateway (REST + WebSocket), S3, DynamoDB
- Step Functions, Amazon Transcribe, Amazon Bedrock (Claude 3.5 Sonnet)
- Cognito, Secrets Manager, CloudWatch, SNS, IAM

**Development Tools:**
- AWS CLI v2 configured with appropriate credentials
- Python 3.11+
- Terraform ≥ 1.0
- Google Cloud SDK (gcloud CLI) - **Required for Google Cloud operations**
- zip, jq, make

**Google Cloud:**
- Google Cloud project with Drive API enabled
- Service Account created with JSON key downloaded
- OAuth consent screen configured

**Note:** If `gcloud` command is not found, install Google Cloud SDK:
```bash
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Then initialize
gcloud init
```

**📚 Detailed Setup Guide:** See [SETUP_GUIDE.md Section 1: Prerequisites](SETUP_GUIDE.md#1-prerequisites) for:
- Development tools installation
- AWS CLI configuration
- Python virtual environment setup
- Project structure overview

---

## 1) Clone Repository

```bash
git clone https://github.com/olajio/customer-care-call-processor.git
cd customer-care-call-processor
```

---

## 2) Local Configuration

1. Create environment file:
   ```bash
   cat > .env << 'EOF'
   # Environment
   ENVIRONMENT=dev
   AWS_REGION=us-east-1
   
   # S3
   S3_BUCKET_NAME=customer-care-calls-dev-YOUR-UNIQUE-ID
   
   # Google Drive
   GDRIVE_FOLDER_ID=your-folder-id-here
   
   # Notifications
   ALERT_EMAIL=your-email@example.com
   EOF
   ```

2. Edit `.env` with your actual values.

3. Optional: Adjust environment-specific settings in `config/dev.yaml` and `config/prod.yaml`.

---

## 3) Google Cloud Setup

**⚠️ For first-time setup with detailed step-by-step instructions, see [SETUP_GUIDE.md Section 2](SETUP_GUIDE.md#2-google-cloud-setup)**

**Quick Steps:**

1. **Authenticate with Google Cloud** (required first):
   ```bash
   gcloud auth login  # Opens browser for authentication
   ```

2. **Create Google Cloud Project** (if needed):
   ```bash
   gcloud projects create customer-care-processor --name="Call Processor"
   gcloud config set project customer-care-processor
   ```

3. **Add Environment Tag** (required by Google Cloud):
   - **Option A (Recommended):** Use Google Cloud Console
     1. Go to IAM & Admin → Tags
     2. Create or select `environment` tag key
     3. Create tag value: `Development`
     4. Go to Manage Resources, select project
     5. Add the `environment=Development` tag
   
   - **Option B:** Use gcloud CLI (requires tag key to exist first)
     ```bash
     gcloud resource-manager tags bindings create \
       --tag-value=tagValues/TAGVALUE_ID \
       --parent=//cloudresourcemanager.googleapis.com/projects/customer-care-processor
     ```
     > See [Attaching tags to resources](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#attaching) for the full command reference.
     > See [Listing tags](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#listing_tags) for how to find your tag key and value IDs.

4. **Enable Google Drive API**:
   ```bash
   gcloud services enable drive.googleapis.com
   ```

5. **Create Service Account**:
   ```bash
   gcloud iam service-accounts create call-processor-sa \
       --display-name="Call Processor Service Account"
   
   gcloud iam service-accounts keys create credentials.json \
       --iam-account=call-processor-sa@YOUR_PROJECT.iam.gserviceaccount.com
   ```

6. **Share Google Drive folder** with the service account email as **Viewer**.

5. **Store credentials in AWS Secrets Manager**:
   ```bash
   ./scripts/setup_google_auth.sh credentials.json
   ```

---

## 4) Deploy Infrastructure

**Option A: One-Command Deploy**
```bash
./scripts/deploy.sh
```

**Option B: Manual Steps**
```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Plan deployment
terraform plan \
  -var="environment=dev" \
  -var="s3_bucket_name=$S3_BUCKET_NAME" \
  -var="gdrive_folder_id=$GDRIVE_FOLDER_ID" \
  -var="alert_email=$ALERT_EMAIL" \
  -out=tfplan

# 3. Apply
terraform apply tfplan

# 4. Package Lambda code
cd ..
./scripts/package_lambdas.sh

# 5. Deploy Lambda code
aws lambda update-function-code \
  --function-name $(terraform -chdir=terraform output -raw webhook_handler_function_name) \
  --zip-file fileb://dist/webhook.zip

# Repeat for other Lambda functions...
```

---

## 5) Register Google Drive Webhook

```bash
python scripts/register_webhook.py \
  --folder-id $GDRIVE_FOLDER_ID \
  --webhook-url $(terraform -chdir=terraform output -raw webhook_url)
```

This creates a push notification channel that watches the Google Drive folder for new files.

---

## 6) Validate Deployment

**Test Webhook Handler:**
```bash
aws lambda invoke \
  --function-name $(terraform -chdir=terraform output -raw webhook_handler_function_name) \
  --payload '{"headers":{"X-Goog-Resource-State":"sync"}}' \
  /tmp/webhook_test.json

cat /tmp/webhook_test.json
```

**Check CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/$(terraform -chdir=terraform output -raw webhook_handler_function_name) --follow
```

**Verify DynamoDB Tables:**
```bash
aws dynamodb list-tables
```

---

## 7) Functional Test (End-to-End)

1. **Upload a test audio file** (mp3, wav, m4a) to the watched Google Drive folder.

2. **Monitor Step Functions** execution in AWS Console:
   - Navigate to Step Functions → State Machines → call-processing
   - Watch the execution progress through states

3. **Verify S3 storage:**
   ```bash
   aws s3 ls s3://$S3_BUCKET_NAME/raw-audio/ --recursive
   aws s3 ls s3://$S3_BUCKET_NAME/transcripts/ --recursive
   aws s3 ls s3://$S3_BUCKET_NAME/summaries/ --recursive
   ```

4. **Check DynamoDB record:**
   ```bash
   aws dynamodb scan --table-name customer-care-call-summaries-dev
   ```

5. **Verify summary was generated** with status "COMPLETED".

---

## 8) CI/CD (GitHub Actions)

Configure repository secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `GDRIVE_FOLDER_ID`
- `ALERT_EMAIL`

Workflows:
- Tests on push/PR: `.github/workflows/test.yml`
- Deploy on push to `main`: `.github/workflows/deploy.yml`

---

## 9) Development Workflow

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
make test              # Unit tests
make test-integration  # Integration tests (needs AWS)

# Code quality
make lint              # flake8/black/mypy

# Build
make package           # Package Lambda code
```

---

## 10) Operations & Monitoring

**CloudWatch Dashboard:**
Navigate to CloudWatch → Dashboards → `customer-care-call-processor-dev`

**Key Metrics:**
| Category | Metrics |
|----------|---------|
| Processing | CallsProcessed, ProcessingTime, SuccessRate |
| AI Services | TranscribeMinutes, BedrockTokens, ThrottlingEvents |
| API | Latency, RequestCount, ErrorRate |
| WebSocket | ActiveConnections, MessagesSent |

**Alarms:**
- High failure rate (>5% failures)
- Processing timeout (>10 minutes)
- Bedrock throttling
- API 5xx errors

**Logs:**
```bash
# Lambda logs
aws logs tail /aws/lambda/<function-name> --follow

# Step Functions
# View in AWS Console → Step Functions → Executions
```

---

## 11) Security Checklist

- [ ] Google service account key stored in Secrets Manager
- [ ] S3 encryption enabled (AES-256/KMS)
- [ ] DynamoDB encryption enabled (KMS)
- [ ] TLS 1.2+ for all APIs
- [ ] Cognito JWT authentication configured
- [ ] IAM least-privilege roles applied
- [ ] CloudTrail enabled for audit logging
- [ ] PII redaction enabled in Transcribe (optional)

---

## 12) Production Hardening

| Component | Recommendation |
|-----------|----------------|
| Lambda | Memory: 1024MB+, Provisioned concurrency |
| Bedrock | Request quota increase, Fallback to Claude Haiku |
| Transcribe | Custom vocabulary for industry terms |
| Step Functions | Dead-letter queue for failures |
| Cognito | Enable MFA for admin accounts |
| S3 | Lifecycle policies for archival, Access logging |
| DynamoDB | Point-in-time recovery, Auto-scaling |

---

## 13) Troubleshooting Quick Reference

| Issue | Check |
|-------|-------|
| Transcription fails | Audio format, Transcribe quotas, Lambda logs |
| Summary quality poor | Bedrock prompt, Transcript format, Model access |
| WebSocket silent | DynamoDB connections, JWT validity, Lambda logs |
| API 401/403 | Cognito token, User group membership |
| Step Functions stuck | Execution details, IAM permissions |
| High costs | Transcribe minutes, Bedrock tokens, Retry loops |

**→ See [SETUP_GUIDE.md Section 10: Troubleshooting](SETUP_GUIDE.md#10-troubleshooting) for detailed solutions**

---

## 14) Cutover Plan

1. Deploy to dev, validate with test files
2. Load-test with sample batch (10-50 files)
3. Promote to staging; repeat validation
4. Update prod environment variables
5. Deploy to production
6. Register production webhook
7. Monitor dashboard/alarms for 24 hours

---

## 15) Handy Commands

```bash
# View logs
make logs-webhook ENVIRONMENT=dev

# Invoke functions manually
aws lambda invoke --function-name <function-name> --payload '{}' output.json

# Clean build artifacts
make clean

# Destroy infrastructure (CAUTION!)
make destroy ENVIRONMENT=dev
```

---

## 16) Documentation References

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Complete deployment walkthrough |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design |
| [case_study_file.md](case_study_file.md) | Project requirements and spec |
| [01_features_and_stories.md](01_features_and_stories.md) | User stories and features |
| [02_build_process_steps.md](02_build_process_steps.md) | Detailed build process |
| [03_stage_completion_checklist.md](03_stage_completion_checklist.md) | Validation checklists |
| [04_navigation_guide.md](04_navigation_guide.md) | Project navigation |

---

## 17) Code References

| Path | Description |
|------|-------------|
| `src/lambda/webhook/` | Webhook handler (Google Drive) |
| `src/lambda/processing/` | Pipeline functions (Transcribe, Bedrock) |
| `src/lambda/api/` | REST API endpoints |
| `src/lambda/websocket/` | WebSocket handlers |
| `terraform/` | Infrastructure as Code |
| `stepfunctions/` | State machine definition |
| `scripts/` | Deployment and utility scripts |
| `tests/` | Unit and integration tests |
