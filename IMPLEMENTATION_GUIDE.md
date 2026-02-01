# Implementation Guide: Google Drive → AWS S3 Webhook Pipeline

Your one-stop, end-to-end checklist to deploy and operate the production-ready pipeline in this repo.

**📖 For comprehensive step-by-step instructions including detailed prerequisite setup, see [WEBHOOK_IMPLEMENTATION.md](WEBHOOK_IMPLEMENTATION.md)**

## 0) Prerequisites

**⚠️ IMPORTANT:** If you're setting up for the first time and need detailed instructions for installing development tools, configuring Google Cloud, and creating service accounts, please refer to [WEBHOOK_IMPLEMENTATION.md Sections 2 & 3](WEBHOOK_IMPLEMENTATION.md#2-prerequisites-and-environment-setup).

**Quick Checklist (assumes tools are already installed):**
- AWS account with rights to Lambda, API Gateway, S3, DynamoDB, SNS, Secrets Manager, CloudWatch, IAM.
- CLI tools: AWS CLI v2, Terraform ≥ 1.0, Python 3.11, zip, jq, make.
- GitHub Actions enabled; repo secrets set: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (if not `us-east-1`), `S3_BUCKET_NAME` (globally unique), `GDRIVE_FOLDER_ID`, `ALERT_EMAIL`.
- Google Cloud project with Drive API enabled; Service Account created with JSON key downloaded.

**📚 Detailed Setup Guide:** See [WEBHOOK_IMPLEMENTATION.md Section 2: Prerequisites](WEBHOOK_IMPLEMENTATION.md#2-prerequisites-and-environment-setup) for:
- Development tools installation (Node.js, Python, AWS CLI, Terraform, Google Cloud SDK)
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
git clone https://github.com/olajio/gdrive-s3-webhook-pipeline.git
cd gdrive-s3-webhook-pipeline
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
- Upload a file (allowed extension, under size limit) to the watched Drive folder.
- Verify it appears in S3 at `gdrive/<fileId>/<filename>`.
- Check DynamoDB sync log for the entry.

## 10) Dev workflow
```bash
pip install -r requirements.txt
make test              # unit tests
make test-integration  # integration (needs AWS resources)
make lint              # flake8/black/mypy
make package           # build Lambda zip
```

## 11) Operations & monitoring
- Dashboard: CloudWatch dashboard `${project_name}-${environment}` (created by Terraform).
- Metrics: WebhooksReceived, FilesUploaded, FilesSkipped, DuplicateFilesSkipped, GoogleDriveErrors, AWSErrors, ChannelsRenewed, BytesUploaded.
- Alarms: high Lambda errors, channel renewal failures, throttles.
- Logs: `/aws/lambda/<webhook-handler>` and `/aws/lambda/<channel-renewal>`; API Gateway log group `${project_name}-${environment}`.

## 12) Security checklist
- Secrets live only in Secrets Manager (`gdrive-webhook-credentials`, `gdrive-webhook-config`).
- S3 and DynamoDB encryption enabled; API Gateway HTTPS-only; signature validation on webhook token.
- IAM least-privilege (see `terraform/iam.tf`).
- Rotate webhook token periodically (update `gdrive-webhook-config`).

## 13) Prod hardening
- Increase Lambda memory/timeouts for prod (`config/prod.yaml` or Terraform vars).
- KMS CMKs for S3/DynamoDB if required.
- S3 access logging (enabled for prod), lifecycle archiving configured.
- Reserved concurrency for webhook handler (already higher in prod settings).
- Tighten `ALLOWED_EXTENSIONS` and `MAX_FILE_SIZE_MB`.

## 14) Troubleshooting quick hits
- Webhook silent: check channel expiry; invoke channel renewal manually; verify token matches secret.
- 401 responses: token mismatch; rotate via `setup_google_auth.sh`.
- Missing files: verify allowed extensions/size; check logs for “Skipping file”.
- Duplicates: ensure md5Checksum available; S3 ETag compared.
- Google 403/quota: watch logs; alerts fire via SNS.

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
- Architecture & deep dive: WEBHOOK_TECHNICAL_DOCUMENTATION.md
- Implementation details: WEBHOOK_IMPLEMENTATION.md
- Strategy comparison: STRATEGY_RANKING.md
- Customer-facing overview: WEBHOOK_ARCHITECTURE_PROPOSAL.md
- Ops scripts: scripts/
- IaC: terraform/
- Code: src/lambda/
```