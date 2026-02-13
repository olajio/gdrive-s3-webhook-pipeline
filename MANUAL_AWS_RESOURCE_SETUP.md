# Manual AWS Resource Setup (Step-by-Step, AWS Console)

This document is a **click-by-click** guide to manually create the same AWS resources that this repo provisions with Terraform (see [terraform](terraform)).

If you follow these steps exactly, you’ll end up with:
- S3 bucket(s) for audio/transcripts/summaries
- DynamoDB tables (3)
- Secrets Manager secrets (Google service account JSON + webhook token)
- IAM roles/policies (Lambda + Step Functions + optional API Gateway logging role)
- Lambda layer + Lambda functions (11) 
- Step Functions state machine
- API Gateway (HTTP API + WebSocket API)
- Cognito User Pool + Domain + App Client + Groups
- Monitoring: CloudWatch log groups, dashboard, alarms + SNS topic

The goal is to **not assume you already know AWS Console workflows**.

---

## 0) Before You Start

### 0.1 Sign in + pick your region
1. Sign in to the AWS Console.
2. In the top-right region selector, choose your region (default in Terraform: `us-east-1`).
3. Keep the same region for every service in this guide.

### 0.2 Permissions you need
You need permissions to create IAM roles/policies, Lambda, API Gateway, Step Functions, Cognito, S3, DynamoDB, CloudWatch, SNS, Secrets Manager.

If you don’t have admin access, make sure your IAM user/role has the deployer policy described in [SETUP_GUIDE.md](SETUP_GUIDE.md).

### 0.3 Fill in your “values worksheet” (don’t skip)
Pick values once, then reuse them everywhere:

- `aws_region`: `us-east-1`
- `environment`: `dev` (or `staging`, `prod`)
- `project_name`: `customer-care-call-processor`
- `s3_bucket_name`: (must be globally unique, example: `customer-care-call-processor-dev-<yourname>-<random>`)
- `google_credentials_secret_name`: default in Terraform: `google-drive-credentials`
- `webhook_token_secret_name`: recommended: `customer-care-call-processor-webhook-config`
- `cognito_domain_prefix`: default in Terraform: `call-processor`
- `gdrive_folder_id`: your Google Drive folder ID

### 0.4 Recommended creation order (reduces backtracking)
1. S3
2. DynamoDB
3. Secrets Manager
4. IAM roles/policies
5. Cognito
6. API Gateway (HTTP + WebSocket)
7. Lambda layer + Lambdas (some env vars reference APIs and Step Functions; you’ll set placeholders and come back)
8. Step Functions
9. Monitoring (SNS, alarms, dashboards)

### 0.5 One AWS “gotcha”: Amazon Bedrock model access
If you plan to use the Bedrock summarization Lambda, you must enable model access:
1. Open **Amazon Bedrock** in the Console.
2. Go to **Model access**.
3. Request/enable access to the model family you will call (Terraform defaults to Claude: `anthropic.claude-3-5-sonnet-*`).

---

## 1) Create S3 Buckets
Source: [terraform/s3.tf](terraform/s3.tf)

### 1.1 Create the primary bucket
1. Go to **S3** → **Buckets** → **Create bucket**.
2. **Bucket name**: your `s3_bucket_name`.
3. **AWS Region**: same as your worksheet.
4. **Object Ownership**: keep default (recommended).
5. **Block Public Access settings**: leave **Block all public access = ON**.
6. **Bucket Versioning**:
   - `prod`: **Enable**
   - non-prod: **Suspend** (or leave disabled)
7. **Default encryption**:
   - **Server-side encryption**: enable
   - **Encryption type**: `SSE-S3`
8. Click **Create bucket**.

### 1.2 Configure CORS (dev only)
1. Open the bucket → **Permissions** tab.
2. Scroll to **Cross-origin resource sharing (CORS)** → **Edit**.
3. Paste the CORS configuration:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["http://localhost:3000", "http://localhost:5173"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```
4. Click **Save changes**.

### 1.3 Configure lifecycle rules
1. Open the bucket → **Management** tab.
2. Under **Lifecycle rules**, click **Create lifecycle rule**.

Rule A: raw audio archival
1. **Lifecycle rule name**: `archive-raw-audio`.
2. **Filter**: choose **Prefix** and set `raw-audio/`.
3. **Lifecycle rule actions**:
   - **Move current versions of objects between storage classes**:
     - Transition after `90` days → `Glacier Instant Retrieval`
     - Transition after `365` days → `Glacier Deep Archive`
   - **Expire current versions of objects** after `2555` days.
4. Save.

Rule B: transcripts archival
1. Create another rule named `archive-transcripts`.
2. Prefix: `transcripts/`.
3. Transition after `180` days → `Glacier Instant Retrieval`.
4. Expire after `2555` days.

Rule C: abort incomplete multipart uploads
1. Create another rule named `cleanup-incomplete-uploads`.
2. No filter needed.
3. Enable **Abort incomplete multipart uploads** after `7` days.

### 1.4 (Prod only) Create a logs bucket and enable access logging
Terraform creates a logs bucket only for `prod`.

1. Create another bucket named `${s3_bucket_name}-logs`.
2. Keep **Block Public Access = ON**.
3. Add a lifecycle rule to expire logs after `90` days.
4. Go back to your primary bucket → **Properties**.
5. Find **Server access logging** → **Edit** → **Enable**.
6. Target bucket: `${s3_bucket_name}-logs`.
7. Prefix: `s3-access-logs/`.
8. Save.

---

## 2) Create DynamoDB Tables (3)
Source: [terraform/dynamodb.tf](terraform/dynamodb.tf)

General DynamoDB notes:
- Billing mode in Terraform defaults to `PAY_PER_REQUEST`.
- Server-side encryption is enabled.
- TTL is enabled for the connections/channels tables.

### 2.1 Call summaries table
1. Go to **DynamoDB** → **Tables** → **Create table**.
2. **Table name**: `${project_name}-summaries-${environment}`.
3. **Partition key**: `call_id` (Type: **String**).
4. **Table settings**: choose **Customize settings**.
5. **Billing mode**: **On-demand (PAY_PER_REQUEST)**.
6. **Encryption at rest**: keep enabled.
7. Click **Create table**.

Add attributes + GSIs
1. Open the table → **Indexes** tab → **Create index**.
2. Create GSI: `status-index`
   - Partition key: `status` (String)
   - Sort key: `created_at` (String)
   - Projection: **All**
3. Create GSI: `user-index`
   - Partition key: `assigned_user_id` (String)
   - Sort key: `created_at` (String)
   - Projection: **All**

Point-in-time recovery (prod only)
1. Open the table → **Backups** tab.
2. Under **Point-in-time recovery**, click **Edit**.
3. Enable for `prod`.

### 2.2 WebSocket connections table
1. DynamoDB → Tables → **Create table**.
2. **Table name**: `${project_name}-connections-${environment}`.
3. Partition key: `connection_id` (String).
4. Customize settings → On-demand billing.
5. Create.

Create GSI: `user-index`
1. Table → **Indexes** → **Create index**.
2. Partition key: `user_id` (String)
3. Projection: All

Enable TTL
1. Table → **Additional settings** (or **Table details**) → find **Time to Live (TTL)**.
2. Click **Enable TTL**.
3. TTL attribute name: `ttl`.

### 2.3 Webhook channels table
1. DynamoDB → Tables → **Create table**.
2. **Table name**: `${project_name}-channels-${environment}`.
3. Partition key: `channel_id` (String).
4. Customize settings → On-demand billing.
5. Create.

Create GSI: `folder-index`
1. Table → **Indexes** → **Create index**.
2. Partition key: `folder_id` (String)
3. Projection: All

Enable TTL
1. Enable TTL using attribute name `ttl`.

---

## 3) Create Secrets in AWS Secrets Manager

Terraform expects a Google credentials secret name (default `google-drive-credentials`) and the system also needs a webhook token.

### 3.1 Store Google service account JSON
1. Go to **Secrets Manager** → **Secrets** → **Store a new secret**.
2. **Secret type**: choose **Other type of secret**.
3. Under **Key/value pairs**, switch to **Plaintext**.
4. Paste the full JSON for your Google service account key.
5. Click **Next**.
6. **Secret name**: your `google_credentials_secret_name`.
7. Click **Next** through the remaining steps (rotation can be **Disabled** for dev).
8. Click **Store**.

### 3.2 Generate + store a webhook token
The webhook handler validates requests using `WEBHOOK_TOKEN` (environment variable). This guide recommends storing it in Secrets Manager too, then copying it into the Lambda env var.

1. Generate a token on your machine:
   - `openssl rand -hex 32`
2. Secrets Manager → **Store a new secret** → **Other type of secret** → **Plaintext**.
3. Store JSON like:
```json
{ "webhook_token": "<paste-token-here>" }
```
4. **Secret name**: your `webhook_token_secret_name` (recommended: `customer-care-call-processor-webhook-config`).
5. Store.

---

## 4) Create IAM Roles and Policies
Sources: [terraform/iam.tf](terraform/iam.tf), [terraform/step_functions.tf](terraform/step_functions.tf)

AWS Console path: **IAM** → **Roles**.

### 4.1 Lambda execution role
Goal: a role that every Lambda function uses.

1. IAM → Roles → **Create role**.
2. **Trusted entity type**: AWS service.
3. **Use case**: **Lambda**.
4. Click **Next**.
5. Attach managed permissions:
   - `AWSLambdaBasicExecutionRole`
   - `AWSXRayDaemonWriteAccess`
6. Click **Next**.
7. **Role name**: `${project_name}-lambda-role-${environment}`.
8. Create role.

Add the inline policy
1. Open the new role.
2. Go to **Permissions** tab → **Add permissions** → **Create inline policy**.
3. Choose **JSON**.
4. Paste and edit this policy. You must replace placeholders like `<S3_BUCKET_ARN>` with real values.
   - Tip: open each resource in the Console and copy its ARN.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:HeadObject", "s3:DeleteObject"],
      "Resource": "<S3_BUCKET_ARN>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "<S3_BUCKET_ARN>"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"],
      "Resource": [
        "<DDB_SUMMARIES_TABLE_ARN>",
        "<DDB_SUMMARIES_TABLE_ARN>/index/*",
        "<DDB_CONNECTIONS_TABLE_ARN>",
        "<DDB_CONNECTIONS_TABLE_ARN>/index/*",
        "<DDB_CHANNELS_TABLE_ARN>",
        "<DDB_CHANNELS_TABLE_ARN>/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": ["arn:aws:secretsmanager:<REGION>:<ACCOUNT_ID>:secret:<GOOGLE_SECRET_NAME>*"]
    },
    {
      "Effect": "Allow",
      "Action": ["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob", "transcribe:ListTranscriptionJobs"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": ["arn:aws:bedrock:<REGION>::foundation-model/anthropic.claude-*"]
    },
    {
      "Effect": "Allow",
      "Action": ["states:StartExecution"],
      "Resource": "<STATE_MACHINE_ARN>"
    },
    {
      "Effect": "Allow",
      "Action": ["execute-api:ManageConnections"],
      "Resource": "<WEBSOCKET_API_EXECUTION_ARN>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "<SNS_TOPIC_ARN>"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:PutMetricData"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": "arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<PROJECT_NAME>-*"
    }
  ]
}
```

5. Click **Next**.
6. **Policy name**: `${project_name}-lambda-policy-${environment}`.
7. Click **Create policy**.

### 4.2 Step Functions role
1. IAM → Roles → **Create role**.
2. AWS service → **Step Functions**.
3. Role name: `${project_name}-sfn-role-${environment}`.
4. Create.
5. Add an inline policy named `${project_name}-sfn-policy-${environment}` that allows:
   - `lambda:InvokeFunction` on the pipeline Lambdas
   - `transcribe:GetTranscriptionJob`
   - Step Functions logging delivery actions
   - X-Ray actions

Tip: you can copy the JSON shape from [terraform/step_functions.tf](terraform/step_functions.tf) and replace ARNs.

### 4.3 (Optional) API Gateway CloudWatch logging role
Terraform optionally creates a role for API Gateway logging.

1. IAM → Roles → Create role → AWS service → **API Gateway**.
2. Role name: `${project_name}-apigw-cloudwatch-${environment}`.
3. Attach managed policy `AmazonAPIGatewayPushToCloudWatchLogs`.

Enable it in API Gateway:
1. API Gateway → **Settings**.
2. Find **CloudWatch log role ARN**.
3. Paste the role ARN.
4. Save.

---

## 5) Create the Lambda Layer + Lambda Functions
Source: [terraform/lambda.tf](terraform/lambda.tf)

### 5.0 Packaging note (important)
Terraform zips the source under [src/lambda](src/lambda) and publishes it as a layer.

For a working Python dependency layer (recommended), you usually need the Lambda layer structure:
`python/` (contains site-packages).

This guide gives you two options:
- Option A (mirror Terraform): zip [src/lambda](src/lambda) as-is.
- Option B (recommended for real deployments): build a dependency layer with `pip`.

### 5.1 (Recommended) Build a dependency layer zip locally
From repo root:
1. Create a layer folder:
   - `mkdir -p build/layer/python`
2. Install required libs into it (example set for the webhook handler):
   - `pip install -t build/layer/python google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib`
3. Zip it:
   - `cd build/layer && zip -r ../../dependencies_layer.zip .`

### 5.2 Create the Lambda layer in AWS Console
1. Go to **Lambda** → **Layers** → **Create layer**.
2. Name: `${project_name}-dependencies-${environment}`.
3. Upload: choose your `dependencies_layer.zip` (recommended) OR a zip of [src/lambda](src/lambda) (mirror Terraform).
4. Compatible runtimes: select **Python 3.11**.
5. Create.

### 5.3 Create Lambda functions (11)
All functions:
- Runtime: **Python 3.11**
- Execution role: `${project_name}-lambda-role-${environment}`
- Tracing: **Active** (X-Ray)

Create each function:
1. Lambda → **Functions** → **Create function**.
2. Choose **Author from scratch**.
3. Name: (use the names below)
4. Runtime: **Python 3.11**
5. Permissions: choose **Use an existing role** → select `${project_name}-lambda-role-${environment}`.
6. Create function.
7. In the function page:
   - **Code**: upload the correct `.zip` for that function
   - **Runtime settings**: set the handler
   - **Configuration → General configuration**: set memory + timeout
   - **Configuration → Environment variables**: set variables
   - **Layers**: add `${project_name}-dependencies-${environment}`
   - **Configuration → Monitoring and operations tools**: enable **Active tracing**

Zip packaging quick reference (from repo root):
- Webhook handler (folder):
  - `cd src/lambda/webhook && zip -r ../../../webhook_handler.zip .`
- Single-file lambdas (zip file at root of zip):
  - `zip -j start_transcribe.zip src/lambda/processing/start_transcribe.py`
  - `zip -j process_transcript.zip src/lambda/processing/process_transcript.py`
  - `zip -j generate_summary.zip src/lambda/processing/generate_summary.py`
  - `zip -j save_summary.zip src/lambda/processing/save_summary.py`
  - `zip -j update_status.zip src/lambda/processing/update_status.py`
  - `zip -j list_summaries.zip src/lambda/api/list_summaries.py`
  - `zip -j get_summary.zip src/lambda/api/get_summary.py`
  - `zip -j ws_connect.zip src/lambda/websocket/connect.py`
  - `zip -j ws_disconnect.zip src/lambda/websocket/disconnect.py`
  - `zip -j ws_notify.zip src/lambda/websocket/notify.py`

Functions (match Terraform names/handlers):

1) Webhook handler
- Name: `${project_name}-webhook-handler-${environment}`
- Handler: `handler.handler`
- Timeout: `60` (Terraform variable: `webhook_handler_timeout`)
- Memory: `512` (Terraform variable: `webhook_handler_memory`)
- Env vars:
  - `S3_BUCKET` = your S3 bucket name
  - `DYNAMODB_TABLE` = `${project_name}-summaries-${environment}`
  - `STEP_FUNCTION_ARN` = (placeholder for now; fill after Step Functions)
  - `GOOGLE_CREDENTIALS_SECRET` = `google_credentials_secret_name`
  - `GDRIVE_FOLDER_ID` = your folder id
  - `WEBHOOK_TOKEN` = the token you generated
  - `ENVIRONMENT` = `environment`

2) Start Transcribe
- Name: `${project_name}-start-transcribe-${environment}`
- Handler: `start_transcribe.handler`
- Timeout: 60, Memory: 256
- Env vars: `TRANSCRIBE_OUTPUT_BUCKET`, `DYNAMODB_TABLE`, `ENVIRONMENT`

3) Process Transcript
- Name: `${project_name}-process-transcript-${environment}`
- Handler: `process_transcript.handler`
- Timeout: 300, Memory: 512
- Env vars: `S3_BUCKET`, `DYNAMODB_TABLE`, `ENVIRONMENT`

4) Generate Summary (Bedrock)
- Name: `${project_name}-generate-summary-${environment}`
- Handler: `generate_summary.handler`
- Timeout: 600, Memory: 1024
- Env vars: `BEDROCK_MODEL_ID`, `MAX_TOKENS`, `DYNAMODB_TABLE`, `ENVIRONMENT`

5) Save Summary
- Name: `${project_name}-save-summary-${environment}`
- Handler: `save_summary.handler`
- Timeout: 60, Memory: 256
- Env vars: `DYNAMODB_TABLE`, `ENVIRONMENT`

6) Update Status
- Name: `${project_name}-update-status-${environment}`
- Handler: `update_status.handler`
- Timeout: 30, Memory: 128
- Env vars: `DYNAMODB_TABLE`, `ENVIRONMENT`

7) List Summaries
- Name: `${project_name}-list-summaries-${environment}`
- Handler: `list_summaries.handler`
- Timeout: 30, Memory: 256
- Env vars: `DYNAMODB_TABLE`, `ENVIRONMENT`

8) Get Summary
- Name: `${project_name}-get-summary-${environment}`
- Handler: `get_summary.handler`
- Timeout: 30, Memory: 256
- Env vars: `DYNAMODB_TABLE`, `S3_BUCKET`, `ENVIRONMENT`

9) WebSocket connect
- Name: `${project_name}-ws-connect-${environment}`
- Handler: `connect.handler`
- Timeout: 10, Memory: 128
- Env vars: `CONNECTIONS_TABLE`, `ENVIRONMENT`

10) WebSocket disconnect
- Name: `${project_name}-ws-disconnect-${environment}`
- Handler: `disconnect.handler`
- Timeout: 10, Memory: 128
- Env vars: `CONNECTIONS_TABLE`, `ENVIRONMENT`

11) WebSocket notify
- Name: `${project_name}-ws-notify-${environment}`
- Handler: `notify.handler`
- Timeout: 30, Memory: 256
- Env vars: `CONNECTIONS_TABLE`, `WEBSOCKET_ENDPOINT`, `ENVIRONMENT`
  - Set `WEBSOCKET_ENDPOINT` after you create the WebSocket API stage (it looks like `wss://.../dev`).

---

## 6) Create the Step Functions State Machine
Source: [terraform/step_functions.tf](terraform/step_functions.tf)

### 6.1 Create the Step Functions log group
1. Go to **CloudWatch** → **Logs** → **Log groups** → **Create log group**.
2. Name: `/aws/step-functions/${project_name}-pipeline-${environment}`.
3. Retention: `log_retention_days` (Terraform default: 30).
4. Create.

### 6.2 Create the state machine
1. Go to **Step Functions** → **State machines** → **Create state machine**.
2. Type: **Standard**.
3. Definition: open [stepfunctions/call-processing.asl.json](stepfunctions/call-processing.asl.json).
4. Replace the template variables with real Lambda ARNs:
   - `UpdateStatusFunctionArn`
   - `StartTranscribeFunctionArn`
   - `ProcessTranscriptFunctionArn`
   - `GenerateSummaryFunctionArn`
   - `SaveSummaryFunctionArn`
   - `NotifyFunctionArn`
5. Paste the final JSON into the definition editor.
6. Name: `${project_name}-pipeline-${environment}`.
7. Permissions: choose **Use an existing role** → `${project_name}-sfn-role-${environment}`.
8. Logging:
   - Destination: the log group you created
   - Level: **ALL**
   - Include execution data: **Enabled**
9. Tracing: enable **X-Ray tracing**.
10. Create.

### 6.3 Update Lambda environment variables that depend on Step Functions
Go back to the webhook handler Lambda and set:
- `STEP_FUNCTION_ARN` = your state machine ARN

### 6.4 (Optional) Create an EventBridge rule for Transcribe completion
Terraform defines a rule but does not attach a target. If you want this to actually trigger Step Functions, you must add a target.

1. Go to **EventBridge** → **Rules** → **Create rule**.
2. Name: `${project_name}-transcribe-complete-${environment}`.
3. Event pattern:
   - Source: `aws.transcribe`
   - Detail type: `Transcribe Job State Change`
   - Status: `COMPLETED` and `FAILED`
4. Target: **Step Functions state machine** → pick `${project_name}-pipeline-${environment}`.
5. Allow EventBridge to invoke Step Functions (it will guide you to create a role).
6. Create.

---

## 7) Create Cognito (User Pool + Domain + Client + Groups)
Source: [terraform/cognito.tf](terraform/cognito.tf)

### 7.1 Create the user pool
1. Go to **Amazon Cognito** → **User pools** → **Create user pool**.
2. **Sign-in options**:
   - Choose **Email** as the sign-in attribute.
3. **Security requirements**:
   - Password policy: minimum length 12; require upper/lower/number/symbol.
   - MFA: `prod` = ON, otherwise OPTIONAL.
4. **Sign-up experience**:
   - Allow users to self sign-up.
   - Auto-verify: email.
5. **Message delivery**:
   - Email provider: Cognito default.
   - Verification subject: `Your verification code`
   - Verification message: `Your verification code is {####}`
6. **Attributes**:
   - Required: `email`, `name`
   - Optional: `department`
7. Name: `${project_name}-users-${environment}`.
8. Create.

### 7.2 Create a user pool domain
1. In your user pool → **App integration**.
2. Find **Domain** → **Create domain**.
3. Prefix: `${cognito_domain_prefix}-${environment}`.
4. Create.

### 7.3 Create the app client
1. In user pool → **App integration** → **App clients** → **Create app client**.
2. Name: `${project_name}-frontend-${environment}`.
3. Client secret: **do not generate** (SPA).
4. OAuth:
   - Allowed flows: Authorization code grant
   - Scopes: `openid`, `email`, `profile`
5. Callback URLs (dev):
   - `http://localhost:3000/callback`
   - `http://localhost:5173/callback`
6. Sign out URLs (dev):
   - `http://localhost:3000`
   - `http://localhost:5173`
7. Token validity: access 1h, id 1h, refresh 30d.
8. Create.

### 7.4 Create groups
1. User pool → **Groups** → **Create group**.
2. Create:
   - `caseworkers` (precedence 3)
   - `supervisors` (precedence 2)
   - `admin` (precedence 1)

---

## 8) Create API Gateway (HTTP API + WebSocket)
Source: [terraform/api_gateway.tf](terraform/api_gateway.tf)

### 8.1 HTTP API (for /webhook and summaries)
1. Go to **API Gateway** → **Create API**.
2. Choose **HTTP API** → **Build**.
3. API name: `${project_name}-api-${environment}`.
4. Configure CORS:
   - Allow origins: `http://localhost:3000`, `http://localhost:5173` (dev)
   - Allow methods: GET, POST, PUT, DELETE, OPTIONS
   - Allow headers: Content-Type, Authorization, X-Amz-Date, X-Api-Key
5. Create.

Create integrations + routes
1. In the API, go to **Routes** → **Create**.
2. Create route `POST /webhook`.
3. Attach integration to the webhook handler Lambda.
4. Create route `GET /summaries` → integration: list_summaries Lambda.
5. Create route `GET /summaries/{call_id}` → integration: get_summary Lambda.

Create JWT authorizer (Cognito)
1. Go to **Authorizers** → **Create and attach authorizer**.
2. Type: JWT.
3. Issuer URL:
   - `https://cognito-idp.<region>.amazonaws.com/<user_pool_id>`
4. Audience:
   - your Cognito app client ID.
5. Attach the authorizer to the `GET /summaries` and `GET /summaries/{call_id}` routes.

Stage + logging
1. Go to **Stages** → create stage named `${environment}`.
2. Enable auto-deploy.
3. Access logs: create/use log group `/aws/apigateway/${project_name}-${environment}` and enable logging.
4. Throttling: burst 100, rate 50.

### 8.2 WebSocket API (for real-time notifications)
1. API Gateway → **Create API**.
2. Choose **WebSocket API**.
3. API name: `${project_name}-websocket-${environment}`.
4. Route selection expression: `$request.body.action`.
5. Create.

Create routes
1. Routes → create `$connect` → integrate with `ws-connect` Lambda.
2. Routes → create `$disconnect` → integrate with `ws-disconnect` Lambda.

Create stage
1. Stages → create stage `${environment}`.
2. Auto-deploy ON.
3. Throttling: burst 500, rate 100.
4. Copy the stage invoke URL (wss://...).
5. Update the `ws-notify` Lambda env var `WEBSOCKET_ENDPOINT` to this URL.

---

## 9) Monitoring (CloudWatch + SNS)
Source: [terraform/cloudwatch.tf](terraform/cloudwatch.tf)

### 9.1 Create the SNS topic (alerts)
1. Go to **SNS** → **Topics** → **Create topic**.
2. Type: Standard.
3. Name: `${project_name}-alerts-${environment}`.
4. Create.

Add email subscription (optional)
1. Open the topic → **Create subscription**.
2. Protocol: Email.
3. Endpoint: your email.
4. Create.
5. Confirm the subscription from your email.

### 9.2 Set CloudWatch log retention
Log groups are created automatically when services write logs, but retention defaults to “Never expire”. Set it to 30 days (or your preferred value):
1. CloudWatch → Logs → Log groups.
2. For each log group for this project, choose **Actions** → **Edit retention setting**.
3. Set to `30 days`.

### 9.3 Create a CloudWatch dashboard (optional)
Terraform creates a dashboard. Manually, you can start simple:
1. CloudWatch → **Dashboards** → **Create dashboard**.
2. Name: `${project_name}-${environment}`.
3. Add widgets:
   - Lambda: Invocations / Errors / Duration
   - Step Functions: ExecutionsStarted / ExecutionsFailed
   - DynamoDB: SuccessfulRequestLatency / ThrottledRequests

### 9.4 Create basic alarms (recommended)
1. CloudWatch → **Alarms** → **Create alarm**.
2. Lambda Errors alarm:
   - Select metric: AWS/Lambda → By Function Name → pick a function → Errors
   - Threshold: `>= 1` over 1 datapoint (5 minutes)
   - Notification: send to your SNS topic
3. Step Functions failures alarm:
   - AWS/States → By State Machine ARN → ExecutionsFailed
   - Threshold: `>= 1`

---

## 10) Post-Setup Checklist (to make the system actually work)

1. Verify Bedrock model access is enabled (Section 0.5).
2. Confirm the Google credentials secret exists (Section 3.1).
3. Confirm webhook handler env vars are set:
   - `STEP_FUNCTION_ARN` points to your state machine
   - `WEBHOOK_TOKEN` is set
4. Register the Google Drive webhook (script-driven step):
   - See [scripts/register_webhook.py](scripts/register_webhook.py)
   - You’ll need the webhook URL: `https://<http-api-id>.execute-api.<region>.amazonaws.com/<env>/webhook`
5. Configure frontend env vars (see Terraform output format in [terraform/outputs.tf](terraform/outputs.tf)).

---

## 11) Cleanup (Cost-Saving Teardown)

> Warning: This deletes data. Export anything needed first.

Recommended order (Console):
1. **API Gateway**
   - Delete HTTP API and WebSocket API (deletes routes/integrations/stages)
2. **Step Functions**
   - Delete the state machine
   - Delete the Step Functions log group
   - Delete EventBridge rule/targets (if you created them)
3. **Lambda**
   - Delete all functions
   - Delete the layer
4. **Cognito**
   - Delete app client
   - Delete domain
   - Delete groups
   - Delete user pool
5. **DynamoDB**
   - Delete all 3 tables
6. **S3**
   - Empty the bucket(s) first: bucket → **Empty** → type `permanently delete`
   - Delete primary bucket
   - Delete logs bucket (prod only)
7. **CloudWatch**
   - Delete dashboard(s)
   - Delete alarms if created manually
8. **SNS**
   - Delete topic(s) and subscriptions
9. **IAM**
   - Delete inline policies and roles created for Lambda/Step Functions/API Gateway logging

---

## Reference: Terraform files
- [terraform/s3.tf](terraform/s3.tf)
- [terraform/dynamodb.tf](terraform/dynamodb.tf)
- [terraform/iam.tf](terraform/iam.tf)
- [terraform/lambda.tf](terraform/lambda.tf)
- [terraform/step_functions.tf](terraform/step_functions.tf)
- [terraform/api_gateway.tf](terraform/api_gateway.tf)
- [terraform/cognito.tf](terraform/cognito.tf)
- [terraform/cloudwatch.tf](terraform/cloudwatch.tf)
