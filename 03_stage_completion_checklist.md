# Stage Completion Checklist
## Enterprise AWS Customer Care Call Processing System

---

## Overview
This document provides detailed validation steps to confirm successful completion of each build stage. Use this checklist to verify that each component is working correctly before moving to the next stage.

---

## Stage 0: Pre-requisites and Environment Setup

### ✅ Completion Criteria

#### Development Tools Installed
- [ ] Node.js v18+ installed
  ```bash
  node --version  # Should output v18.x.x or higher
  ```

- [ ] Python 3.11+ installed
  ```bash
  python --version  # Should output Python 3.11.x or higher
  ```

- [ ] AWS CLI v2 installed
  ```bash
  aws --version  # Should output aws-cli/2.x.x
  ```

- [ ] AWS CDK installed
  ```bash
  cdk --version  # Should output version number
  ```

- [ ] Google Cloud SDK installed
  ```bash
  gcloud --version  # Should output SDK version
  ```

#### Version Control Setup
- [ ] GitHub repositories created (infrastructure, lambdas, frontend, docs)
- [ ] Can clone repositories locally
- [ ] Can commit and push to feature branches
- [ ] Branch protection rules active on main branch
- [ ] SSH keys or access tokens configured

#### Local Environment
- [ ] Project directory structure created
- [ ] Python virtual environment created and activatable
- [ ] CDK project npm install completes without errors
- [ ] .env file created with necessary variables
- [ ] Can activate virtual environment: `source venv/bin/activate`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 1: Google Cloud Platform Setup

### ✅ Completion Criteria

#### Google Cloud Project
- [ ] Google Cloud Project created
- [ ] Project ID noted: `___________________________`
- [ ] Billing enabled on project
- [ ] Can access project in Google Cloud Console

#### Google Drive API
- [ ] Google Drive API enabled in project
- [ ] API shows as "Enabled" in APIs & Services dashboard
- [ ] No errors when accessing API configuration

#### Service Account
- [ ] Service account created with name `customer-care-drive-reader`
- [ ] Service account email noted: `___________________________@___________.iam.gserviceaccount.com`
- [ ] Service account JSON key downloaded
- [ ] JSON key file contains all required fields:
  - [ ] `type`
  - [ ] `project_id`
  - [ ] `private_key_id`
  - [ ] `private_key`
  - [ ] `client_email`
  - [ ] `client_id`

#### Google Drive Folder
- [ ] "Customer Care Recordings" folder created in Google Drive
- [ ] "Incoming" subfolder created
- [ ] Folder ID noted: `___________________________`
- [ ] Service account shared with "Viewer" permission
- [ ] Service account email appears in folder's "Share" settings

#### Access Testing
- [ ] Test script (`scripts/test_drive_access.py`) executed
- [ ] Required Python packages installed: `google-auth`, `google-api-python-client`
- [ ] Test script executes without errors
- [ ] Test script successfully lists files in folder (or shows 0 files)
- [ ] Test file uploaded to folder is visible via API

### 🔒 Security Checklist
- [ ] Service account key stored at `~/.config/customer-care-call-processor/service-account-key.json`
- [ ] Service account key permissions set to read-only: `chmod 400 ~/.config/customer-care-call-processor/service-account-key.json`
- [ ] Service account has minimal permissions (Viewer only)
- [ ] Folder shared only with service account (not public)

### 📦 Deliverables Collected
- [ ] Google Cloud Project ID: `___________________________`
- [ ] Service account email: `___________________________`
- [ ] Service account JSON key file path: `___________________________`
- [ ] Google Drive folder ID: `___________________________`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 2: AWS Account and Foundation Setup

### ✅ Completion Criteria

#### AWS Account Configuration
- [ ] AWS account accessible
- [ ] Root user MFA enabled
- [ ] IAM deployer group and user created via Terraform
- [ ] Deployer policy attached with required permissions
- [ ] Deployer access key generated and stored securely

#### AWS CLI Configuration
- [ ] AWS CLI configured with profile `customer-care-dev`
- [ ] Profile works:
  ```bash
  aws sts get-caller-identity --profile customer-care-dev
  # Should return Account ID, User ARN, UserId
  ```
- [ ] AWS_PROFILE environment variable set (optional but recommended)

#### AWS Organization (Optional)
- [ ] AWS Organization created (if using multi-account)
- [ ] Organizational Units (OUs) created: Development, Staging, Production
- [ ] Separate accounts created for each environment (if applicable)
- [ ] Can assume roles between accounts

#### CDK Project Initialization
- [ ] CDK project initialized in `customer-care-infrastructure` directory
- [ ] TypeScript compilation works: `npm run build`
- [ ] Can list stacks: `cdk ls`
- [ ] Can synthesize templates: `cdk synth` (no errors)
- [ ] Stack structure created:
  - [ ] `lib/stacks/storage-stack.ts`
  - [ ] `lib/stacks/auth-stack.ts`
  - [ ] `lib/stacks/api-stack.ts`
  - [ ] `lib/stacks/processing-stack.ts`
  - [ ] `lib/stacks/monitoring-stack.ts`

#### CDK Bootstrap
- [ ] CDK bootstrapped in target region:
  ```bash
  aws cloudformation describe-stacks --stack-name CDKToolkit --profile customer-care-dev
  # Should show CREATE_COMPLETE status
  ```
- [ ] CDKToolkit S3 bucket created (visible in S3 console)
- [ ] CDKToolkit IAM roles created

#### Tagging Strategy
- [ ] Tagging policy defined in `lib/config/tags.ts`
- [ ] Tags include: Project, Environment, ManagedBy, CostCenter, Owner
- [ ] Tags can be imported and applied to stacks

### 📦 Deliverables Collected
- [ ] AWS Account ID: `___________________________`
- [ ] AWS Region: `___________________________`
- [ ] CDK Bootstrap complete: ✓

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 3: AWS Storage Layer Setup

### ✅ Completion Criteria

#### S3 Bucket
- [ ] Storage Stack CDK code written
- [ ] S3 bucket definition includes:
  - [ ] Encryption enabled (S3_MANAGED or KMS)
  - [ ] Versioning enabled
  - [ ] Block public access enabled
  - [ ] Lifecycle rule for Glacier transition (90 days)
  - [ ] CORS configuration for presigned URLs
- [ ] Storage Stack synthesizes without errors: `cdk synth StorageStack`
- [ ] Storage Stack deployed successfully: `cdk deploy StorageStack`
- [ ] S3 bucket created and visible in AWS Console
- [ ] Bucket name noted: `___________________________`

#### DynamoDB Tables
- [ ] Three DynamoDB tables defined:
  1. **call-summaries** table:
     - [ ] Partition key: `call_id` (String)
     - [ ] Sort key: `timestamp` (String)
     - [ ] GSI 1: `status-timestamp-index`
     - [ ] GSI 2: `user-timestamp-index`
     - [ ] GSI 3: `date-index`
     - [ ] Point-in-time recovery enabled
     - [ ] DynamoDB Streams enabled
     - [ ] Encryption enabled
  
  2. **websocket-connections** table:
     - [ ] Partition key: `connectionId` (String)
     - [ ] TTL attribute configured
     - [ ] Billing mode: PAY_PER_REQUEST
  
  3. **users** table:
     - [ ] Partition key: `email` (String)
     - [ ] Billing mode: PAY_PER_REQUEST

- [ ] All tables deployed successfully
- [ ] Tables visible in DynamoDB console
- [ ] Table names noted:
  - `___________________________` (call-summaries)
  - `___________________________` (websocket-connections)
  - `___________________________` (users)

#### Verification Tests
- [ ] Can describe S3 bucket:
  ```bash
  aws s3 ls --profile customer-care-dev | grep customer-care-audio
  ```
- [ ] Can list DynamoDB tables:
  ```bash
  aws dynamodb list-tables --profile customer-care-dev
  ```
- [ ] Can put test item in DynamoDB:
  ```bash
  aws dynamodb put-item --table-name customer-care-summaries-dev \
    --item '{"call_id":{"S":"test-001"},"timestamp":{"S":"2026-01-31T10:00:00Z"},"status":{"S":"TEST"}}' \
    --profile customer-care-dev
  ```
- [ ] Can scan table to see test item:
  ```bash
  aws dynamodb scan --table-name customer-care-summaries-dev --profile customer-care-dev
  ```
- [ ] Can delete test item after verification

### 📦 Deliverables Collected
- [ ] S3 Bucket Name: `___________________________`
- [ ] DynamoDB Table Names:
  - Call Summaries: `___________________________`
  - WebSocket Connections: `___________________________`
  - Users: `___________________________`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 4: Google-AWS Communication Bridge

### ✅ Completion Criteria

#### Secrets Stored in AWS Secrets Manager
- [ ] Google service account credentials uploaded to Secrets Manager
  - Secret name: `customer-care/google-service-account`
  - [ ] Secret created successfully
  - [ ] Secret ARN noted: `___________________________`

- [ ] Google Drive folder ID stored in Secrets Manager
  - Secret name: `customer-care/google-drive-folder-id`
  - [ ] Secret created successfully
  - [ ] Secret ARN noted: `___________________________`

- [ ] Webhook verification token generated and stored
  - Secret name: `customer-care/webhook-token`
  - [ ] Token generated: `openssl rand -hex 32`
  - [ ] Secret created successfully
  - [ ] Token saved locally in `webhook-token.txt`
  - [ ] Secret ARN noted: `___________________________`

#### Secret Verification
- [ ] Can list secrets:
  ```bash
  aws secretsmanager list-secrets --profile customer-care-dev | grep customer-care
  ```
- [ ] Can retrieve test secret (verify it's accessible):
  ```bash
  aws secretsmanager get-secret-value \
    --secret-id customer-care/google-service-account \
    --profile customer-care-dev
  # Should return secret value (JSON)
  ```

#### IAM Policy for Secrets Access
- [ ] IAM policy created: `CustomerCareSecretsReadPolicy`
- [ ] Policy allows `secretsmanager:GetSecretValue` action
- [ ] Policy restricts to `customer-care/*` secrets only
- [ ] Policy ARN noted: `___________________________`

#### Security Verification
- [ ] Service account JSON file NOT in git repository
- [ ] Service account JSON file NOT in any public location
- [ ] Webhook token stored securely
- [ ] .gitignore includes `*.json`, `webhook-token.txt`

### 📦 Deliverables Collected
- [ ] Secret ARNs:
  - Google Service Account: `___________________________`
  - Drive Folder ID: `___________________________`
  - Webhook Token: `___________________________`
- [ ] IAM Policy ARN: `___________________________`
- [ ] Webhook Token (saved locally): `___________________________`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 5: Data Ingestion Layer

### ✅ Completion Criteria

#### Lambda Function Code
- [ ] Webhook handler Lambda code written (`lambdas/webhook-handler/index.py`)
- [ ] Code includes:
  - [ ] Webhook token validation
  - [ ] Google Drive file download logic
  - [ ] S3 upload logic
  - [ ] DynamoDB record creation
  - [ ] Step Functions trigger (will be added later)
  - [ ] Error handling and logging
  - [ ] CloudWatch metrics emission

- [ ] `requirements.txt` created with all dependencies
- [ ] Lambda function packaged: `webhook-handler.zip` created
- [ ] Package size < 250MB (or using Lambda layers)

#### API Gateway and Lambda Deployment
- [ ] API Stack CDK code written (`lib/stacks/api-stack.ts`)
- [ ] Lambda function defined in CDK with:
  - [ ] Runtime: Python 3.11
  - [ ] Timeout: 5 minutes
  - [ ] Memory: 1024 MB
  - [ ] Environment variables set
  - [ ] IAM permissions granted (S3, DynamoDB, Secrets Manager)

- [ ] API Gateway REST API defined
- [ ] POST /webhook/gdrive endpoint created
- [ ] Lambda integration configured
- [ ] API Stack synthesizes: `cdk synth ApiStack`
- [ ] API Stack deployed: `cdk deploy ApiStack`
- [ ] API Gateway endpoint URL noted: `___________________________`

#### Google Drive Webhook Configuration
- [ ] Webhook setup script created (`scripts/setup-google-webhook.py`)
- [ ] Script configured with:
  - [ ] API Gateway endpoint URL
  - [ ] Webhook token
  - [ ] Service account credentials
  - [ ] Folder ID
- [ ] Webhook registration script executed successfully
- [ ] Google API returns success response
- [ ] Channel ID noted: `___________________________`
- [ ] Resource ID noted: `___________________________`

#### End-to-End Upload Test
- [ ] Test audio file uploaded to Google Drive "Incoming" folder
- [ ] Webhook notification received (check CloudWatch Logs):
  ```bash
  aws logs tail /aws/lambda/webhook-handler --follow --profile customer-care-dev
  ```
- [ ] File downloaded from Google Drive (log shows download)
- [ ] File uploaded to S3:
  ```bash
  aws s3 ls s3://BUCKET-NAME/raw-audio/ --recursive --profile customer-care-dev
  # Should show uploaded file
  ```
- [ ] DynamoDB record created:
  ```bash
  aws dynamodb scan --table-name SUMMARIES-TABLE --profile customer-care-dev
  # Should show record with status "UPLOADED"
  ```
- [ ] CloudWatch metrics show successful execution
- [ ] No errors in Lambda logs

#### Performance Verification
- [ ] Webhook responds within 10 seconds of file upload
- [ ] File download completes within 2 minutes
- [ ] S3 upload completes successfully
- [ ] Total webhook handler execution time < 5 minutes

### 📦 Deliverables Collected
- [ ] API Gateway Endpoint: `___________________________`
- [ ] Lambda Function ARN: `___________________________`
- [ ] Google Webhook Channel ID: `___________________________`
- [ ] Google Webhook Resource ID: `___________________________`
- [ ] Test Call ID: `___________________________`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 6: AI Services Configuration

### ✅ Completion Criteria

#### Amazon Transcribe Setup
- [ ] Amazon Transcribe available in target region
- [ ] Can execute Transcribe CLI commands:
  ```bash
  aws transcribe help --profile customer-care-dev
  ```
- [ ] Test audio file uploaded to S3
- [ ] Test transcription job created and started
- [ ] Test job completes successfully:
  ```bash
  aws transcribe get-transcription-job \
    --transcription-job-name test-transcription-001 \
    --profile customer-care-dev
  # Should show status "COMPLETED"
  ```
- [ ] Transcription output downloaded from S3
- [ ] Output includes:
  - [ ] Full transcript text
  - [ ] Speaker labels
  - [ ] Timestamps
  - [ ] Confidence scores
- [ ] Transcription accuracy acceptable (>85%)

#### Amazon Bedrock Model Access
- [ ] Navigated to Amazon Bedrock console
- [ ] Requested model access for:
  - [ ] Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)
  - [ ] Claude 3 Haiku (optional)
- [ ] Model access status: "Access granted"
- [ ] Models available in selected region (us-east-1 or chosen region)

#### Bedrock Testing
- [ ] Test script created (`scripts/test-bedrock.py`)
- [ ] Required AWS SDK (boto3) installed
- [ ] Test script executes without errors
- [ ] Bedrock returns response in JSON format
- [ ] Response contains all required fields:
  - [ ] `call_date`
  - [ ] `issue_sentence`
  - [ ] `key_details`
  - [ ] `action_items`
  - [ ] `next_steps`
  - [ ] `sentiment`
- [ ] Response time < 5 seconds
- [ ] Summary quality acceptable (manual review)

#### Prompt Optimization
- [ ] Prompt template created (`config/bedrock-prompt-template.txt`)
- [ ] Prompt tested with multiple transcript types:
  - [ ] Short calls (< 2 minutes)
  - [ ] Long calls (> 10 minutes)
  - [ ] Emotional content
  - [ ] Technical issues
  - [ ] Clear resolutions
  - [ ] Unclear/incomplete calls
- [ ] JSON parsing success rate: 100% (all tests)
- [ ] Field completeness: 100% (all required fields present)
- [ ] Summary relevance rating: ≥ 4/5
- [ ] Token usage per call measured: _________ tokens (should be < 2000)

#### Service Quotas
- [ ] Current quotas checked:
  - [ ] Amazon Transcribe concurrent jobs: _________ (need ≥ 5)
  - [ ] Amazon Bedrock tokens per minute: _________ (need ≥ 2500)
- [ ] Quota increase requests submitted (if needed)
- [ ] Quota increases approved (if needed)

### 📦 Deliverables Collected
- [ ] Test transcription job output saved
- [ ] Bedrock model IDs confirmed:
  - Claude 3.5 Sonnet: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- [ ] Optimized prompt template saved
- [ ] Average token usage per call: _________ tokens
- [ ] Service quotas sufficient: ✓

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 7: Processing Orchestration Layer

### ✅ Completion Criteria

#### State Machine Design
- [ ] State machine definition created (`config/step-functions-definition.json`)
- [ ] Definition includes all states:
  - [ ] UpdateStatusTranscribing
  - [ ] TranscribeAudio
  - [ ] ProcessTranscript
  - [ ] UpdateStatusSummarizing
  - [ ] GenerateSummary
  - [ ] SaveToDynamoDB
  - [ ] NotifyFrontend
  - [ ] MarkAsFailed (error handler)
- [ ] Error handling configured:
  - [ ] Catch blocks on all processing states
  - [ ] Retry logic with exponential backoff
  - [ ] Dead-letter queue for unrecoverable failures
- [ ] Definition is valid JSON (no syntax errors)

#### Processing Lambda Functions
- [ ] **Process Transcript Lambda** implemented (`lambdas/process-transcript/`)
  - [ ] Retrieves Transcribe job results
  - [ ] Parses JSON output
  - [ ] Separates speaker segments
  - [ ] Formats conversation flow
  - [ ] Extracts metadata (duration, talk time)
  - [ ] Saves formatted transcript to S3
  - [ ] Returns structured data
  - [ ] Packaged as ZIP

- [ ] **Generate Summary Lambda** implemented (`lambdas/generate-summary/`)
  - [ ] Loads prompt template
  - [ ] Formats prompt with transcript
  - [ ] Calls Bedrock API
  - [ ] Parses JSON response
  - [ ] Validates all fields present
  - [ ] Handles throttling errors
  - [ ] Packaged as ZIP

- [ ] **Save Summary Lambda** implemented (`lambdas/save-summary/`)
  - [ ] Saves summary JSON to S3
  - [ ] Updates DynamoDB record
  - [ ] Sets status to "COMPLETED"
  - [ ] Includes all S3 URLs
  - [ ] Emits success metrics
  - [ ] Packaged as ZIP

#### Processing Stack Deployment
- [ ] Processing Stack CDK code written (`lib/stacks/processing-stack.ts`)
- [ ] All Lambda functions defined with correct:
  - [ ] Runtime (Python 3.11)
  - [ ] Memory allocation
  - [ ] Timeout settings
  - [ ] Environment variables
  - [ ] IAM permissions
- [ ] Step Functions state machine defined
- [ ] IAM roles granted necessary permissions:
  - [ ] Transcribe access
  - [ ] Bedrock access
  - [ ] S3 read/write
  - [ ] DynamoDB read/write
- [ ] Processing Stack synthesizes: `cdk synth ProcessingStack`
- [ ] Processing Stack deploys: `cdk deploy ProcessingStack`
- [ ] State machine ARN noted: `___________________________`

#### End-to-End Processing Test
- [ ] Test execution started manually:
  ```bash
  aws stepfunctions start-execution \
    --state-machine-arn ARN \
    --input '{"call_id":"test-001",...}' \
    --profile customer-care-dev
  ```
- [ ] Execution visible in Step Functions console
- [ ] Execution progresses through all states
- [ ] Transcribe job completes successfully
- [ ] Transcript saved to S3:
  ```bash
  aws s3 ls s3://BUCKET/transcripts/ --profile customer-care-dev
  ```
- [ ] Summary generated by Bedrock
- [ ] Summary saved to S3:
  ```bash
  aws s3 ls s3://BUCKET/summaries/ --profile customer-care-dev
  ```
- [ ] DynamoDB record updated with status "COMPLETED":
  ```bash
  aws dynamodb get-item \
    --table-name TABLE \
    --key '{"call_id":{"S":"test-001"}}' \
    --profile customer-care-dev
  ```
- [ ] Execution completes with status "SUCCEEDED"
- [ ] No errors in CloudWatch Logs

#### Performance Verification
- [ ] Total processing time < 5 minutes for 5-minute call
- [ ] Transcription time < 3 minutes
- [ ] Summary generation time < 1 minute
- [ ] No timeouts in any Lambda function
- [ ] No throttling errors

#### Error Handling Test
- [ ] Test failure scenario (e.g., invalid S3 key)
- [ ] Execution retries failed state (check retry count in logs)
- [ ] After max retries, execution enters MarkAsFailed state
- [ ] DynamoDB status updated to "FAILED"
- [ ] Error message recorded in DynamoDB

### 📦 Deliverables Collected
- [ ] Step Functions State Machine ARN: `___________________________`
- [ ] Lambda Function ARNs:
  - Process Transcript: `___________________________`
  - Generate Summary: `___________________________`
  - Save Summary: `___________________________`
- [ ] Test Execution ARN: `___________________________`
- [ ] Average Processing Time: _________ minutes

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 8: Backend API Layer

### ✅ Completion Criteria

#### API Lambda Functions Implemented
- [ ] **List Summaries Lambda** (`lambdas/api-list-summaries/`)
  - [ ] Parses query parameters (limit, status, date range, lastKey)
  - [ ] Queries DynamoDB with filters
  - [ ] Returns paginated results
  - [ ] Handles errors gracefully
  - [ ] Returns CORS headers
  - [ ] Packaged as ZIP

- [ ] **Get Summary Detail Lambda** (`lambdas/api-get-summary/`)
  - [ ] Extracts call_id from path parameters
  - [ ] Queries DynamoDB
  - [ ] Returns 404 if not found
  - [ ] Returns complete summary object
  - [ ] Packaged as ZIP

- [ ] **Get Audio URL Lambda** (`lambdas/api-get-audio-url/`)
  - [ ] Generates presigned URL for audio file
  - [ ] URL expires in 1 hour
  - [ ] Returns URL and expiration time
  - [ ] Packaged as ZIP

- [ ] **Get Transcript Lambda** (`lambdas/api-get-transcript/`)
  - [ ] Retrieves transcript from S3
  - [ ] Returns formatted transcript with speaker labels
  - [ ] Packaged as ZIP

#### API Gateway Endpoints
- [ ] API Stack updated with all endpoints:
  - [ ] GET /summaries (list)
  - [ ] GET /summaries/{call_id} (detail)
  - [ ] GET /summaries/{call_id}/audio (audio URL)
  - [ ] GET /summaries/{call_id}/transcript (transcript)
- [ ] Lambda integrations configured
- [ ] CORS enabled on all endpoints
- [ ] API Stack redeployed: `cdk deploy ApiStack`

#### API Testing
- [ ] **List Summaries** test:
  ```bash
  curl https://API-URL/summaries?limit=10
  ```
  - [ ] Returns 200 status
  - [ ] Returns array of summaries
  - [ ] Pagination token included
  - [ ] Response time < 500ms

- [ ] **Get Summary Detail** test:
  ```bash
  curl https://API-URL/summaries/test-001
  ```
  - [ ] Returns 200 status for existing call
  - [ ] Returns complete summary object
  - [ ] Returns 404 for non-existent call
  - [ ] Response time < 500ms

- [ ] **Get Audio URL** test:
  ```bash
  curl https://API-URL/summaries/test-001/audio
  ```
  - [ ] Returns 200 status
  - [ ] Returns presigned URL
  - [ ] URL works (can download file)
  - [ ] URL expires after 1 hour
  - [ ] Response time < 500ms

- [ ] **Get Transcript** test:
  ```bash
  curl https://API-URL/summaries/test-001/transcript
  ```
  - [ ] Returns 200 status
  - [ ] Returns transcript with speaker labels
  - [ ] Response time < 500ms

#### API Documentation
- [ ] OpenAPI specification created (`api-docs/openapi.yaml`)
- [ ] Specification includes all endpoints
- [ ] Request/response schemas defined
- [ ] Authentication requirements documented
- [ ] Example requests/responses included
- [ ] OpenAPI spec validates (no errors)

#### Performance Verification
- [ ] P95 latency < 500ms for all endpoints (tested with load)
- [ ] No 5xx errors during testing
- [ ] Error responses return proper status codes and messages

### 📦 Deliverables Collected
- [ ] API Endpoints:
  - List: `___________________________/summaries`
  - Detail: `___________________________/summaries/{call_id}`
  - Audio URL: `___________________________/summaries/{call_id}/audio`
  - Transcript: `___________________________/summaries/{call_id}/transcript`
- [ ] OpenAPI Specification: `api-docs/openapi.yaml`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 9: Authentication and Authorization

### ✅ Completion Criteria

#### Cognito User Pool Creation
- [ ] Auth Stack CDK code written (`lib/stacks/auth-stack.ts`)
- [ ] User Pool configured with:
  - [ ] Email sign-in
  - [ ] Password policy (8+ chars, upper, lower, digit)
  - [ ] Email verification required
  - [ ] MFA optional
  - [ ] Account recovery via email
- [ ] User groups defined:
  - [ ] caseworkers
  - [ ] supervisors
  - [ ] admins
- [ ] App client configured with:
  - [ ] USER_PASSWORD_AUTH flow
  - [ ] USER_SRP_AUTH flow
  - [ ] Callback URLs
  - [ ] Logout URLs
- [ ] Auth Stack synthesizes: `cdk synth AuthStack`
- [ ] Auth Stack deploys: `cdk deploy AuthStack`
- [ ] User Pool ID noted: `___________________________`
- [ ] User Pool Client ID noted: `___________________________`

#### Test Users Created
- [ ] Admin user created:
  ```bash
  aws cognito-idp admin-create-user --user-pool-id USER-POOL-ID --username admin@example.com
  ```
  - [ ] User exists in Cognito console
  - [ ] User added to "admins" group
  - [ ] Temporary password set

- [ ] Caseworker user created:
  ```bash
  aws cognito-idp admin-create-user --user-pool-id USER-POOL-ID --username caseworker@example.com
  ```
  - [ ] User exists in Cognito console
  - [ ] User added to "caseworkers" group
  - [ ] Temporary password set

- [ ] Test user credentials noted securely

#### API Gateway Integration
- [ ] Cognito authorizer added to API Gateway
- [ ] All protected endpoints updated to require authentication
- [ ] API Stack redeployed with authorizer
- [ ] Endpoints show authorizer in API Gateway console

#### Authentication Testing
- [ ] Can authenticate with test credentials:
  ```bash
  aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id CLIENT-ID \
    --auth-parameters USERNAME=caseworker@example.com,PASSWORD=TestPass123!
  ```
  - [ ] Returns access token
  - [ ] Returns ID token
  - [ ] Returns refresh token
  - [ ] Tokens valid for expected duration

- [ ] API call with valid token succeeds:
  ```bash
  curl -H "Authorization: Bearer ID-TOKEN" https://API-URL/summaries
  ```
  - [ ] Returns 200 status
  - [ ] Returns data

- [ ] API call without token fails:
  ```bash
  curl https://API-URL/summaries
  ```
  - [ ] Returns 401 Unauthorized

- [ ] API call with invalid token fails:
  ```bash
  curl -H "Authorization: Bearer INVALID-TOKEN" https://API-URL/summaries
  ```
  - [ ] Returns 401 Unauthorized

#### Authorization Testing
- [ ] JWT tokens contain group claims
- [ ] Can decode token and see user groups
- [ ] Token expiration works (tokens expire after 1 hour)
- [ ] Refresh token works (can get new access token)

### 📦 Deliverables Collected
- [ ] User Pool ID: `___________________________`
- [ ] User Pool Client ID: `___________________________`
- [ ] User Pool ARN: `___________________________`
- [ ] Test User Credentials (admin): `___________________________`
- [ ] Test User Credentials (caseworker): `___________________________`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 10: Real-Time Notification System

### ✅ Completion Criteria

#### WebSocket API Creation
- [ ] WebSocket Stack CDK code written (`lib/stacks/websocket-stack.ts`)
- [ ] Connection Lambda implemented (`lambdas/websocket-connect/`)
  - [ ] Validates JWT token from query string
  - [ ] Stores connection in DynamoDB
  - [ ] Sets TTL for 24 hours
  - [ ] Packaged as ZIP
- [ ] Disconnect Lambda implemented (`lambdas/websocket-disconnect/`)
  - [ ] Removes connection from DynamoDB
  - [ ] Packaged as ZIP
- [ ] WebSocket API defined with routes:
  - [ ] $connect
  - [ ] $disconnect
  - [ ] $default
- [ ] WebSocket Stack synthesizes: `cdk synth WebSocketStack`
- [ ] WebSocket Stack deploys: `cdk deploy WebSocketStack`
- [ ] WebSocket URL noted: `___________________________`

#### Notification Lambda
- [ ] Notification Lambda implemented (`lambdas/websocket-notify/`)
  - [ ] Queries all active connections from DynamoDB
  - [ ] Posts message to each connection via API Gateway Management API
  - [ ] Handles stale connections (deletes if post fails)
  - [ ] Message format includes: type, data
  - [ ] Packaged as ZIP
- [ ] Notification Lambda integrated with Step Functions (added as final state)
- [ ] Processing Stack redeployed with notification step

#### WebSocket Connection Testing
- [ ] Test script created (`scripts/test-websocket.py`)
- [ ] Required package installed: `pip install websockets`
- [ ] Can establish WebSocket connection:
  ```python
  # Connection with valid token succeeds
  ```
  - [ ] Connection established
  - [ ] Connection ID stored in DynamoDB
  - [ ] TTL set correctly

- [ ] Connection with invalid token fails:
  - [ ] Returns 401 or connection closes immediately

- [ ] Connection persists:
  - [ ] Can keep connection open for > 1 minute
  - [ ] No unexpected disconnections

#### Notification Testing
- [ ] Trigger test call processing (upload file to Google Drive)
- [ ] WebSocket client receives notification when processing completes
- [ ] Notification format correct:
  ```json
  {
    "type": "NEW_SUMMARY",
    "data": {
      "call_id": "...",
      "issue_sentence": "...",
      "sentiment": "...",
      "timestamp": "..."
    }
  }
  ```
- [ ] Notification received within 5 seconds of processing completion

#### Reconnection Testing
- [ ] Manually disconnect WebSocket
- [ ] Client automatically reconnects (if reconnection logic implemented)
- [ ] OR can manually reconnect and establish new connection

#### Multiple Connections
- [ ] Can establish multiple WebSocket connections (different users)
- [ ] All connections receive broadcast notifications
- [ ] Connections tracked separately in DynamoDB

### 📦 Deliverables Collected
- [ ] WebSocket URL: `___________________________`
- [ ] WebSocket API ID: `___________________________`
- [ ] Notification Lambda ARN: `___________________________`

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 11: Frontend Application

### ✅ Completion Criteria

#### React Project Setup
- [ ] React project initialized with Vite and TypeScript
- [ ] All dependencies installed:
  - [ ] @aws-amplify/auth
  - [ ] axios
  - [ ] react-router-dom@6
  - [ ] @tanstack/react-query
  - [ ] @mui/material (or chosen UI library)
  - [ ] react-hook-form
  - [ ] date-fns
  - [ ] react-h5-audio-player
- [ ] Folder structure created:
  - [ ] src/components/Auth
  - [ ] src/components/Dashboard
  - [ ] src/components/Layout
  - [ ] src/components/Common
  - [ ] src/services
  - [ ] src/hooks
  - [ ] src/contexts
  - [ ] src/types
- [ ] Environment variables configured in `.env`
- [ ] Can run development server: `npm run dev`

#### Authentication Implementation
- [ ] Amplify configured with Cognito credentials
- [ ] AuthContext created and working
- [ ] Login component implemented
- [ ] Protected Route component implemented
- [ ] Can log in with test user credentials
- [ ] Successful login redirects to dashboard
- [ ] Failed login shows error message
- [ ] Logout functionality works
- [ ] Session persists across page refresh

#### API Service Layer
- [ ] API client created with axios
- [ ] Auth token interceptor configured
- [ ] Token automatically added to requests
- [ ] API functions defined:
  - [ ] summariesApi.list()
  - [ ] summariesApi.getById()
  - [ ] summariesApi.getAudioUrl()
  - [ ] summariesApi.getTranscript()
- [ ] Can fetch data from backend API
- [ ] Error handling implemented

#### Dashboard Components
- [ ] **Summary List Component**:
  - [ ] Displays grid/table of summaries
  - [ ] Shows: date, issue, sentiment, status, duration
  - [ ] Implements pagination (20 items per page)
  - [ ] Status badges color-coded
  - [ ] Click to view detail
  
- [ ] **Filters and Search**:
  - [ ] Status filter dropdown
  - [ ] Date range picker
  - [ ] Search input
  - [ ] Clear filters button
  - [ ] Filters work correctly

- [ ] **Summary Detail Component**:
  - [ ] Header with call metadata
  - [ ] Issue sentence prominently displayed
  - [ ] Key details shown as bullet list
  - [ ] Action items shown as numbered list
  - [ ] Next steps shown as numbered list
  - [ ] Full transcript in expandable section
  - [ ] Speaker labels visible
  - [ ] Timestamps visible

- [ ] **Audio Player**:
  - [ ] Embedded in detail view
  - [ ] Loads audio via presigned URL
  - [ ] Play/pause controls work
  - [ ] Seek bar works
  - [ ] Volume control works
  - [ ] Audio plays without errors

#### WebSocket Integration
- [ ] WebSocket hook implemented (`useWebSocket.ts`)
- [ ] WebSocket connects on login
- [ ] Connection status indicator visible
- [ ] New summary notification appears when received
- [ ] Toast/alert shows notification
- [ ] Summary list updates automatically
- [ ] Reconnection works after disconnect

#### Responsive Design
- [ ] Layout responsive on:
  - [ ] Desktop (1920x1080)
  - [ ] Tablet (768x1024)
  - [ ] Mobile (375x667)
- [ ] Navigation menu works on mobile
- [ ] All components readable on small screens
- [ ] No horizontal scrolling
- [ ] Touch targets appropriately sized

#### Build and Performance
- [ ] Production build succeeds:
  ```bash
  npm run build
  ```
  - [ ] No build errors
  - [ ] Build output in `dist/` directory
- [ ] Build size reasonable (< 2MB for main bundle)
- [ ] Page load time < 3 seconds (measured)
- [ ] No console errors in browser
- [ ] Lighthouse score > 80 (optional but recommended)

#### User Flow Testing
- [ ] **Login Flow**:
  - [ ] Can access login page
  - [ ] Can enter credentials
  - [ ] Successful login redirects to dashboard
  - [ ] Failed login shows error
  
- [ ] **View Summaries**:
  - [ ] Dashboard loads and displays summaries
  - [ ] Pagination works
  - [ ] Can navigate to next/previous page
  
- [ ] **Filter and Search**:
  - [ ] Filters apply correctly
  - [ ] Search returns relevant results
  - [ ] Can clear filters
  
- [ ] **View Detail**:
  - [ ] Can click summary to view detail
  - [ ] Detail page loads all data
  - [ ] Audio player works
  - [ ] Transcript displays correctly
  - [ ] Can navigate back to list
  
- [ ] **Real-time Updates**:
  - [ ] Upload new test call
  - [ ] Notification appears in dashboard
  - [ ] New summary visible without refresh

### 📦 Deliverables Collected
- [ ] Frontend repository with all code
- [ ] Production build in `dist/` directory
- [ ] Environment configuration documented
- [ ] User guide (screenshots of key features)

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 12: Monitoring and Observability

### ✅ Completion Criteria

#### CloudWatch Dashboards
- [ ] Monitoring Stack CDK code written (`lib/stacks/monitoring-stack.ts`)
- [ ] **Dashboard 1: Processing Pipeline** created with widgets:
  - [ ] Calls uploaded per hour
  - [ ] Processing time (P50, P95, P99)
  - [ ] Success rate (%)
  - [ ] Failure rate (%)
  - [ ] Step Functions execution graph
  - [ ] Error distribution by type

- [ ] **Dashboard 2: API Performance** created with widgets:
  - [ ] API latency by endpoint (P50, P95, P99)
  - [ ] Request count per endpoint
  - [ ] 4xx error rate
  - [ ] 5xx error rate
  - [ ] Throttling events

- [ ] **Dashboard 3: Cost Tracking** created with widgets:
  - [ ] Transcribe minutes used
  - [ ] Bedrock token consumption
  - [ ] Lambda invocations
  - [ ] S3 storage size
  - [ ] Monthly cost projection

- [ ] Monitoring Stack synthesizes: `cdk synth MonitoringStack`
- [ ] Monitoring Stack deploys: `cdk deploy MonitoringStack`
- [ ] All dashboards visible in CloudWatch console
- [ ] Dashboards auto-refresh every 1 minute

#### CloudWatch Alarms
- [ ] **Critical Alarms** (immediate notification):
  - [ ] Step Function failure rate > 10%
  - [ ] API Gateway 5xx errors > 5 per minute
  - [ ] Lambda function errors > 10 per minute
  - [ ] DynamoDB throttling events
  
- [ ] **Warning Alarms** (business hours notification):
  - [ ] Average processing time > 10 minutes
  - [ ] S3 storage > 80% of budget
  - [ ] Bedrock throttling events
  - [ ] Lambda concurrent executions > 80% of limit

- [ ] All alarms created and in "OK" state initially
- [ ] Alarm actions configured

#### SNS Notifications
- [ ] SNS topic created: `customer-care-alarms`
- [ ] Email subscription added
- [ ] Subscription confirmed (check email)
- [ ] All alarms linked to SNS topic
- [ ] Test notification sent and received

#### Testing Monitoring
- [ ] Dashboards display real data from previous tests
- [ ] Metrics visible for:
  - [ ] Lambda invocations
  - [ ] Step Functions executions
  - [ ] API Gateway requests
  - [ ] DynamoDB operations
- [ ] Time ranges work (1h, 3h, 12h, 1d, 1w)

#### Alarm Testing
- [ ] Trigger test alarm (e.g., force Lambda error)
- [ ] Alarm state changes to "ALARM"
- [ ] Email notification received within 5 minutes
- [ ] Email contains:
  - [ ] Alarm name
  - [ ] Metric name
  - [ ] Threshold breached
  - [ ] Current value
  - [ ] Link to dashboard/logs
- [ ] Alarm auto-resolves when metric returns to normal
- [ ] "OK" notification received

### 📦 Deliverables Collected
- [ ] Dashboard URLs:
  - Processing Pipeline: `___________________________`
  - API Performance: `___________________________`
  - Cost Tracking: `___________________________`
- [ ] SNS Topic ARN: `___________________________`
- [ ] Number of Alarms Configured: _________

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 13: Security Hardening

### ✅ Completion Criteria

#### Encryption Verification
- [ ] **S3 Encryption**:
  - [ ] Server-side encryption enabled (verified in S3 console)
  - [ ] Encryption type: AES-256 or KMS
  
- [ ] **DynamoDB Encryption**:
  - [ ] Encryption at rest enabled (verified in DynamoDB console)
  - [ ] Encryption type: AWS managed or customer managed KMS
  
- [ ] **Secrets Manager Encryption**:
  - [ ] All secrets encrypted with KMS (default)
  
- [ ] **CloudWatch Logs Encryption**:
  - [ ] Log groups encrypted with KMS:
    ```bash
    aws logs describe-log-groups --profile customer-care-dev
    # Check kmsKeyId field
    ```

- [ ] **In-Transit Encryption**:
  - [ ] All API calls use HTTPS (verified)
  - [ ] WebSocket uses WSS (verified)
  - [ ] Google Drive API calls use HTTPS (verified)

#### AWS WAF Configuration
- [ ] WAF WebACL created
- [ ] WAF rules configured:
  - [ ] Rate limiting (100 requests per 5 minutes per IP)
  - [ ] Geo-blocking (optional)
  - [ ] Common attack protection (SQL injection, XSS)
- [ ] WAF associated with API Gateway
- [ ] WAF metrics visible in CloudWatch
- [ ] Test rate limiting:
  - [ ] Make 101 requests rapidly
  - [ ] 101st request blocked (429 response)

#### CloudTrail Audit Logging
- [ ] CloudTrail created
- [ ] Multi-region trail enabled
- [ ] Management events logged
- [ ] Data events enabled for S3 bucket (optional)
- [ ] Logs delivered to S3 bucket
- [ ] Log file validation enabled
- [ ] CloudTrail logging active:
  ```bash
  aws cloudtrail get-trail-status --name customer-care-audit-trail --profile customer-care-dev
  # Should show "IsLogging": true
  ```
- [ ] Test logs visible in S3:
  ```bash
  aws s3 ls s3://cloudtrail-bucket/AWSLogs/ACCOUNT-ID/CloudTrail/ --profile customer-care-dev
  ```

#### IAM Security Audit
- [ ] Run IAM Access Analyzer (if enabled)
- [ ] Review all IAM policies:
  - [ ] No policies with `*` actions and `*` resources
  - [ ] All policies follow least privilege principle
  - [ ] No unused policies
- [ ] Review IAM roles:
  - [ ] All roles have trust policies
  - [ ] No roles with overly permissive trust policies
- [ ] Review IAM users:
  - [ ] No users with access keys older than 90 days
  - [ ] Root user not used for daily operations
  - [ ] Root user MFA enabled

#### Security Group and Network Review
- [ ] Review security groups (if using VPC):
  - [ ] No security groups with 0.0.0.0/0 on sensitive ports
  - [ ] Egress rules appropriately restrictive
- [ ] API Gateway:
  - [ ] Resource policies reviewed (if any)
  - [ ] Endpoint type appropriate (Regional recommended)
- [ ] S3 Bucket Policies:
  - [ ] No public access allowed
  - [ ] Bucket policy reviewed and minimal

#### Security Scanning
- [ ] Run AWS Security Hub (if enabled):
  - [ ] No critical findings
  - [ ] High findings reviewed and remediated
- [ ] Run Trusted Advisor security checks:
  - [ ] No red flags for security
- [ ] Dependency scanning:
  - [ ] `npm audit` run on frontend (no high/critical vulnerabilities)
  - [ ] `pip check` or `safety check` run on Lambda code

### 🔒 Security Checklist Summary
- [ ] All data encrypted at rest
- [ ] All data encrypted in transit
- [ ] WAF protecting API Gateway
- [ ] CloudTrail logging all actions
- [ ] IAM policies follow least privilege
- [ ] No overly permissive security groups
- [ ] No critical security findings
- [ ] Secrets stored securely (not in code)
- [ ] Regular security scans scheduled

### 📦 Deliverables Collected
- [ ] WAF WebACL ARN: `___________________________`
- [ ] CloudTrail Name: `___________________________`
- [ ] Security audit report completed
- [ ] All critical findings resolved: ✓

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 14: Testing and Validation

### ✅ Completion Criteria

#### End-to-End Testing
- [ ] **Complete workflow test** (5 iterations):
  1. [ ] Upload audio file to Google Drive "Incoming" folder
  2. [ ] Webhook receives notification within 10 seconds
  3. [ ] File appears in S3 raw-audio folder within 2 minutes
  4. [ ] DynamoDB status changes: UPLOADED → TRANSCRIBING → SUMMARIZING → COMPLETED
  5. [ ] Processing completes within 5 minutes (timed)
  6. [ ] Transcript saved to S3 transcripts folder
  7. [ ] Summary saved to S3 summaries folder
  8. [ ] Summary appears in dashboard (verify in browser)
  9. [ ] WebSocket notification received
  10. [ ] Audio playback works
  11. [ ] Transcript displays correctly
  12. [ ] All summary fields present and accurate

- [ ] **5 successful runs** (success rate 100%)
- [ ] Average processing time: _________ minutes (must be < 5)
- [ ] No errors in CloudWatch Logs

#### Load Testing
- [ ] Load test script created (`scripts/load-test.py`)
- [ ] Test scenario: 100 concurrent file uploads
- [ ] Load test executed:
  ```bash
  python scripts/load-test.py
  ```
  - [ ] All 100 files uploaded successfully
  - [ ] All 100 files processed successfully
  - [ ] Processing time P95 < 5 minutes
  - [ ] No Lambda timeouts
  - [ ] No throttling errors
  - [ ] No Step Functions failures
  - [ ] System remains responsive during load

- [ ] CloudWatch metrics during load test:
  - [ ] CPU/Memory within limits
  - [ ] No alarms triggered
  - [ ] API latency remains < 500ms

#### Security Testing
- [ ] **Authentication tests**:
  - [ ] API call without token → 401 Unauthorized ✓
  - [ ] API call with invalid token → 401 Unauthorized ✓
  - [ ] API call with expired token → 401 Unauthorized ✓
  - [ ] API call with valid token → 200 Success ✓
  
- [ ] **Authorization tests**:
  - [ ] User can only access authorized resources
  - [ ] Caseworker cannot access admin endpoints (if applicable)
  
- [ ] **Input validation**:
  - [ ] API rejects invalid input formats
  - [ ] SQL injection attempts fail safely
  - [ ] XSS attempts fail safely
  
- [ ] **CORS tests**:
  - [ ] Allowed origin can access API ✓
  - [ ] Disallowed origin blocked ✓

#### Browser Compatibility Testing
- [ ] **Desktop browsers** tested:
  - [ ] Chrome (latest version): ✓
  - [ ] Firefox (latest version): ✓
  - [ ] Safari (latest version): ✓
  - [ ] Edge (latest version): ✓
  
- [ ] **Responsive design** tested on:
  - [ ] Desktop 1920x1080: ✓
  - [ ] Laptop 1366x768: ✓
  - [ ] Tablet 768x1024: ✓
  - [ ] Mobile 375x667: ✓
  
- [ ] **Features tested on all browsers**:
  - [ ] Login
  - [ ] View summaries
  - [ ] Filter/search
  - [ ] View detail
  - [ ] Audio playback
  - [ ] Real-time notifications
  - [ ] Logout

#### Accessibility Testing
- [ ] **Keyboard navigation**:
  - [ ] Can navigate with Tab key
  - [ ] Can activate buttons with Enter/Space
  - [ ] Focus visible on all interactive elements
  
- [ ] **Screen reader** (NVDA/JAWS/VoiceOver):
  - [ ] All buttons/links have labels
  - [ ] Form inputs have labels
  - [ ] Images have alt text
  - [ ] Headings properly structured
  
- [ ] **Color contrast**:
  - [ ] Text readable against background
  - [ ] Links distinguishable
  - [ ] Status badges readable
  
- [ ] **WCAG 2.1 compliance** (optional):
  - [ ] Level AA compliance checked

#### Performance Testing
- [ ] **Page load times** measured:
  - [ ] Login page: _________ seconds (target < 2s)
  - [ ] Dashboard: _________ seconds (target < 3s)
  - [ ] Detail page: _________ seconds (target < 3s)
  
- [ ] **API latency** measured (P95):
  - [ ] List summaries: _________ ms (target < 500ms)
  - [ ] Get summary: _________ ms (target < 500ms)
  - [ ] Get audio URL: _________ ms (target < 500ms)
  - [ ] Get transcript: _________ ms (target < 500ms)
  
- [ ] **Lighthouse audit** (optional):
  - [ ] Performance score: _________ (target > 90)
  - [ ] Accessibility score: _________ (target > 90)
  - [ ] Best Practices score: _________ (target > 90)
  - [ ] SEO score: _________ (target > 90)

#### Test Documentation
- [ ] Test report created with:
  - [ ] Test cases executed (list)
  - [ ] Pass/fail status for each
  - [ ] Performance metrics captured
  - [ ] Issues found and resolution status
  - [ ] Browser compatibility matrix
  - [ ] Load test results
  - [ ] Screenshots of key features

### 📦 Deliverables Collected
- [ ] Test report document
- [ ] Load test results
- [ ] Performance metrics
- [ ] Issue log (if any issues found)
- [ ] Browser compatibility matrix
- [ ] All critical issues resolved: ✓

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________

---

## Stage 15: Production Deployment

### ✅ Completion Criteria

#### Production Environment Preparation
- [ ] Production AWS account configured (if multi-account)
- [ ] Production account ID: `___________________________`
- [ ] CDK bootstrapped in production:
  ```bash
  cdk bootstrap aws://PROD-ACCOUNT/us-east-1 --profile customer-care-prod
  ```
- [ ] Production secrets created in Secrets Manager:
  - [ ] Google service account credentials
  - [ ] Google Drive folder ID (production folder)
  - [ ] Webhook token (new token for production)
- [ ] Production configuration reviewed:
  - [ ] Environment set to "prod"
  - [ ] Resource naming includes "prod"
  - [ ] Appropriate sizing/limits for production

#### Infrastructure Deployment to Production
- [ ] All stacks deployed in order:
  1. [ ] StorageStack: `cdk deploy StorageStack --profile customer-care-prod`
  2. [ ] AuthStack: `cdk deploy AuthStack --profile customer-care-prod`
  3. [ ] ApiStack: `cdk deploy ApiStack --profile customer-care-prod`
  4. [ ] ProcessingStack: `cdk deploy ProcessingStack --profile customer-care-prod`
  5. [ ] WebSocketStack: `cdk deploy WebSocketStack --profile customer-care-prod`
  6. [ ] MonitoringStack: `cdk deploy MonitoringStack --profile customer-care-prod`

- [ ] All stacks show CREATE_COMPLETE status
- [ ] No deployment errors
- [ ] All resources created successfully

#### DNS and SSL Configuration
- [ ] Domain registered or delegated: `___________________________`
- [ ] ACM certificate requested for:
  - [ ] `customercare.yourdomain.com` (frontend)
  - [ ] `api.customercare.yourdomain.com` (API Gateway)
- [ ] Certificate validated via DNS
- [ ] Certificate status: "Issued"
- [ ] Custom domain configured for API Gateway
- [ ] Route53 records created:
  - [ ] A/ALIAS record for API Gateway
  - [ ] A/ALIAS record for CloudFront (frontend)
- [ ] DNS propagation verified:
  ```bash
  nslookup api.customercare.yourdomain.com
  nslookup customercare.yourdomain.com
  ```
- [ ] HTTPS working for both domains

#### Frontend Production Deployment
- [ ] Production environment variables configured:
  ```
  VITE_API_BASE_URL=https://api.customercare.yourdomain.com
  VITE_WEBSOCKET_URL=wss://ws.customercare.yourdomain.com/prod
  VITE_USER_POOL_ID=us-east-1_PRODPOOLID
  VITE_USER_POOL_CLIENT_ID=PRODCLIENTID
  ```
- [ ] Production build created:
  ```bash
  npm run build
  ```
- [ ] Build output reviewed (no errors)
- [ ] Deployed to production hosting:
  - [ ] AWS Amplify OR
  - [ ] S3 + CloudFront
- [ ] Frontend accessible at production URL
- [ ] SSL working (HTTPS)

#### Production User Creation
- [ ] Admin user(s) created in Cognito
- [ ] Caseworker users created
- [ ] Supervisor users created (if applicable)
- [ ] Users added to appropriate groups
- [ ] Temporary passwords sent securely
- [ ] Password change enforced on first login

#### Production Smoke Tests
- [ ] **Upload test**:
  - [ ] Upload test audio to production Google Drive folder
  - [ ] Processing completes successfully
  - [ ] Summary appears in production dashboard
  
- [ ] **Authentication test**:
  - [ ] Can log in with production credentials
  - [ ] Session persists
  - [ ] Logout works
  
- [ ] **Dashboard test**:
  - [ ] Summaries load correctly
  - [ ] Filters work
  - [ ] Pagination works
  
- [ ] **Detail view test**:
  - [ ] Can view summary detail
  - [ ] Audio plays
  - [ ] Transcript displays
  
- [ ] **Real-time notification test**:
  - [ ] Upload new call
  - [ ] Notification received in dashboard
  - [ ] New summary appears without refresh

#### Monitoring and Alerting Verification
- [ ] CloudWatch dashboards accessible and showing data
- [ ] All alarms in "OK" state
- [ ] SNS notifications configured and tested
- [ ] Test alarm triggers successfully:
  - [ ] Notification received via email
  - [ ] Notification received via Slack (if configured)

#### Production Readiness Checklist
- [ ] All infrastructure deployed
- [ ] DNS and SSL configured
- [ ] Frontend deployed and accessible
- [ ] Users created and can log in
- [ ] Smoke tests passing
- [ ] Monitoring active
- [ ] Alerting working
- [ ] Runbook documentation available
- [ ] Disaster recovery plan documented
- [ ] Team trained on system operations
- [ ] Support processes defined

#### Go-Live
- [ ] Go-live date/time scheduled: `___________________________`
- [ ] Stakeholders notified
- [ ] Users notified and trained
- [ ] System announced as live
- [ ] Monitoring team on standby

#### Post-Launch (First 24 Hours)
- [ ] Monitor dashboards hourly
- [ ] Check for errors in logs
- [ ] Verify processing success rate
- [ ] Check cost metrics
- [ ] Gather user feedback
- [ ] Document any issues and resolutions

#### Week 1 Hypercare
- [ ] Daily dashboard reviews completed
- [ ] User feedback collected
- [ ] Adjustments made as needed
- [ ] Lessons learned documented
- [ ] System stable and performing to SLA

### 📦 Deliverables Collected
- [ ] Production URLs:
  - Frontend: `___________________________`
  - API: `___________________________`
  - WebSocket: `___________________________`
- [ ] Production credentials secured
- [ ] Go-live date: `___________________________`
- [ ] Post-launch report completed

### 📝 Sign-Off
- **Completed By:** _________________
- **Date:** _________________
- **Issues Encountered:** _________________
- **System Status:** LIVE IN PRODUCTION ✓

---

## Final Project Sign-Off

### Overall Project Completion
- [ ] All 16 stages completed successfully
- [ ] All acceptance criteria met
- [ ] System deployed to production
- [ ] Users trained and using system
- [ ] Documentation complete
- [ ] Monitoring and alerting active
- [ ] Post-launch support plan in place

### Success Metrics Validation
- [ ] **Technical KPIs Met**:
  - [ ] Processing time P95 < 5 minutes: _________
  - [ ] Transcription accuracy > 90%: _________
  - [ ] API latency P95 < 500ms: _________
  - [ ] Availability 99.9%: _________
  - [ ] Error rate < 1%: _________
  - [ ] Cost per call < $1.00: _________

- [ ] **Business KPIs Tracking**:
  - [ ] User adoption tracking started
  - [ ] Time savings measurement in progress
  - [ ] User satisfaction survey scheduled

### Project Team Sign-Off
- **Project Manager:** _________________ Date: _________
- **Solution Architect:** _________________ Date: _________
- **Lead Developer:** _________________ Date: _________
- **DevOps Engineer:** _________________ Date: _________
- **QA Lead:** _________________ Date: _________
- **Product Owner:** _________________ Date: _________

---

*Document Version: 1.0*  
*Last Updated: January 31, 2026*  
*Project Status: [IN PROGRESS / COMPLETED]*
