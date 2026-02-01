# Implementation Guide: Enterprise Customer Care Call Processing System

Your quick-start, end-to-end checklist to deploy the AI-powered call transcription and summarization pipeline.

**📖 For comprehensive step-by-step instructions including detailed prerequisite setup, see [WEBHOOK_IMPLEMENTATION.md](WEBHOOK_IMPLEMENTATION.md)**

**🏗️ For complete system architecture, see [ARCHITECTURE.md](ARCHITECTURE.md)**

**📑 For detailed implementation stages, see [02_build_process_steps.md](02_build_process_steps.md)**

## 0) Prerequisites

**⚠️ IMPORTANT:** If you're setting up for the first time, see [WEBHOOK_IMPLEMENTATION.md Sections 2 & 3](WEBHOOK_IMPLEMENTATION.md#2-prerequisites-and-environment-setup) for detailed instructions.

**Quick Checklist (assumes tools are already installed):**

**AWS Services Required:**
- Lambda, API Gateway (REST + WebSocket), S3, DynamoDB
- Step Functions, Amazon Transcribe, Amazon Bedrock (Claude 3.5 Sonnet)
- Cognito, Secrets Manager, CloudWatch, SNS, IAM

**Development Tools:**
- AWS CLI v2, AWS CDK, Python 3.11+, Node.js 18+
- Terraform ≥ 1.0, zip, jq, make

**Google Cloud:**
- Google Cloud project with Drive API enabled
- Service Account created with JSON key downloaded

**GitHub Actions Secrets:**
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- `S3_BUCKET_NAME`, `GDRIVE_FOLDER_ID`, `ALERT_EMAIL`

**📚 Detailed Setup Guide:** See [WEBHOOK_IMPLEMENTATION.md Section 2: Prerequisites](WEBHOOK_IMPLEMENTATION.md#2-prerequisites-and-environment-setup) for:
- Development tools installation (Node.js, Python, AWS CLI, CDK, Google Cloud SDK)
- Version control setup
- Python virtual environment configuration
- Project structure creation

**🔐 Google Cloud Setup Guide:** See [WEBHOOK_IMPLEMENTATION.md Section 3: Google Cloud Platform Setup](WEBHOOK_IMPLEMENTATION.md#3-google-cloud-platform-setup) for:
- Creating Google Cloud Project
- Enabling Google Drive API
- Creating and configuring Service Account
- Securing service account keys
- Creating and sharing Google Drive folders
- Testing service account access

## 1) Clone
```bash
git clone https://github.com/olajio/customer-care-call-processor.git
cd customer-care-call-processor
```

## 2) Local configuration
1. Copy env template:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your values (S3 bucket, folder ID, alert email, region, environment).
3. Optional: adjust per-env YAML in `config/dev.yaml` and `config/prod.yaml`.

## 3) Google setup (service account + folder share)

**⚠️ For first-time setup with detailed step-by-step instructions, see [WEBHOOK_IMPLEMENTATION.md Section 3](WEBHOOK_IMPLEMENTATION.md#3-google-cloud-platform-setup)**

**Quick Steps (assumes you've read the detailed guide):**
1. In Google Cloud Console, create a Service Account (Viewer role is enough for reads).
   - **Detailed instructions:** [Section 3.3](WEBHOOK_IMPLEMENTATION.md#33-create-service-account)
2. Create & download the JSON key.
   - **Detailed instructions with security warnings:** [Section 3.4](WEBHOOK_IMPLEMENTATION.md#34-generate-and-secure-service-account-key)
3. Share the target Google Drive folder with the service account email as **Viewer**.
   - **Detailed instructions:** [Section 3.5](WEBHOOK_IMPLEMENTATION.md#35-create-and-share-google-drive-folder)
4. **💡 Recommended:** Test service account access before proceeding.
   - **Test script and validation:** [Section 3.6](WEBHOOK_IMPLEMENTATION.md#36-test-service-account-access)
5. Store creds + webhook token in AWS Secrets Manager via helper script:
   ```bash
   ./scripts/setup_google_auth.sh /path/to/service-account-key.json
   ```
   This writes secrets:
   - `gdrive-webhook-credentials` (service account JSON)
   - `gdrive-webhook-config` (webhook token)

## 4) AWS sanity checks
```bash
aws sts get-caller-identity
```
Ensure `S3_BUCKET_NAME` in `.env` is unique.

## 5) Deploy (one command)
```bash
./scripts/deploy.sh
```
What it does: packages Lambda code, runs Terraform (init/plan/apply), updates both Lambdas, invokes channel renewal once to create the initial webhook channel. Outputs the webhook URL, Lambda names, S3 bucket.

## 6) Manual deploy (if you prefer explicit steps)
```bash
cd terraform
terraform init
terraform plan \
  -var="environment=dev" \
  -var="s3_bucket_name=$S3_BUCKET_NAME" \
  -var="gdrive_folder_id=$GDRIVE_FOLDER_ID" \
  -var="alert_email=$ALERT_EMAIL" \
  -out=tfplan
terraform apply tfplan
```
Package & push Lambda code:
```bash
cd ../src/lambda
pip install -r ../../requirements.txt -t . --upgrade
zip -r ../../lambda_package.zip . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*"
cd ../..
aws lambda update-function-code --function-name $(terraform -chdir=terraform output -raw webhook_handler_function_name) --zip-file fileb://lambda_package.zip
aws lambda update-function-code --function-name $(terraform -chdir=terraform output -raw channel_renewal_function_name) --zip-file fileb://lambda_package.zip
```
Trigger initial channel creation (one time):
```bash
aws lambda invoke \
  --function-name $(terraform -chdir=terraform output -raw channel_renewal_function_name) \
  --payload '{}' /tmp/channel_response.json
cat /tmp/channel_response.json
```

## 7) CI/CD (GitHub Actions)
- Tests on push/PR: `.github/workflows/test.yml`
- Deploy on push to `main` or manual dispatch: `.github/workflows/deploy.yml`
Ensure repo secrets above are set.

## 8) Validate deployment
1. Ping webhook Lambda (sync verification):
   ```bash
   aws lambda invoke \
     --function-name $(terraform -chdir=terraform output -raw webhook_handler_function_name) \
     --payload '{"headers":{"X-Goog-Resource-State":"sync","X-Goog-Channel-Token":"test"}}' \
     /tmp/webhook_test.json
   cat /tmp/webhook_test.json
   ```
2. Tail logs:
   ```bash
   aws logs tail /aws/lambda/$(terraform -chdir=terraform output -raw webhook_handler_function_name) --follow
   aws logs tail /aws/lambda/$(terraform -chdir=terraform output -raw channel_renewal_function_name) --follow
   ```
3. Check resources:
   ```bash
   aws dynamodb describe-table --table-name $(terraform -chdir=terraform output -raw channels_table_name)
   aws dynamodb describe-table --table-name $(terraform -chdir=terraform output -raw sync_log_table_name)
   aws s3 ls s3://$(terraform -chdir=terraform output -raw s3_bucket_name)
   ```

## 9) Functional test (end-to-end)
1. Upload a test audio file (mp3, wav, m4a) to the watched Drive folder.
2. Monitor Step Functions execution in AWS Console.
3. Verify audio appears in S3 at `raw-audio/YYYY-MM-DD/{call-id}.ext`.
4. Check transcript in S3 at `transcripts/YYYY-MM-DD/{call-id}-transcript.json`.
5. Check summary in S3 at `summaries/YYYY-MM-DD/{call-id}-summary.json`.
6. Verify DynamoDB `call-summaries` table has the record with status "COMPLETED".
7. If frontend is deployed, verify summary appears in dashboard.

## 10) Dev workflow
```bash
pip install -r requirements.txt
make test              # unit tests
make test-integration  # integration (needs AWS resources)
make lint              # flake8/black/mypy
make package           # build Lambda zip
```

## 11) Operations & monitoring
- **Dashboards**: CloudWatch dashboards for Processing Pipeline, API Performance, Cost Tracking
- **Key Metrics**:
  - Processing: CallsProcessed, ProcessingTime (P50/P95/P99), SuccessRate, FailureRate
  - AI Services: TranscribeMinutes, BedrockTokens, ThrottlingEvents
  - API: Latency, RequestCount, ErrorRate (4xx/5xx)
  - WebSocket: ActiveConnections, MessagesSent
- **Alarms**: High failure rates, processing timeouts, Bedrock throttling, API 5xx errors
- **Logs**: 
  - Lambda: `/aws/lambda/<function-name>`
  - Step Functions: Execution history in console
  - API Gateway: Access logs and execution logs

## 12) Security checklist
- **Secrets Management**: Google service account in Secrets Manager; rotate every 90 days
- **Encryption**: S3 (AES-256/KMS), DynamoDB (KMS), TLS 1.2+ for all APIs
- **Authentication**: Cognito JWT tokens for API/WebSocket; custom token for webhooks
- **IAM**: Least-privilege roles for all Lambda functions (see CDK/Terraform)
- **Network**: API Gateway WAF protection; CORS properly configured
- **Audit**: CloudTrail enabled; DynamoDB Streams for change tracking
- **PII**: Transcribe PII redaction enabled (optional); data retention policies defined

## 13) Prod hardening
- **Lambda**: Increase memory (1024MB+ for processing), configure provisioned concurrency
- **Bedrock**: Request quota increases before go-live; implement fallback to Claude Haiku
- **Transcribe**: Pre-configure custom vocabulary for industry terms
- **Step Functions**: Configure dead-letter queue for failed executions
- **Cognito**: Enable MFA for admin/supervisor accounts
- **S3**: Lifecycle policies for Glacier archival (90 days); access logging enabled
- **DynamoDB**: Point-in-time recovery enabled; auto-scaling configured
- **Cost**: Set up billing alerts; reserved capacity for predictable workloads

## 14) Troubleshooting quick hits
- **Transcription fails**: Check audio format support; verify Transcribe quotas; review Lambda logs
- **Summary quality poor**: Review Bedrock prompt; check transcript formatting; verify model access
- **WebSocket silent**: Verify connection in DynamoDB; check JWT token validity; review connection Lambda logs
- **API 401/403**: Confirm Cognito token not expired; verify user in correct group
- **Step Functions stuck**: Check execution details in console; verify IAM permissions for each state
- **High costs**: Monitor Transcribe minutes and Bedrock tokens; check for retry loops
- **→ See [WEBHOOK_IMPLEMENTATION.md Section 11](WEBHOOK_IMPLEMENTATION.md#11-troubleshooting) for detailed troubleshooting**

## 15) Cutover plan
1. Deploy to dev, validate with test files.
2. Load-test with sample batch.
3. Promote to staging; repeat checks.
4. Set prod folder/bucket vars; deploy to prod.
5. Trigger initial channel creation in prod (invoke channel renewal once).
6. Monitor dashboard/alarms for 24h.

## 16) Handy commands
```bash
make logs-webhook ENVIRONMENT=dev
make invoke-renewal ENVIRONMENT=dev
make clean
make destroy ENVIRONMENT=dev   # caution
```

## 17) References
- **System Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Complete Specification**: [case_study_file.md](case_study_file.md)
- **User Stories & Features**: [01_features_and_stories.md](01_features_and_stories.md)
- **Detailed Build Steps**: [02_build_process_steps.md](02_build_process_steps.md)
- **Validation Checklists**: [03_stage_completion_checklist.md](03_stage_completion_checklist.md)
- **Navigation Guide**: [04_navigation_guide.md](04_navigation_guide.md)
- **Webhook Implementation**: [WEBHOOK_IMPLEMENTATION.md](WEBHOOK_IMPLEMENTATION.md)
- **IaC**: terraform/ (Terraform) or CDK code
- **Lambda Code**: src/lambda/
- **Frontend**: transcribe001-frontend/
```