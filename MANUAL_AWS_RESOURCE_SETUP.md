# Manual AWS Resource Creation Guide (Matches Terraform)

This document mirrors the infrastructure defined in Terraform (see [terraform](terraform)) and explains how to create the same resources manually in the AWS Console. It is intended for learning and validation before automation.

Scope (matches Section 4 resources):
- S3 bucket (with encryption, public access block, CORS, lifecycle, optional access logs)
- DynamoDB tables (3)
- Lambda functions (10) + layer
- Step Functions state machine
- API Gateway (HTTP API + WebSocket)
- Cognito User Pool + Client + Groups + Domain
- IAM roles and policies (Lambda execution, Step Functions, API Gateway logs)

Supporting resources also created by Terraform:
- CloudWatch log groups (Lambda + API Gateway + Step Functions)
- CloudWatch dashboard
- SNS topic + optional email subscription

> Tip: Use a consistent naming convention matching Terraform variables:
> - Project name: customer-care-call-processor
> - Environment: dev (or staging/prod)
> - Region: us-east-1

---

## 1) IAM Roles and Policies

### 1.1 Lambda Execution Role
Source: [terraform/iam.tf](terraform/iam.tf)

Create an IAM role named:
- customer-care-call-processor-lambda-role-<env>

Trusted entity: **Lambda** (`lambda.amazonaws.com`).

Attach AWS managed policies:
- AWSLambdaBasicExecutionRole
- AWSXRayDaemonWriteAccess

Add inline policy named:
- customer-care-call-processor-lambda-policy-<env>

Policy actions (from Terraform):
- S3: PutObject, GetObject, HeadObject, DeleteObject, ListBucket
- DynamoDB: GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan
- Secrets Manager: GetSecretValue
- Transcribe: StartTranscriptionJob, GetTranscriptionJob, ListTranscriptionJobs
- Bedrock: InvokeModel, InvokeModelWithResponseStream
- Step Functions: StartExecution
- API Gateway (WebSocket): execute-api:ManageConnections
- SNS: Publish
- CloudWatch: PutMetricData
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents

Use resource scoping consistent with your environment (same as Terraform).

### 1.2 Step Functions Role
Source: [terraform/step_functions.tf](terraform/step_functions.tf)

Create role:
- customer-care-call-processor-sfn-role-<env>

Trusted entity: **Step Functions** (`states.amazonaws.com`).

Inline policy must allow:
- lambda:InvokeFunction on the 6 pipeline Lambdas
- transcribe:GetTranscriptionJob
- logs:* log delivery actions for Step Functions logging
- xray:PutTraceSegments, PutTelemetryRecords, GetSamplingRules, GetSamplingTargets

### 1.3 API Gateway CloudWatch Role (Optional)
Source: [terraform/iam.tf](terraform/iam.tf)

Create role:
- customer-care-call-processor-apigw-cloudwatch-<env>

Trusted entity: **API Gateway** (`apigateway.amazonaws.com`).

Attach managed policy:
- AmazonAPIGatewayPushToCloudWatchLogs

---

## 2) S3 Storage
Source: [terraform/s3.tf](terraform/s3.tf)

Create primary bucket:
- <s3_bucket_name> (from terraform.tfvars)

Settings:
- Block all public access: **ON**
- Server-side encryption: **SSE-S3 (AES256)**
- Versioning: Enabled in prod; Suspended otherwise
- CORS (dev): allow origins http://localhost:3000 and http://localhost:5173; methods GET/HEAD; headers *; expose ETag; max age 3600
- Lifecycle rules:
  - raw-audio/: transition to Glacier IR at 90 days; Deep Archive at 365 days; expire at 2555 days
  - transcripts/: transition to Glacier IR at 180 days; expire at 2555 days
  - abort incomplete multipart uploads after 7 days

If environment is prod:
- Create logs bucket: <s3_bucket_name>-logs
- Block public access
- Add lifecycle to expire logs after 90 days
- Enable server access logging on primary bucket targeting logs bucket, prefix s3-access-logs/

---

## 3) DynamoDB Tables (3)
Source: [terraform/dynamodb.tf](terraform/dynamodb.tf)

### 3.1 Call Summaries Table
Name: customer-care-call-processor-summaries-<env>
- Partition key: call_id (String)
- GSI: status-index (hash: status, range: created_at)
- GSI: user-index (hash: assigned_user_id, range: created_at)
- SSE: enabled
- Point-in-time recovery: enabled in prod, disabled otherwise

### 3.2 WebSocket Connections Table
Name: customer-care-call-processor-connections-<env>
- Partition key: connection_id (String)
- GSI: user-index (hash: user_id)
- TTL attribute: ttl (enabled)
- SSE: enabled

### 3.3 Webhook Channels Table
Name: customer-care-call-processor-channels-<env>
- Partition key: channel_id (String)
- GSI: folder-index (hash: folder_id)
- TTL attribute: ttl (enabled)
- SSE: enabled

---

## 4) Lambda Functions (10) + Layer
Source: [terraform/lambda.tf](terraform/lambda.tf)

### 4.1 Lambda Layer
Name: customer-care-call-processor-dependencies-<env>
- Runtime: python3.11
- Content: zip of [src/lambda](src/lambda)

### 4.2 Functions and Settings
All functions use runtime python3.11 and the Lambda execution role. Enable X-Ray tracing (Active). Create CloudWatch log groups with retention set to log_retention_days (default 30).

**Webhook Handler**
- Name: customer-care-call-processor-webhook-handler-<env>
- Handler: handler.handler
- Timeout: webhook_handler_timeout (default 60)
- Memory: webhook_handler_memory (default 512)
- Layer: dependencies layer
- Env vars: S3_BUCKET, DYNAMODB_TABLE, STEP_FUNCTION_ARN, GOOGLE_CREDENTIALS_SECRET, GDRIVE_FOLDER_ID, ENVIRONMENT

**Start Transcribe**
- Name: customer-care-call-processor-start-transcribe-<env>
- Handler: start_transcribe.handler
- Timeout: 60
- Memory: 256
- Env vars: TRANSCRIBE_OUTPUT_BUCKET, DYNAMODB_TABLE, ENVIRONMENT

**Process Transcript**
- Name: customer-care-call-processor-process-transcript-<env>
- Handler: process_transcript.handler
- Timeout: processing_lambda_timeout (default 300)
- Memory: processing_lambda_memory (default 512)
- Env vars: S3_BUCKET, DYNAMODB_TABLE, ENVIRONMENT

**Generate Summary (Bedrock)**
- Name: customer-care-call-processor-generate-summary-<env>
- Handler: generate_summary.handler
- Timeout: bedrock_lambda_timeout (default 600)
- Memory: bedrock_lambda_memory (default 1024)
- Env vars: BEDROCK_MODEL_ID, MAX_TOKENS, DYNAMODB_TABLE, ENVIRONMENT

**Save Summary**
- Name: customer-care-call-processor-save-summary-<env>
- Handler: save_summary.handler
- Timeout: 60
- Memory: 256
- Env vars: DYNAMODB_TABLE, ENVIRONMENT

**Update Status**
- Name: customer-care-call-processor-update-status-<env>
- Handler: update_status.handler
- Timeout: 30
- Memory: 128
- Env vars: DYNAMODB_TABLE, ENVIRONMENT

**List Summaries**
- Name: customer-care-call-processor-list-summaries-<env>
- Handler: list_summaries.handler
- Timeout: 30
- Memory: 256
- Env vars: DYNAMODB_TABLE, ENVIRONMENT

**Get Summary**
- Name: customer-care-call-processor-get-summary-<env>
- Handler: get_summary.handler
- Timeout: 30
- Memory: 256
- Env vars: DYNAMODB_TABLE, S3_BUCKET, ENVIRONMENT

**WebSocket Connect**
- Name: customer-care-call-processor-ws-connect-<env>
- Handler: connect.handler
- Timeout: 10
- Memory: 128
- Env vars: CONNECTIONS_TABLE, ENVIRONMENT

**WebSocket Disconnect**
- Name: customer-care-call-processor-ws-disconnect-<env>
- Handler: disconnect.handler
- Timeout: 10
- Memory: 128
- Env vars: CONNECTIONS_TABLE, ENVIRONMENT

**WebSocket Notify**
- Name: customer-care-call-processor-ws-notify-<env>
- Handler: notify.handler
- Timeout: 30
- Memory: 256
- Env vars: CONNECTIONS_TABLE, WEBSOCKET_ENDPOINT, ENVIRONMENT

---

## 5) Step Functions State Machine
Source: [terraform/step_functions.tf](terraform/step_functions.tf)

Create state machine:
- Name: customer-care-call-processor-pipeline-<env>
- Definition: [stepfunctions/call-processing.asl.json](stepfunctions/call-processing.asl.json) with Lambda ARNs substituted for:
  - UpdateStatusFunctionArn
  - StartTranscribeFunctionArn
  - ProcessTranscriptFunctionArn
  - GenerateSummaryFunctionArn
  - SaveSummaryFunctionArn
  - NotifyFunctionArn
- Logging: CloudWatch log group `/aws/step-functions/customer-care-call-processor-pipeline-<env>`; include execution data; level ALL
- X-Ray tracing: enabled

EventBridge rule (optional, per Terraform):
- Name: customer-care-call-processor-transcribe-complete-<env>
- Pattern: source aws.transcribe; detail-type Transcribe Job State Change; status COMPLETED/FAILED

---

## 6) API Gateway
Source: [terraform/api_gateway.tf](terraform/api_gateway.tf)

### 6.1 HTTP API (REST)
- Name: customer-care-call-processor-api-<env>
- Protocol: HTTP
- CORS (dev): allow origins http://localhost:3000 and http://localhost:5173; methods GET/POST/PUT/DELETE/OPTIONS; headers Content-Type, Authorization, X-Amz-Date, X-Api-Key

Integrations (AWS_PROXY):
- POST /webhook → webhook_handler Lambda (no auth)
- GET /summaries → list_summaries Lambda (JWT auth)
- GET /summaries/{call_id} → get_summary Lambda (JWT auth)

Authorizer:
- Cognito JWT authorizer
- Issuer: https://cognito-idp.<region>.amazonaws.com/<user_pool_id>
- Audience: Cognito user pool client ID

Stage:
- Name: <env>
- Auto-deploy: ON
- Access logs to `/aws/apigateway/customer-care-call-processor-<env>`
- Default throttling: burst 100, rate 50

### 6.2 WebSocket API
- Name: customer-care-call-processor-websocket-<env>
- Route selection expression: $request.body.action

Routes:
- $connect → websocket_connect Lambda
- $disconnect → websocket_disconnect Lambda

Stage:
- Name: <env>
- Auto-deploy: ON
- Default throttling: burst 500, rate 100

Add Lambda invoke permissions for API Gateway for:
- webhook_handler, list_summaries, get_summary
- websocket_connect, websocket_disconnect

---

## 7) Cognito User Pool
Source: [terraform/cognito.tf](terraform/cognito.tf)

Create user pool:
- Name: customer-care-call-processor-users-<env>
- Username: email
- Auto-verify email
- Password policy: min 12, upper/lower/number/symbol required
- MFA: OPTIONAL (ON in prod)
- Account recovery: email
- Email sending: COGNITO_DEFAULT
- Attributes: email (required), name (required), department (optional)
- Verification email: subject “Your verification code” / message “Your verification code is {####}”
- Admin create user: allow users to self-signup (allow_admin_create_user_only = false), with invite templates

Create user pool domain:
- <cognito_domain_prefix>-<env>

Create user pool client:
- Name: customer-care-call-processor-frontend-<env>
- Generate secret: false
- OAuth flows: code
- OAuth scopes: email, openid, profile
- Callback URLs (dev): http://localhost:3000/callback, http://localhost:5173/callback
- Logout URLs (dev): http://localhost:3000, http://localhost:5173
- Token validity: access 1h, id 1h, refresh 30d
- Explicit auth flows: ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH
- Prevent user existence errors: enabled

Create groups:
- caseworkers (precedence 3)
- supervisors (precedence 2)
- admin (precedence 1)

---

## 8) Monitoring and Alerts
Source: [terraform/cloudwatch.tf](terraform/cloudwatch.tf)

Create SNS topic:
- customer-care-call-processor-alerts-<env>
- Optional email subscription if alert_email is set

Create CloudWatch dashboard:
- Name: customer-care-call-processor-<env>
- Widgets for pipeline metrics, Lambda metrics, Step Functions metrics (as defined in Terraform)

Create log groups:
- Lambda log groups: /aws/lambda/<function-name>
- API Gateway logs: /aws/apigateway/customer-care-call-processor-<env>
- Step Functions logs: /aws/step-functions/customer-care-call-processor-pipeline-<env>
- Retention: log_retention_days (default 30)

---

## 9) Cleanup (Cost-Saving Teardown)

> Warning: This deletes data. Export anything needed first.

Recommended order:
1. **API Gateway**
   - Delete HTTP API and WebSocket API (removes routes, integrations, stages)
2. **Lambda**
   - Delete 10 Lambda functions and the dependency layer
3. **Step Functions**
   - Delete state machine and log group
   - Delete EventBridge rule (if created)
4. **Cognito**
   - Delete user pool client, domain, groups, then user pool
5. **DynamoDB**
   - Delete 3 tables (summaries, connections, channels)
6. **S3**
   - Empty and delete primary bucket and logs bucket (if prod)
7. **CloudWatch**
   - Delete dashboards and any leftover log groups
8. **SNS**
   - Delete alerts topic and subscriptions
9. **IAM**
   - Detach inline/managed policies and delete roles created for Lambda, Step Functions, and API Gateway logs

---

## 10) Reference Files
- [terraform/s3.tf](terraform/s3.tf)
- [terraform/dynamodb.tf](terraform/dynamodb.tf)
- [terraform/lambda.tf](terraform/lambda.tf)
- [terraform/step_functions.tf](terraform/step_functions.tf)
- [terraform/api_gateway.tf](terraform/api_gateway.tf)
- [terraform/cognito.tf](terraform/cognito.tf)
- [terraform/cloudwatch.tf](terraform/cloudwatch.tf)
- [terraform/iam.tf](terraform/iam.tf)
