# Build Process Steps
## Enterprise AWS Customer Care Call Processing System

---

## Table of Contents
1. [Pre-requisites and Environment Setup](#stage-0-pre-requisites-and-environment-setup)
2. [Google Cloud Platform Setup](#stage-1-google-cloud-platform-setup)
3. [AWS Account and Foundation Setup](#stage-2-aws-account-and-foundation-setup)
4. [AWS Storage Layer Setup](#stage-3-aws-storage-layer-setup)
5. [Google-AWS Communication Bridge](#stage-4-google-aws-communication-bridge)
6. [Data Ingestion Layer](#stage-5-data-ingestion-layer)
7. [AI Services Configuration](#stage-6-ai-services-configuration)
8. [Processing Orchestration Layer](#stage-7-processing-orchestration-layer)
9. [Backend API Layer](#stage-8-backend-api-layer)
10. [Authentication and Authorization](#stage-9-authentication-and-authorization)
11. [Real-Time Notification System](#stage-10-real-time-notification-system)
12. [Frontend Application](#stage-11-frontend-application)
13. [Monitoring and Observability](#stage-12-monitoring-and-observability)
14. [Security Hardening](#stage-13-security-hardening)
15. [Testing and Validation](#stage-14-testing-and-validation)
16. [Production Deployment](#stage-15-production-deployment)

---

## Stage 0: Pre-requisites and Environment Setup

### Duration: 1-2 days

### Objectives
- Set up development environment
- Install required tools and SDKs
- Configure version control
- Establish team access

### Steps

#### Step 0.1: Install Development Tools
**Tasks:**
1. Install Node.js (v18 or later) and npm
   ```bash
   # macOS
   brew install node@18
   ```

2. Install Python 3.11 or later
   ```bash
   # macOS
   brew install python@3.11
   ```

3. Install AWS CLI v2
   ```bash
   # macOS
   curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
   sudo installer -pkg AWSCLIV2.pkg -target /
   ```

4. Install AWS CDK
   ```bash
   npm install -g aws-cdk
   ```

5. Install Google Cloud SDK
   ```bash
   # macOS
   brew install --cask google-cloud-sdk
   
   # Linux (Debian/Ubuntu)
   echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
   sudo apt-get update && sudo apt-get install google-cloud-sdk
   
   # Linux (Quick Install Script)
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # Amazon Linux / RHEL
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
   
   **Initialize after installation:**
   ```bash
   gcloud init  # Authenticate and set default project
   ```

6. Install code editor (VS Code recommended)
   ```bash
   brew install --cask visual-studio-code
   ```

**Validation:**
```bash
node --version  # Should show v18+
python --version  # Should show 3.11+
aws --version  # Should show aws-cli/2.x
cdk --version  # Should show AWS CDK version
gcloud --version  # Should show Google Cloud SDK version
```

#### Step 0.2: Set Up Version Control
**Tasks:**
1. Create GitHub organization or use existing
2. Create repositories:
   - `customer-care-infrastructure` (AWS CDK code)
   - `customer-care-lambdas` (Lambda function code)
   - `customer-care-frontend` (React application)
   - `customer-care-docs` (Documentation)

3. Clone repositories locally
   ```bash
   git clone git@github.com:yourorg/customer-care-infrastructure.git
   git clone git@github.com:yourorg/customer-care-lambdas.git
   git clone git@github.com:yourorg/customer-care-frontend.git
   git clone git@github.com:yourorg/customer-care-docs.git
   ```

4. Set up branch protection rules:
   - Require pull request reviews
   - Require status checks to pass
   - Require branches to be up to date

**Validation:**
- All repositories accessible
- Can commit and push to feature branches
- Branch protection rules active on main/master

#### Step 0.3: Set Up Local Development Environment
**Tasks:**
1. Create project directory structure
   ```bash
   mkdir -p ~/projects/customer-care-system
   cd ~/projects/customer-care-system
   ```

2. Install Python dependencies (create virtual environment)
   ```bash
   cd customer-care-lambdas
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install boto3 botocore pytest
   ```

3. Install Node.js dependencies for CDK
   ```bash
   cd customer-care-infrastructure
   npm install
   ```

4. Configure environment variables
   ```bash
   # Create .env file for local development
   cat > .env << EOF
   AWS_REGION=us-east-1
   ENVIRONMENT=dev
   PROJECT_NAME=customer-care
   EOF
   ```

**Validation:**
- Virtual environment activates successfully
- npm install completes without errors
- .env file created

---

## Stage 1: Google Cloud Platform Setup

### Duration: 1 day

### Objectives
- Create Google Cloud Project
- Enable Google Drive API
- Create service account
- Configure Drive folder access
- Generate credentials

### Steps

#### Step 1.1: Authenticate with Google Cloud (Required First)
**Tasks:**
1. Open terminal and authenticate with Google Cloud:
   ```bash
   gcloud auth login
   ```
   This will open a browser window for you to sign in with your Google account.

2. Verify authentication:
   ```bash
   gcloud auth list  # Shows authenticated accounts
   ```

**Validation:**
- Your Google account email appears in the authenticated accounts list
- Account shows as active (indicated by asterisk *)

**Troubleshooting:**
- If browser doesn't open, copy the URL from terminal and open manually
- If running on remote system, use `gcloud auth login --no-browser` and follow instructions

#### Step 1.2: Create Google Cloud Project
**Tasks:**
1. Log in to [Google Cloud Console](https://console.cloud.google.com)

2. Create new project
   - Click "Select a project" → "New Project"
   - Project name: "customer-care-audio-processor"
   - Note the Project ID (e.g., `customer-care-audio-123456`)

3. Enable billing for the project
   - Navigation menu → Billing
   - Link billing account

4. **Add Environment Tag** (required by Google Cloud):
   
   **Easiest Method: Use Google Cloud Console**
   - Navigate to "IAM & Admin" → "Tags"
   - Create `environment` tag key if it doesn't exist
   - Create tag value: `Development` (or Test, Staging, Production)
   - Go to "Manage Resources" and select your project
   - Click "Tags" and add `environment=Development`
   
   **Alternative: Use gcloud CLI (after tag key is set up)**
   ```bash
   gcloud resource-manager tags bindings create \
     --tag-value=tagValues/TAGVALUE_ID \
     --parent=//cloudresourcemanager.googleapis.com/projects/YOUR_PROJECT_ID
   ```
   > See [Attaching tags to resources](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#attaching) for the full command reference.
   
   **Tag Options:** Development, Test, Staging, or Production

5. Set the project as your active project:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   gcloud config get-value project  # Verify
   ```

**Validation:**
- Project created and visible in console
- Project ID noted for later use
- Billing enabled
- Environment tag created:
  ```bash
  gcloud resource-manager tags bindings list --parent=//cloudresourcemanager.googleapis.com/projects/YOUR_PROJECT_ID
  ```
- Project set as active in gcloud CLI

#### Step 1.3: Enable Google Drive API
**Tasks:**
1. In Google Cloud Console, navigate to "APIs & Services" → "Library"

2. Search for "Google Drive API"

3. Click "Enable"

4. Wait for API enablement (usually immediate)

5. Enable via CLI (alternative method):
   ```bash
   gcloud services enable drive.googleapis.com
   ```

**Validation:**
- Navigate to "APIs & Services" → "Dashboard"
- Confirm "Google Drive API" shows as enabled
- Or verify via CLI: `gcloud services list --enabled --filter="name:drive.googleapis.com"`

#### Step 1.4: Create Service Account
**Tasks:**
1. Navigate to "IAM & Admin" → "Service Accounts"

2. Click "Create Service Account"

3. Service account details:
   - Name: `customer-care-drive-reader`
   - ID: `customer-care-drive-reader` (auto-generated)
   - Description: "Service account for reading customer care call recordings from Google Drive"

4. Grant roles (click "Continue"):
   - No roles needed at project level (we'll grant folder-level access)

5. Skip "Grant users access" (click "Done")

**Validation:**
- Service account appears in list
- Note the service account email (e.g., `customer-care-drive-reader@customer-care-audio-123456.iam.gserviceaccount.com`)

#### Step 1.5: Generate Service Account Key
**Tasks:**
1. Click on the service account you just created

2. Go to "Keys" tab

3. Click "Add Key" → "Create new key"

4. Select "JSON" format

5. Click "Create"

6. Save the downloaded JSON file securely (e.g., `google-service-account-key.json`)

**⚠️ SECURITY WARNING:**
- This JSON file contains credentials that provide access to Google Drive
- Never commit this file to version control
- Store in a secure location (will upload to AWS Secrets Manager later)

**Validation:**
- JSON file downloaded
- File contains: `type`, `project_id`, `private_key_id`, `private_key`, `client_email`

#### Step 1.5: Create Google Drive Folder
**Tasks:**
1. Log in to Google Drive with administrator account

2. Create folder structure:
   ```
   Customer Care Recordings/
   ├── Incoming/  (for new uploads)
   └── Processed/ (for archived files - optional)
   ```

3. Note the folder ID for "Incoming" folder:
   - Open the "Incoming" folder
   - Copy folder ID from URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - Example: `1a2b3c4d5e6f7g8h9i0j`

4. Share folder with service account:
   - Right-click "Incoming" folder → Share
   - Enter service account email: `customer-care-drive-reader@customer-care-audio-123456.iam.gserviceaccount.com`
   - Permission: "Viewer" (read-only)
   - Uncheck "Notify people"
   - Click "Share"

**Validation:**
- Folder created in Google Drive
- Folder ID noted
- Service account has Viewer access
- Test: Upload a test file to confirm service account can access it

#### Step 1.6: Test Service Account Access
**Tasks:**
1. Create test script `test_google_drive.py`:
   ```python
   from google.oauth2 import service_account
   from googleapiclient.discovery import build
   
   # Path to your service account key file
   SERVICE_ACCOUNT_FILE = 'google-service-account-key.json'
   FOLDER_ID = 'YOUR_FOLDER_ID_HERE'
   
   # Authenticate
   credentials = service_account.Credentials.from_service_account_file(
       SERVICE_ACCOUNT_FILE,
       scopes=['https://www.googleapis.com/auth/drive.readonly']
   )
   
   # Build Drive API client
   service = build('drive', 'v3', credentials=credentials)
   
   # List files in folder
   results = service.files().list(
       q=f"'{FOLDER_ID}' in parents",
       pageSize=10,
       fields="files(id, name, mimeType, size)"
   ).execute()
   
   files = results.get('files', [])
   print(f"Found {len(files)} files:")
   for file in files:
       print(f"  - {file['name']} ({file['mimeType']})")
   ```

2. Install required Python package:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

3. Run test script:
   ```bash
   python test_google_drive.py
   ```

**Validation:**
- Script runs without errors
- Lists any files in the folder (or shows 0 files if empty)

**Outputs from Stage 1:**
- ✓ Google Cloud Project ID
- ✓ Service account email
- ✓ Service account JSON key file
- ✓ Google Drive folder ID
- ✓ Confirmed service account can read folder

---

## Stage 2: AWS Account and Foundation Setup

### Duration: 1-2 days

### Objectives
- Set up AWS account and organization
- Configure AWS CLI credentials
- Set up multi-account structure (optional)
- Initialize CDK project
- Configure infrastructure as code

### Steps

#### Step 2.1: AWS Account Setup
**Tasks:**
1. Create AWS account or use existing:
   - Sign up at [aws.amazon.com](https://aws.amazon.com)
   - Set up root user MFA (required)

2. Create IAM user for development:
   - Navigate to IAM → Users → Add User
   - Username: `customer-care-developer`
   - Access type: Programmatic access
   - Permissions: AdministratorAccess (or create custom policy)
   - Download access key CSV

3. Configure AWS CLI:
   ```bash
   aws configure --profile customer-care-dev
   # AWS Access Key ID: [Your access key]
   # AWS Secret Access Key: [Your secret key]
   # Default region: us-east-1
   # Default output format: json
   ```

4. Set environment variable:
   ```bash
   export AWS_PROFILE=customer-care-dev
   # Add to ~/.bashrc or ~/.zshrc for persistence
   ```

**Validation:**
```bash
aws sts get-caller-identity
# Should return your user ARN and account ID
```

#### Step 2.2: Set Up AWS Organization (Optional but Recommended)
**Tasks:**
1. Navigate to AWS Organizations console

2. Create organization if not exists

3. Create Organizational Units (OUs):
   - Development
   - Staging
   - Production

4. Create separate AWS accounts for each environment (optional):
   - `customer-care-dev` (123456789012)
   - `customer-care-staging` (234567890123)
   - `customer-care-prod` (345678901234)

5. Enable trusted access for AWS services:
   - CloudFormation StackSets
   - AWS Config
   - CloudTrail

**Validation:**
- Organization structure visible in console
- Can switch between accounts using role assumption

#### Step 2.3: Initialize CDK Project
**Tasks:**
1. Create CDK project directory:
   ```bash
   cd customer-care-infrastructure
   cdk init app --language=typescript
   ```

2. Install required CDK libraries:
   ```bash
   npm install @aws-cdk/aws-s3 @aws-cdk/aws-dynamodb \
     @aws-cdk/aws-lambda @aws-cdk/aws-apigateway \
     @aws-cdk/aws-stepfunctions @aws-cdk/aws-stepfunctions-tasks \
     @aws-cdk/aws-cognito @aws-cdk/aws-secretsmanager \
     @aws-cdk/aws-cloudwatch @aws-cdk/aws-sns \
     @aws-cdk/aws-iam @aws-cdk/aws-logs
   ```

3. Create stack structure:
   ```bash
   mkdir -p lib/stacks
   touch lib/stacks/storage-stack.ts
   touch lib/stacks/auth-stack.ts
   touch lib/stacks/api-stack.ts
   touch lib/stacks/processing-stack.ts
   touch lib/stacks/monitoring-stack.ts
   ```

4. Configure CDK context (`cdk.json`):
   ```json
   {
     "app": "npx ts-node bin/customer-care-infrastructure.ts",
     "context": {
       "projectName": "customer-care",
       "environments": {
         "dev": {
           "account": "123456789012",
           "region": "us-east-1"
         },
         "staging": {
           "account": "234567890123",
           "region": "us-east-1"
         },
         "prod": {
           "account": "345678901234",
           "region": "us-east-1"
         }
       }
     }
   }
   ```

**Validation:**
```bash
cdk ls  # Should list stack names
cdk synth  # Should synthesize CloudFormation templates without errors
```

#### Step 2.4: Bootstrap CDK
**Tasks:**
1. Bootstrap CDK in target account/region:
   ```bash
   cdk bootstrap aws://123456789012/us-east-1 --profile customer-care-dev
   ```

2. Verify bootstrap stack created:
   ```bash
   aws cloudformation describe-stacks --stack-name CDKToolkit --profile customer-care-dev
   ```

**Validation:**
- CDKToolkit stack shows CREATE_COMPLETE status
- S3 bucket created for CDK assets (e.g., `cdktoolkit-stagingbucket-xxxxx`)

#### Step 2.5: Configure Tagging Strategy
**Tasks:**
1. Create tagging policy file (`lib/config/tags.ts`):
   ```typescript
   export const commonTags = {
     Project: 'CustomerCare',
     Environment: process.env.ENVIRONMENT || 'dev',
     ManagedBy: 'CDK',
     CostCenter: 'IT-Operations',
     Owner: 'Platform-Team',
     Compliance: 'HIPAA-Ready'
   };
   ```

2. Apply tags to all stacks in main CDK app

**Validation:**
- Tags defined and importable
- Will be applied when stacks are deployed

**Outputs from Stage 2:**
- ✓ AWS account configured
- ✓ AWS CLI working with correct profile
- ✓ CDK project initialized
- ✓ CDK bootstrapped in target region
- ✓ Multi-stack structure created
- ✓ Tagging strategy defined

---

## Stage 3: AWS Storage Layer Setup

### Duration: 1 day

### Objectives
- Create S3 buckets for audio, transcripts, summaries
- Create DynamoDB tables
- Configure lifecycle policies
- Set up encryption

### Steps

#### Step 3.1: Create S3 Bucket Stack
**Tasks:**
1. Implement Storage Stack (`lib/stacks/storage-stack.ts`):
   ```typescript
   import * as cdk from 'aws-cdk-lib';
   import * as s3 from 'aws-cdk-lib/aws-s3';
   import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
   import { Construct } from 'constructs';
   
   export class StorageStack extends cdk.Stack {
     public readonly audioBucket: s3.Bucket;
     public readonly callSummariesTable: dynamodb.Table;
     public readonly websocketConnectionsTable: dynamodb.Table;
     public readonly usersTable: dynamodb.Table;
     
     constructor(scope: Construct, id: string, props?: cdk.StackProps) {
       super(scope, id, props);
       
       // S3 Bucket for audio files
       this.audioBucket = new s3.Bucket(this, 'CustomerCareAudioBucket', {
         bucketName: `customer-care-audio-${this.account}-${this.stackName}`,
         encryption: s3.BucketEncryption.S3_MANAGED,
         versioned: true,
         blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
         lifecycleRules: [
           {
             id: 'TransitionToGlacier',
             transitions: [{
               storageClass: s3.StorageClass.GLACIER,
               transitionAfter: cdk.Duration.days(90)
             }]
           }
         ],
         cors: [{
           allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.HEAD],
           allowedOrigins: ['*'], // Restrict in production
           allowedHeaders: ['*'],
           maxAge: 3600
         }]
       });
       
       // DynamoDB table implementation continues...
     }
   }
   ```

2. Define folder structure (logical - will be created by uploads):
   ```
   /raw-audio/YYYY-MM-DD/{call-id}.ext
   /transcripts/YYYY-MM-DD/{call-id}-transcript.json
   /summaries/YYYY-MM-DD/{call-id}-summary.json
   ```

**Validation:**
- CDK synth succeeds
- CloudFormation template generated

#### Step 3.2: Create DynamoDB Tables
**Tasks:**
1. Add DynamoDB tables to Storage Stack:
   ```typescript
   // Table 1: call-summaries
   this.callSummariesTable = new dynamodb.Table(this, 'CallSummariesTable', {
     tableName: `customer-care-summaries-${this.stackName}`,
     partitionKey: { name: 'call_id', type: dynamodb.AttributeType.STRING },
     sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
     billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
     encryption: dynamodb.TableEncryption.AWS_MANAGED,
     pointInTimeRecovery: true,
     stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
   });
   
   // GSI 1: status-timestamp-index
   this.callSummariesTable.addGlobalSecondaryIndex({
     indexName: 'status-timestamp-index',
     partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
     sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING }
   });
   
   // GSI 2: user-timestamp-index
   this.callSummariesTable.addGlobalSecondaryIndex({
     indexName: 'user-timestamp-index',
     partitionKey: { name: 'assigned_user', type: dynamodb.AttributeType.STRING },
     sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING }
   });
   
   // GSI 3: date-index
   this.callSummariesTable.addGlobalSecondaryIndex({
     indexName: 'date-index',
     partitionKey: { name: 'call_date', type: dynamodb.AttributeType.STRING },
     sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING }
   });
   
   // Table 2: websocket-connections
   this.websocketConnectionsTable = new dynamodb.Table(this, 'WebsocketConnectionsTable', {
     tableName: `customer-care-websocket-connections-${this.stackName}`,
     partitionKey: { name: 'connectionId', type: dynamodb.AttributeType.STRING },
     billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
     timeToLiveAttribute: 'ttl'
   });
   
   // Table 3: users
   this.usersTable = new dynamodb.Table(this, 'UsersTable', {
     tableName: `customer-care-users-${this.stackName}`,
     partitionKey: { name: 'email', type: dynamodb.AttributeType.STRING },
     billingMode: dynamodb.BillingMode.PAY_PER_REQUEST
   });
   ```

**Validation:**
- All three tables defined in stack
- GSIs properly configured
- Encryption enabled

#### Step 3.3: Deploy Storage Stack
**Tasks:**
1. Deploy stack:
   ```bash
   cdk deploy StorageStack --profile customer-care-dev
   ```

2. Wait for deployment (3-5 minutes)

3. Note outputs:
   - S3 bucket name
   - DynamoDB table names

**Validation:**
```bash
# Verify S3 bucket created
aws s3 ls --profile customer-care-dev | grep customer-care-audio

# Verify DynamoDB tables created
aws dynamodb list-tables --profile customer-care-dev
```

**Outputs from Stage 3:**
- ✓ S3 bucket created with lifecycle policies
- ✓ DynamoDB tables created with GSIs
- ✓ Encryption enabled on all resources
- ✓ Bucket and table names noted

---

## Stage 4: Google-AWS Communication Bridge

### Duration: 1 day

### Objectives
- Store Google credentials in AWS Secrets Manager
- Create IAM roles for Lambda functions
- Test credential retrieval

### Steps

#### Step 4.1: Store Google Service Account Credentials
**Tasks:**
1. Upload service account JSON to AWS Secrets Manager:
   ```bash
   aws secretsmanager create-secret \
     --name customer-care/google-service-account \
     --description "Google Drive service account credentials" \
     --secret-string file://google-service-account-key.json \
     --profile customer-care-dev
   ```

2. Note the Secret ARN from output

3. Store Google Drive folder ID as secret:
   ```bash
   aws secretsmanager create-secret \
     --name customer-care/google-drive-folder-id \
     --description "Google Drive folder ID for call recordings" \
     --secret-string '{"folderId":"YOUR_FOLDER_ID_HERE"}' \
     --profile customer-care-dev
   ```

4. Store webhook verification token:
   ```bash
   # Generate random token
   WEBHOOK_TOKEN=$(openssl rand -hex 32)
   
   aws secretsmanager create-secret \
     --name customer-care/webhook-token \
     --description "Token for Google Drive webhook verification" \
     --secret-string "{\"token\":\"$WEBHOOK_TOKEN\"}" \
     --profile customer-care-dev
   
   # Save token for Google webhook configuration later
   echo $WEBHOOK_TOKEN > webhook-token.txt
   ```

**Validation:**
```bash
# List secrets
aws secretsmanager list-secrets --profile customer-care-dev

# Retrieve secret (test)
aws secretsmanager get-secret-value \
  --secret-id customer-care/google-service-account \
  --profile customer-care-dev
```

#### Step 4.2: Create IAM Policy for Secrets Access
**Tasks:**
1. Create IAM policy document (`policies/secrets-read-policy.json`):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "secretsmanager:GetSecretValue"
         ],
         "Resource": [
           "arn:aws:secretsmanager:us-east-1:123456789012:secret:customer-care/*"
         ]
       }
     ]
   }
   ```

2. Create policy:
   ```bash
   aws iam create-policy \
     --policy-name CustomerCareSecretsReadPolicy \
     --policy-document file://policies/secrets-read-policy.json \
     --profile customer-care-dev
   ```

**Validation:**
- Policy created successfully
- ARN noted for attaching to Lambda roles

#### Step 4.3: Configure Secret Rotation (Optional)
**Tasks:**
1. Set up rotation Lambda (future enhancement)
2. Configure 90-day rotation schedule

**Validation:**
- Rotation configured (or noted for future implementation)

**Outputs from Stage 4:**
- ✓ Google service account credentials stored in Secrets Manager
- ✓ Folder ID stored in Secrets Manager
- ✓ Webhook token generated and stored
- ✓ IAM policy created for secrets access
- ✓ Secret ARNs noted

---

## Stage 5: Data Ingestion Layer

### Duration: 2-3 days

### Objectives
- Create API Gateway webhook endpoint
- Implement webhook handler Lambda function
- Configure Google Drive webhook
- Test end-to-end file upload flow

### Steps

#### Step 5.1: Implement Webhook Handler Lambda Function
**Tasks:**
1. Create Lambda function code (`lambdas/webhook-handler/index.py`):
   ```python
   import json
   import os
   import boto3
   from google.oauth2 import service_account
   from googleapiclient.discovery import build
   from datetime import datetime
   import uuid
   
   # AWS clients
   s3_client = boto3.client('s3')
   dynamodb = boto3.resource('dynamodb')
   secrets_client = boto3.client('secretsmanager')
   sfn_client = boto3.client('stepfunctions')
   
   # Environment variables
   BUCKET_NAME = os.environ['BUCKET_NAME']
   TABLE_NAME = os.environ['TABLE_NAME']
   STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']
   WEBHOOK_TOKEN_SECRET = os.environ['WEBHOOK_TOKEN_SECRET']
   GOOGLE_CREDS_SECRET = os.environ['GOOGLE_CREDS_SECRET']
   
   def lambda_handler(event, context):
       # Validate webhook token
       # Download file from Google Drive
       # Upload to S3
       # Create DynamoDB record
       # Trigger Step Functions
       # Return response
       pass  # Implementation details...
   ```

2. Create requirements.txt:
   ```
   boto3==1.34.0
   google-auth==2.25.0
   google-auth-oauthlib==1.2.0
   google-auth-httplib2==0.2.0
   google-api-python-client==2.110.0
   ```

3. Package Lambda function:
   ```bash
   cd lambdas/webhook-handler
   pip install -r requirements.txt -t .
   zip -r webhook-handler.zip .
   ```

**Validation:**
- Lambda code written
- Dependencies packaged
- Zip file created

#### Step 5.2: Create API Gateway and Lambda in CDK
**Tasks:**
1. Create API Stack (`lib/stacks/api-stack.ts`):
   ```typescript
   import * as cdk from 'aws-cdk-lib';
   import * as lambda from 'aws-cdk-lib/aws-lambda';
   import * as apigateway from 'aws-cdk-lib/aws-apigateway';
   import * as iam from 'aws-cdk-lib/aws-iam';
   import { Construct } from 'constructs';
   
   export class ApiStack extends cdk.Stack {
     constructor(scope: Construct, id: string, 
                 storageBucket: s3.Bucket,
                 summariesTable: dynamodb.Table,
                 props?: cdk.StackProps) {
       super(scope, id, props);
       
       // Webhook Handler Lambda
       const webhookHandler = new lambda.Function(this, 'WebhookHandler', {
         runtime: lambda.Runtime.PYTHON_3_11,
         handler: 'index.lambda_handler',
         code: lambda.Code.fromAsset('lambdas/webhook-handler/webhook-handler.zip'),
         timeout: cdk.Duration.minutes(5),
         memorySize: 1024,
         environment: {
           BUCKET_NAME: storageBucket.bucketName,
           TABLE_NAME: summariesTable.tableName,
           WEBHOOK_TOKEN_SECRET: 'customer-care/webhook-token',
           GOOGLE_CREDS_SECRET: 'customer-care/google-service-account'
         }
       });
       
       // Grant permissions
       storageBucket.grantWrite(webhookHandler);
       summariesTable.grantWriteData(webhookHandler);
       
       // API Gateway
       const api = new apigateway.RestApi(this, 'CustomerCareApi', {
         restApiName: 'Customer Care API',
         description: 'API for customer care call processing'
       });
       
       const webhook = api.root.addResource('webhook');
       const gdriveWebhook = webhook.addResource('gdrive');
       gdriveWebhook.addMethod('POST', new apigateway.LambdaIntegration(webhookHandler));
     }
   }
   ```

**Validation:**
- CDK synth succeeds
- Lambda and API Gateway resources defined

#### Step 5.3: Deploy API Stack
**Tasks:**
1. Deploy:
   ```bash
   cdk deploy ApiStack --profile customer-care-dev
   ```

2. Note API Gateway endpoint URL from output (e.g., `https://abc123.execute-api.us-east-1.amazonaws.com/prod`)

**Validation:**
```bash
# Test endpoint (should return error without valid webhook data)
curl -X POST https://abc123.execute-api.us-east-1.amazonaws.com/prod/webhook/gdrive
```

#### Step 5.4: Configure Google Drive Webhook
**Tasks:**
1. Create script to set up webhook (`scripts/setup-google-webhook.py`):
   ```python
   from google.oauth2 import service_account
   from googleapiclient.discovery import build
   import uuid
   
   SERVICE_ACCOUNT_FILE = 'google-service-account-key.json'
   FOLDER_ID = 'YOUR_FOLDER_ID'
   WEBHOOK_URL = 'https://abc123.execute-api.us-east-1.amazonaws.com/prod/webhook/gdrive'
   WEBHOOK_TOKEN = 'YOUR_WEBHOOK_TOKEN'
   
   credentials = service_account.Credentials.from_service_account_file(
       SERVICE_ACCOUNT_FILE,
       scopes=['https://www.googleapis.com/auth/drive.readonly']
   )
   
   service = build('drive', 'v3', credentials=credentials)
   
   # Create webhook
   channel_id = str(uuid.uuid4())
   body = {
       'id': channel_id,
       'type': 'web_hook',
       'address': WEBHOOK_URL,
       'token': WEBHOOK_TOKEN,
       'expiration': None  # Will need renewal
   }
   
   response = service.files().watch(
       fileId=FOLDER_ID,
       body=body,
       supportsAllDrives=True
   ).execute()
   
   print(f"Webhook created: {response}")
   print(f"Channel ID: {channel_id}")
   print(f"Resource ID: {response['resourceId']}")
   ```

2. Run script:
   ```bash
   python scripts/setup-google-webhook.py
   ```

3. Save channel ID and resource ID for future renewal

**Validation:**
- Webhook created successfully
- No errors from Google API

#### Step 5.5: Test End-to-End Upload Flow
**Tasks:**
1. Upload test audio file to Google Drive folder

2. Monitor CloudWatch Logs for Lambda invocation:
   ```bash
   aws logs tail /aws/lambda/webhook-handler --follow --profile customer-care-dev
   ```

3. Verify in S3:
   ```bash
   aws s3 ls s3://customer-care-audio-ACCOUNT-ID/raw-audio/ --recursive --profile customer-care-dev
   ```

4. Verify in DynamoDB:
   ```bash
   aws dynamodb scan --table-name customer-care-summaries-dev --profile customer-care-dev
   ```

**Validation:**
- Webhook receives notification within 10 seconds
- File downloaded from Google Drive
- File uploaded to S3 in correct folder structure
- DynamoDB record created with status "UPLOADED"
- CloudWatch metrics show successful execution

**Outputs from Stage 5:**
- ✓ Webhook handler Lambda deployed
- ✓ API Gateway endpoint configured
- ✓ Google Drive webhook configured
- ✓ End-to-end file upload tested successfully
- ✓ Webhook channel ID noted for renewal

---

## Stage 6: AI Services Configuration

### Duration: 2-3 days

### Objectives
- Request and configure Amazon Transcribe
- Request and configure Amazon Bedrock access
- Test AI services
- Optimize prompts for Claude

### Steps

#### Step 6.1: Enable Amazon Transcribe
**Tasks:**
1. Verify Amazon Transcribe is available in your region:
   ```bash
   aws transcribe help --profile customer-care-dev
   ```

2. Create test transcription job:
   ```bash
   # Upload test audio to S3 first
   aws s3 cp test-audio.mp3 s3://customer-care-audio-ACCOUNT/test/ --profile customer-care-dev
   
   # Start transcription job
   aws transcribe start-transcription-job \
     --transcription-job-name test-transcription-001 \
     --media MediaFileUri=s3://customer-care-audio-ACCOUNT/test/test-audio.mp3 \
     --output-bucket-name customer-care-audio-ACCOUNT \
     --language-code en-US \
     --settings ShowSpeakerLabels=true,MaxSpeakerLabels=2 \
     --profile customer-care-dev
   ```

3. Check job status:
   ```bash
   aws transcribe get-transcription-job \
     --transcription-job-name test-transcription-001 \
     --profile customer-care-dev
   ```

4. Review output in S3

**Validation:**
- Transcription job completes successfully
- Output JSON contains transcript with speaker labels
- Transcription accuracy acceptable (>85%)

#### Step 6.2: Request Amazon Bedrock Model Access
**Tasks:**
1. Navigate to AWS Bedrock Console

2. Go to "Model access" in left sidebar

3. Click "Request model access"

4. Select models:
   - ✓ Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)
   - ✓ Claude 3 Haiku (optional - for cost optimization)

5. Submit access request

6. Wait for approval (typically immediate for most accounts, may take up to 24 hours)

**Validation:**
- Model access shows "Access granted" status
- Model available in us-east-1 (or your chosen region)

#### Step 6.3: Test Amazon Bedrock
**Tasks:**
1. Create test script (`scripts/test-bedrock.py`):
   ```python
   import boto3
   import json
   
   bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
   
   # Test prompt
   prompt = """You are an expert customer service analyst. 
   Analyze this call transcript and provide a structured summary.
   
   Transcript:
   Agent: Thank you for calling. How can I help you today?
   Customer: Hi, my internet has been down for 2 days. I need it fixed urgently.
   Agent: I apologize for the inconvenience. Let me check your account. Can I have your account number?
   Customer: It's 12345678.
   Agent: Thank you. I see the issue. We'll send a technician tomorrow between 9-12.
   Customer: That works. Thank you.
   
   Provide output in JSON format with these fields:
   - call_date: date of call
   - issue_sentence: one sentence summary
   - key_details: array of key details
   - action_items: array of actions
   - next_steps: array of next steps
   - sentiment: Positive, Neutral, or Negative
   """
   
   request_body = {
       "anthropic_version": "bedrock-2023-05-31",
       "max_tokens": 2000,
       "temperature": 0.3,
       "top_p": 0.9,
       "messages": [
           {
               "role": "user",
               "content": prompt
           }
       ]
   }
   
   response = bedrock.invoke_model(
       modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
       body=json.dumps(request_body)
   )
   
   response_body = json.loads(response['body'].read())
   print(json.dumps(response_body, indent=2))
   ```

2. Run test:
   ```bash
   python scripts/test-bedrock.py
   ```

**Validation:**
- Script executes without errors
- Returns structured JSON summary
- Summary quality is acceptable
- Response time < 5 seconds

#### Step 6.4: Optimize Prompts for Production
**Tasks:**
1. Create prompt template file (`config/bedrock-prompt-template.txt`):
   ```
   You are an expert customer service analyst specializing in analyzing customer care call transcripts.
   
   Your task is to analyze the following call transcript and extract key information.
   
   IMPORTANT INSTRUCTIONS:
   - Be factual and accurate. Do not make assumptions or add information not in the transcript.
   - Focus on the customer's issue and what actions were taken or promised.
   - Identify sentiment based on the overall tone of the conversation.
   - Output ONLY valid JSON, no additional text.
   
   TRANSCRIPT:
   {transcript_text}
   
   Provide your analysis in this exact JSON format:
   {
     "call_date": "YYYY-MM-DD",
     "issue_sentence": "Single sentence describing the main issue",
     "key_details": ["Detail 1", "Detail 2", "Detail 3"],
     "action_items": ["Action 1", "Action 2"],
     "next_steps": ["Step 1", "Step 2"],
     "sentiment": "Positive|Neutral|Negative",
     "agent_id": "extracted if mentioned, otherwise null",
     "customer_id": "extracted if mentioned, otherwise null"
   }
   ```

2. Test various prompt variations:
   - Test with different transcript lengths
   - Test with different issue types
   - Test with emotional content
   - Test with unclear transcripts

3. Measure:
   - JSON parse success rate (target: 100%)
   - Field completeness (target: 100%)
   - Summary relevance (manual review)
   - Token usage per call

**Validation:**
- Prompt consistently produces valid JSON
- All required fields present
- Summary quality rated 4/5 or higher by reviewers
- Token usage < 2000 tokens per summary

#### Step 6.5: Create Service Quota Increase Requests (If Needed)
**Tasks:**
1. Navigate to Service Quotas console

2. Check current quotas:
   - Amazon Transcribe: Concurrent transcription jobs (default: 10)
   - Amazon Bedrock: Tokens per minute (varies by model)

3. Calculate required quotas:
   - Peak load: 100 calls per hour = ~1.67 calls per minute
   - Transcribe: Need at least 5 concurrent jobs
   - Bedrock: Estimate 1000 tokens per call input + 500 tokens output = 1500 tokens/call
   - For 100 calls/hour: 150,000 tokens/hour = 2,500 tokens/minute

4. Request increases if needed:
   - Transcribe: Increase to 20 concurrent jobs
   - Bedrock: Increase token limit if default is insufficient

**Validation:**
- Current quotas checked and noted
- Increase requests submitted if needed
- Approval received (may take 24-48 hours)

**Outputs from Stage 6:**
- ✓ Amazon Transcribe tested and working
- ✓ Amazon Bedrock access granted
- ✓ Claude 3.5 Sonnet tested and working
- ✓ Prompt template optimized
- ✓ Service quotas sufficient for load
- ✓ Token usage per call measured

---

## Stage 7: Processing Orchestration Layer

### Duration: 3-4 days

### Objectives
- Create AWS Step Functions state machine
- Implement processing Lambda functions
- Test end-to-end processing pipeline
- Configure error handling and retries

### Steps

#### Step 7.1: Design State Machine
**Tasks:**
1. Create state machine definition (`config/step-functions-definition.json`):
   ```json
   {
     "Comment": "Customer Care Call Processing Pipeline",
     "StartAt": "UpdateStatusTranscribing",
     "States": {
       "UpdateStatusTranscribing": {
         "Type": "Task",
         "Resource": "arn:aws:states:::dynamodb:updateItem",
         "Parameters": {
           "TableName": "${TableName}",
           "Key": {
             "call_id": {"S.$": "$.call_id"}
           },
           "UpdateExpression": "SET #status = :status",
           "ExpressionAttributeNames": {
             "#status": "status"
           },
           "ExpressionAttributeValues": {
             ":status": {"S": "TRANSCRIBING"}
           }
         },
         "Next": "TranscribeAudio"
       },
       "TranscribeAudio": {
         "Type": "Task",
         "Resource": "arn:aws:states:::aws-sdk:transcribe:startTranscriptionJob.sync",
         "Parameters": {
           "TranscriptionJobName.$": "$.call_id",
           "Media": {
             "MediaFileUri.$": "States.Format('s3://{}/{}', $.s3_bucket, $.s3_key)"
           },
           "LanguageCode": "en-US",
           "Settings": {
             "ShowSpeakerLabels": true,
             "MaxSpeakerLabels": 2
           }
         },
         "Next": "ProcessTranscript",
         "Catch": [{
           "ErrorEquals": ["States.ALL"],
           "Next": "MarkAsFailed"
         }],
         "Retry": [{
           "ErrorEquals": ["States.ALL"],
           "IntervalSeconds": 2,
           "MaxAttempts": 3,
           "BackoffRate": 2.0
         }]
       },
       "ProcessTranscript": {
         "Type": "Task",
         "Resource": "arn:aws:states:::lambda:invoke",
         "Parameters": {
           "FunctionName": "${ProcessTranscriptFunction}",
           "Payload.$": "$"
         },
         "Next": "UpdateStatusSummarizing",
         "Catch": [{
           "ErrorEquals": ["States.ALL"],
           "Next": "MarkAsFailed"
         }]
       },
       "UpdateStatusSummarizing": {
         "Type": "Task",
         "Resource": "arn:aws:states:::dynamodb:updateItem",
         "Parameters": {
           "TableName": "${TableName}",
           "Key": {
             "call_id": {"S.$": "$.call_id"}
           },
           "UpdateExpression": "SET #status = :status",
           "ExpressionAttributeNames": {
             "#status": "status"
           },
           "ExpressionAttributeValues": {
             ":status": {"S": "SUMMARIZING"}
           }
         },
         "Next": "GenerateSummary"
       },
       "GenerateSummary": {
         "Type": "Task",
         "Resource": "arn:aws:states:::lambda:invoke",
         "Parameters": {
           "FunctionName": "${GenerateSummaryFunction}",
           "Payload.$": "$"
         },
         "Next": "SaveToDynamoDB",
         "Catch": [{
           "ErrorEquals": ["States.ALL"],
           "Next": "MarkAsFailed"
         }],
         "Retry": [{
           "ErrorEquals": ["ThrottlingException"],
           "IntervalSeconds": 5,
           "MaxAttempts": 5,
           "BackoffRate": 2.0
         }]
       },
       "SaveToDynamoDB": {
         "Type": "Task",
         "Resource": "arn:aws:states:::lambda:invoke",
         "Parameters": {
           "FunctionName": "${SaveSummaryFunction}",
           "Payload.$": "$"
         },
         "Next": "NotifyFrontend",
         "Catch": [{
           "ErrorEquals": ["States.ALL"],
           "Next": "MarkAsFailed"
         }]
       },
       "NotifyFrontend": {
         "Type": "Task",
         "Resource": "arn:aws:states:::lambda:invoke",
         "Parameters": {
           "FunctionName": "${NotifyFunction}",
           "Payload.$": "$"
         },
         "End": true
       },
       "MarkAsFailed": {
         "Type": "Task",
         "Resource": "arn:aws:states:::dynamodb:updateItem",
         "Parameters": {
           "TableName": "${TableName}",
           "Key": {
             "call_id": {"S.$": "$.call_id"}
           },
           "UpdateExpression": "SET #status = :status, error_message = :error",
           "ExpressionAttributeNames": {
             "#status": "status"
           },
           "ExpressionAttributeValues": {
             ":status": {"S": "FAILED"},
             ":error": {"S.$": "$.Error"}
           }
         },
         "End": true
       }
     }
   }
   ```

**Validation:**
- State machine definition is valid JSON
- All states properly connected

#### Step 7.2: Implement Processing Lambda Functions
**Tasks:**
1. **Process Transcript Lambda** (`lambdas/process-transcript/index.py`):
   ```python
   import boto3
   import json
   
   s3_client = boto3.client('s3')
   transcribe_client = boto3.client('transcribe')
   
   def lambda_handler(event, context):
       """Parse Transcribe output and format for Bedrock"""
       
       call_id = event['call_id']
       job_name = call_id
       
       # Get transcript from Transcribe
       response = transcribe_client.get_transcription_job(
           TranscriptionJobName=job_name
       )
       
       transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
       
       # Download transcript JSON
       # Parse and format
       # Save formatted transcript to S3
       # Return formatted data
       
       return {
           'call_id': call_id,
           'transcript_text': formatted_transcript,
           's3_transcript_url': transcript_s3_url,
           'duration_seconds': duration,
           'speaker_talk_time': speaker_times
       }
   ```

2. **Generate Summary Lambda** (`lambdas/generate-summary/index.py`):
   ```python
   import boto3
   import json
   
   bedrock = boto3.client('bedrock-runtime')
   
   def lambda_handler(event, context):
       """Generate AI summary using Bedrock Claude"""
       
       transcript = event['transcript_text']
       call_id = event['call_id']
       
       # Load prompt template
       # Format prompt with transcript
       # Call Bedrock
       # Parse JSON response
       # Validate all fields present
       
       return {
           **event,
           'summary': summary_json,
           'bedrock_request_id': request_id,
           'tokens_used': token_count
       }
   ```

3. **Save Summary Lambda** (`lambdas/save-summary/index.py`):
   ```python
   import boto3
   import json
   from datetime import datetime
   
   dynamodb = boto3.resource('dynamodb')
   s3_client = boto3.client('s3')
   
   def lambda_handler(event, context):
       """Save summary to DynamoDB and S3"""
       
       table = dynamodb.Table(os.environ['TABLE_NAME'])
       bucket = os.environ['BUCKET_NAME']
       
       # Prepare record
       # Save summary JSON to S3
       # Update DynamoDB with complete data
       # Mark status as COMPLETED
       
       return {
           'call_id': call_id,
           'status': 'COMPLETED',
           's3_summary_url': summary_url
       }
   ```

4. Package all Lambda functions:
   ```bash
   cd lambdas/process-transcript && pip install -r requirements.txt -t . && zip -r ../process-transcript.zip . && cd ../..
   cd lambdas/generate-summary && pip install -r requirements.txt -t . && zip -r ../generate-summary.zip . && cd ../..
   cd lambdas/save-summary && pip install -r requirements.txt -t . && zip -r ../save-summary.zip . && cd ../..
   ```

**Validation:**
- All Lambda functions packaged
- No syntax errors

#### Step 7.3: Create Processing Stack in CDK
**Tasks:**
1. Create Processing Stack (`lib/stacks/processing-stack.ts`):
   ```typescript
   import * as cdk from 'aws-cdk-lib';
   import * as lambda from 'aws-cdk-lib/aws-lambda';
   import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
   import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
   import { Construct } from 'constructs';
   
   export class ProcessingStack extends cdk.Stack {
     public readonly stateMachine: sfn.StateMachine;
     
     constructor(scope: Construct, id: string, props) {
       super(scope, id, props);
       
       // Lambda functions
       const processTranscriptFn = new lambda.Function(/*...*/);
       const generateSummaryFn = new lambda.Function(/*...*/);
       const saveSummaryFn = new lambda.Function(/*...*/);
       const notifyFn = new lambda.Function(/*...*/);
       
       // State machine definition
       // Grant permissions
       // Create CloudWatch alarms
     }
   }
   ```

**Validation:**
- CDK synth succeeds

#### Step 7.4: Deploy Processing Stack
**Tasks:**
1. Deploy:
   ```bash
   cdk deploy ProcessingStack --profile customer-care-dev
   ```

2. Note Step Functions ARN from output

**Validation:**
```bash
# List state machines
aws stepfunctions list-state-machines --profile customer-care-dev
```

#### Step 7.5: Test End-to-End Processing
**Tasks:**
1. Start execution manually:
   ```bash
   aws stepfunctions start-execution \
     --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:CustomerCareProcessing \
     --input '{"call_id":"test-001","s3_bucket":"customer-care-audio-123456789012-dev","s3_key":"raw-audio/2026-01-31/test-001.mp3","file_name":"test.mp3"}' \
     --profile customer-care-dev
   ```

2. Monitor execution in Step Functions console

3. Check CloudWatch Logs for each Lambda

4. Verify results:
   - Transcribe job completed
   - Transcript saved to S3
   - Summary generated
   - DynamoDB record updated with status "COMPLETED"

**Validation:**
- Execution completes successfully
- Processing time < 5 minutes for 5-minute call
- All data persisted correctly
- No errors in CloudWatch Logs

**Outputs from Stage 7:**
- ✓ Step Functions state machine deployed
- ✓ All processing Lambda functions deployed
- ✓ End-to-end processing pipeline tested
- ✓ Error handling and retries configured
- ✓ Processing time meets SLA (< 5 minutes)

---

## Stage 8: Backend API Layer

### Duration: 2-3 days

### Objectives
- Implement API Lambda functions (list, get, audio URL)
- Configure API Gateway endpoints
- Test all API endpoints
- Document API with OpenAPI

### Steps

#### Step 8.1: Implement API Lambda Functions
**Tasks:**
1. **List Summaries Lambda** (`lambdas/api-list-summaries/index.py`):
   ```python
   import boto3
   import json
   from decimal import Decimal
   
   dynamodb = boto3.resource('dynamodb')
   
   def lambda_handler(event, context):
       """List summaries with pagination and filtering"""
       
       table = dynamodb.Table(os.environ['TABLE_NAME'])
       
       # Parse query parameters
       limit = int(event.get('queryStringParameters', {}).get('limit', 20))
       status = event.get('queryStringParameters', {}).get('status')
       start_date = event.get('queryStringParameters', {}).get('startDate')
       end_date = event.get('queryStringParameters', {}).get('endDate')
       last_key = event.get('queryStringParameters', {}).get('lastEvaluatedKey')
       
       # Build query
       # Execute scan/query
       # Format response
       
       return {
           'statusCode': 200,
           'headers': {
               'Content-Type': 'application/json',
               'Access-Control-Allow-Origin': '*'
           },
           'body': json.dumps({
               'items': items,
               'lastEvaluatedKey': last_evaluated_key,
               'count': len(items)
           })
       }
   ```

2. **Get Summary Detail Lambda** (`lambdas/api-get-summary/index.py`):
   ```python
   def lambda_handler(event, context):
       """Get detailed summary for specific call"""
       
       call_id = event['pathParameters']['call_id']
       table = dynamodb.Table(os.environ['TABLE_NAME'])
       
       response = table.get_item(Key={'call_id': call_id})
       
       if 'Item' not in response:
           return {
               'statusCode': 404,
               'body': json.dumps({'error': 'Call not found'})
           }
       
       return {
           'statusCode': 200,
           'headers': {'Content-Type': 'application/json'},
           'body': json.dumps(response['Item'], default=decimal_serializer)
       }
   ```

3. **Get Audio URL Lambda** (`lambdas/api-get-audio-url/index.py`):
   ```python
   import boto3
   
   s3_client = boto3.client('s3')
   
   def lambda_handler(event, context):
       """Generate presigned URL for audio file"""
       
       call_id = event['pathParameters']['call_id']
       
       # Get S3 key from DynamoDB
       # Generate presigned URL (1 hour expiration)
       
       url = s3_client.generate_presigned_url(
           'get_object',
           Params={'Bucket': bucket, 'Key': key},
           ExpiresIn=3600
       )
       
       return {
           'statusCode': 200,
           'body': json.dumps({
               'audio_url': url,
               'expires_in': 3600
           })
       }
   ```

4. **Get Transcript Lambda** (`lambdas/api-get-transcript/index.py`):
   ```python
   def lambda_handler(event, context):
       """Get full transcript from S3"""
       
       call_id = event['pathParameters']['call_id']
       
       # Get transcript S3 URL from DynamoDB
       # Fetch transcript from S3
       # Return formatted transcript
       
       return {
           'statusCode': 200,
           'body': json.dumps(transcript_data)
       }
   ```

5. Package Lambda functions

**Validation:**
- All Lambda code written
- Functions packaged

#### Step 8.2: Update API Stack with New Endpoints
**Tasks:**
1. Update API Stack to include all endpoints:
   ```typescript
   // Add to ApiStack
   
   // GET /summaries
   const summaries = api.root.addResource('summaries');
   summaries.addMethod('GET', new apigateway.LambdaIntegration(listSummariesFn), {
     authorizer: cognitoAuthorizer  // Will add in next stage
   });
   
   // GET /summaries/{call_id}
   const summaryDetail = summaries.addResource('{call_id}');
   summaryDetail.addMethod('GET', new apigateway.LambdaIntegration(getSummaryFn));
   
   // GET /summaries/{call_id}/audio
   const audio = summaryDetail.addResource('audio');
   audio.addMethod('GET', new apigateway.LambdaIntegration(getAudioUrlFn));
   
   // GET /summaries/{call_id}/transcript
   const transcript = summaryDetail.addResource('transcript');
   transcript.addMethod('GET', new apigateway.LambdaIntegration(getTranscriptFn));
   ```

**Validation:**
- CDK synth succeeds

#### Step 8.3: Deploy Updated API Stack
**Tasks:**
1. Deploy:
   ```bash
   cdk deploy ApiStack --profile customer-care-dev
   ```

**Validation:**
- Deployment succeeds
- New endpoints accessible

#### Step 8.4: Test API Endpoints
**Tasks:**
1. Test list summaries:
   ```bash
   curl https://abc123.execute-api.us-east-1.amazonaws.com/prod/summaries?limit=10
   ```

2. Test get summary:
   ```bash
   curl https://abc123.execute-api.us-east-1.amazonaws.com/prod/summaries/test-001
   ```

3. Test get audio URL:
   ```bash
   curl https://abc123.execute-api.us-east-1.amazonaws.com/prod/summaries/test-001/audio
   ```

4. Test get transcript:
   ```bash
   curl https://abc123.execute-api.us-east-1.amazonaws.com/prod/summaries/test-001/transcript
   ```

**Validation:**
- All endpoints return correct status codes
- Data format matches expectations
- Presigned URL works (can download audio)
- Latency < 500ms (P95)

#### Step 8.5: Document API with OpenAPI
**Tasks:**
1. Generate OpenAPI specification (`api-docs/openapi.yaml`)
2. Add to API Gateway as documentation
3. Create Postman collection for testing

**Validation:**
- OpenAPI spec validates
- Documentation accessible

**Outputs from Stage 8:**
- ✓ All API Lambda functions implemented
- ✓ API endpoints deployed
- ✓ All endpoints tested successfully
- ✓ API latency meets SLA (< 500ms)
- ✓ API documentation created

---

## Stage 9: Authentication and Authorization

### Duration: 2 days

### Objectives
- Create Amazon Cognito User Pool
- Configure user groups and permissions
- Integrate Cognito with API Gateway
- Test authentication flow

### Steps

#### Step 9.1: Create Cognito User Pool
**Tasks:**
1. Create Auth Stack (`lib/stacks/auth-stack.ts`):
   ```typescript
   import * as cognito from 'aws-cdk-lib/aws-cognito';
   
   export class AuthStack extends cdk.Stack {
     public readonly userPool: cognito.UserPool;
     public readonly userPoolClient: cognito.UserPoolClient;
     
     constructor(scope: Construct, id: string, props?: cdk.StackProps) {
       super(scope, id, props);
       
       this.userPool = new cognito.UserPool(this, 'CustomerCareUserPool', {
         userPoolName: 'customer-care-users',
         selfSignUpEnabled: false,
         signInAliases: {
           email: true
         },
         passwordPolicy: {
           minLength: 8,
           requireLowercase: true,
           requireUppercase: true,
           requireDigits: true,
           requireSymbols: false
         },
         accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
         mfa: cognito.Mfa.OPTIONAL,
         mfaSecondFactor: {
           sms: false,
           otp: true
         }
       });
       
       // User groups
       new cognito.CfnUserPoolGroup(this, 'CaseworkersGroup', {
         userPoolId: this.userPool.userPoolId,
         groupName: 'caseworkers',
         description: 'Standard caseworker access'
       });
       
       new cognito.CfnUserPoolGroup(this, 'SupervisorsGroup', {
         userPoolId: this.userPool.userPoolId,
         groupName: 'supervisors',
         description: 'Supervisor access with analytics'
       });
       
       new cognito.CfnUserPoolGroup(this, 'AdminsGroup', {
         userPoolId: this.userPool.userPoolId,
         groupName: 'admins',
         description: 'Full system access'
       });
       
       // App client
       this.userPoolClient = this.userPool.addClient('WebAppClient', {
         authFlows: {
           userPassword: true,
           userSrp: true
         },
         oAuth: {
           flows: {
             authorizationCodeGrant: true
           },
           callbackUrls: ['http://localhost:3000', 'https://yourdomain.com'],
           logoutUrls: ['http://localhost:3000', 'https://yourdomain.com']
         }
       });
     }
   }
   ```

**Validation:**
- CDK synth succeeds

#### Step 9.2: Deploy Auth Stack
**Tasks:**
1. Deploy:
   ```bash
   cdk deploy AuthStack --profile customer-care-dev
   ```

2. Note outputs:
   - User Pool ID
   - User Pool Client ID
   - User Pool ARN

**Validation:**
```bash
# List user pools
aws cognito-idp list-user-pools --max-results 10 --profile customer-care-dev
```

#### Step 9.3: Create Test Users
**Tasks:**
1. Create admin user:
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id us-east-1_XXXXXXXXX \
     --username admin@example.com \
     --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true \
     --temporary-password TempPassword123! \
     --message-action SUPPRESS \
     --profile customer-care-dev
   ```

2. Add user to admins group:
   ```bash
   aws cognito-idp admin-add-user-to-group \
     --user-pool-id us-east-1_XXXXXXXXX \
     --username admin@example.com \
     --group-name admins \
     --profile customer-care-dev
   ```

3. Create test caseworker:
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id us-east-1_XXXXXXXXX \
     --username caseworker@example.com \
     --user-attributes Name=email,Value=caseworker@example.com Name=email_verified,Value=true \
     --temporary-password TempPassword123! \
     --profile customer-care-dev
   
   aws cognito-idp admin-add-user-to-group \
     --user-pool-id us-east-1_XXXXXXXXX \
     --username caseworker@example.com \
     --group-name caseworkers \
     --profile customer-care-dev
   ```

**Validation:**
- Users created successfully
- Can see users in Cognito console

#### Step 9.4: Integrate Cognito with API Gateway
**Tasks:**
1. Update API Stack to add Cognito authorizer:
   ```typescript
   const authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
     cognitoUserPools: [userPool]
   });
   
   // Update all protected endpoints
   summaries.addMethod('GET', new apigateway.LambdaIntegration(listSummariesFn), {
     authorizer: authorizer,
     authorizationType: apigateway.AuthorizationType.COGNITO
   });
   ```

2. Redeploy API Stack:
   ```bash
   cdk deploy ApiStack --profile customer-care-dev
   ```

**Validation:**
- API Gateway shows Cognito authorizer configured
- Endpoints require authentication

#### Step 9.5: Test Authentication Flow
**Tasks:**
1. Create test script (`scripts/test-auth.sh`):
   ```bash
   #!/bin/bash
   
   USER_POOL_ID="us-east-1_XXXXXXXXX"
   CLIENT_ID="XXXXXXXXXXXXXXXXXXXXXXXXXX"
   USERNAME="caseworker@example.com"
   PASSWORD="NewPassword123!"
   
   # Initiate auth
   AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
     --auth-flow USER_PASSWORD_AUTH \
     --client-id $CLIENT_ID \
     --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD \
     --query 'AuthenticationResult.[AccessToken,IdToken,RefreshToken]' \
     --output text)
   
   ACCESS_TOKEN=$(echo $AUTH_RESPONSE | cut -f1)
   ID_TOKEN=$(echo $AUTH_RESPONSE | cut -f2)
   
   echo "Access Token: $ACCESS_TOKEN"
   
   # Test API call with token
   curl -H "Authorization: Bearer $ID_TOKEN" \
     https://abc123.execute-api.us-east-1.amazonaws.com/prod/summaries
   ```

2. Run test:
   ```bash
   chmod +x scripts/test-auth.sh
   ./scripts/test-auth.sh
   ```

**Validation:**
- Authentication succeeds
- Token received
- API call with token succeeds
- API call without token returns 401 Unauthorized

**Outputs from Stage 9:**
- ✓ Cognito User Pool created
- ✓ User groups configured
- ✓ Test users created
- ✓ API Gateway integrated with Cognito
- ✓ Authentication flow tested successfully
- ✓ User Pool ID and Client ID noted

---

## Stage 10: Real-Time Notification System

### Duration: 2 days

### Objectives
- Create WebSocket API
- Implement connection management
- Implement notification Lambda
- Test real-time notifications

### Steps

#### Step 10.1: Create WebSocket API
**Tasks:**
1. Create WebSocket Stack (`lib/stacks/websocket-stack.ts`):
   ```typescript
   import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
   import * as integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
   
   export class WebSocketStack extends cdk.Stack {
     public readonly webSocketApi: apigatewayv2.CfnApi;
     
     constructor(scope: Construct, id: string, props) {
       super(scope, id, props);
       
       // Connection Lambda
       const connectFn = new lambda.Function(/*...*/);
       const disconnectFn = new lambda.Function(/*...*/);
       const defaultFn = new lambda.Function(/*...*/);
       
       // WebSocket API
       this.webSocketApi = new apigatewayv2.CfnApi(this, 'CustomerCareWebSocket', {
         name: 'customer-care-websocket',
         protocolType: 'WEBSOCKET',
         routeSelectionExpression: '$request.body.action'
       });
       
       // Routes
       // $connect, $disconnect, $default
     }
   }
   ```

**Validation:**
- CDK synth succeeds

#### Step 10.2: Implement Connection Management
**Tasks:**
1. **Connect Lambda** (`lambdas/websocket-connect/index.py`):
   ```python
   import boto3
   import json
   from datetime import datetime, timedelta
   
   dynamodb = boto3.resource('dynamodb')
   cognito = boto3.client('cognito-idp')
   
   def lambda_handler(event, context):
       """Handle WebSocket connection"""
       
       connection_id = event['requestContext']['connectionId']
       
       # Get token from query string
       token = event.get('queryStringParameters', {}).get('token')
       
       # Validate token with Cognito
       try:
           user_info = cognito.get_user(AccessToken=token)
           email = next(a['Value'] for a in user_info['UserAttributes'] if a['Name'] == 'email')
       except:
           return {'statusCode': 401, 'body': 'Unauthorized'}
       
       # Store connection
       table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])
       ttl = int((datetime.now() + timedelta(hours=24)).timestamp())
       
       table.put_item(Item={
           'connectionId': connection_id,
           'user_id': user_info['Username'],
           'email': email,
           'connected_at': datetime.now().isoformat(),
           'ttl': ttl
       })
       
       return {'statusCode': 200, 'body': 'Connected'}
   ```

2. **Disconnect Lambda** (`lambdas/websocket-disconnect/index.py`):
   ```python
   def lambda_handler(event, context):
       """Handle WebSocket disconnection"""
       
       connection_id = event['requestContext']['connectionId']
       
       table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])
       table.delete_item(Key={'connectionId': connection_id})
       
       return {'statusCode': 200, 'body': 'Disconnected'}
   ```

**Validation:**
- Lambda functions written

#### Step 10.3: Implement Notification Lambda
**Tasks:**
1. Create Notification Lambda (`lambdas/websocket-notify/index.py`):
   ```python
   import boto3
   import json
   
   dynamodb = boto3.resource('dynamodb')
   apigateway_management = boto3.client('apigatewaymanagementapi')
   
   def lambda_handler(event, context):
       """Send notification to connected clients"""
       
       summary_data = event.get('summary', {})
       call_id = event.get('call_id')
       
       # Get all active connections
       connections_table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])
       response = connections_table.scan()
       connections = response['Items']
       
       # Prepare message
       message = {
           'type': 'NEW_SUMMARY',
           'data': {
               'call_id': call_id,
               'issue_sentence': summary_data.get('issue_sentence'),
               'sentiment': summary_data.get('sentiment'),
               'timestamp': summary_data.get('timestamp')
           }
       }
       
       # Send to all connections
       for connection in connections:
           try:
               apigateway_management.post_to_connection(
                   ConnectionId=connection['connectionId'],
                   Data=json.dumps(message)
               )
           except:
               # Connection stale, delete it
               connections_table.delete_item(
                   Key={'connectionId': connection['connectionId']}
               )
       
       return {'statusCode': 200}
   ```

**Validation:**
- Notification Lambda written

#### Step 10.4: Deploy WebSocket Stack
**Tasks:**
1. Deploy:
   ```bash
   cdk deploy WebSocketStack --profile customer-care-dev
   ```

2. Note WebSocket URL from output (e.g., `wss://xyz789.execute-api.us-east-1.amazonaws.com/prod`)

**Validation:**
- WebSocket API deployed
- URL accessible

#### Step 10.5: Test WebSocket Connection
**Tasks:**
1. Create test script (`scripts/test-websocket.py`):
   ```python
   import asyncio
   import websockets
   import json
   
   async def test_connection():
       token = "YOUR_ACCESS_TOKEN"
       uri = f"wss://xyz789.execute-api.us-east-1.amazonaws.com/prod?token={token}"
       
       async with websockets.connect(uri) as websocket:
           print("Connected!")
           
           # Listen for messages
           async for message in websocket:
               print(f"Received: {message}")
   
   asyncio.run(test_connection())
   ```

2. Run test:
   ```bash
   pip install websockets
   python scripts/test-websocket.py
   ```

3. Trigger notification by processing a test call

**Validation:**
- WebSocket connection established
- Message received when call processing completes
- Connection persists until manually closed

**Outputs from Stage 10:**
- ✓ WebSocket API deployed
- ✓ Connection management working
- ✓ Notification Lambda integrated
- ✓ Real-time notifications tested
- ✓ WebSocket URL noted

---

## Stage 11: Frontend Application

### Duration: 4-5 days

### Objectives
- Set up React application
- Implement authentication UI
- Implement dashboard UI
- Integrate with backend APIs
- Test user flows

### Steps

#### Step 11.1: Initialize React Project
**Tasks:**
1. Create React app with Vite:
   ```bash
   cd customer-care-frontend
   npm create vite@latest . -- --template react-ts
   npm install
   ```

2. Install dependencies:
   ```bash
   npm install @aws-amplify/auth axios react-router-dom@6 \
     react-query @tanstack/react-query \
     @mui/material @mui/icons-material @emotion/react @emotion/styled \
     react-hook-form date-fns react-h5-audio-player
   ```

3. Create folder structure:
   ```bash
   mkdir -p src/{components,services,hooks,contexts,types,utils,routes}
   mkdir -p src/components/{Auth,Dashboard,Layout,Common}
   ```

**Validation:**
- Project initializes
- npm install completes
- Can run `npm run dev`

#### Step 11.2: Configure Environment Variables
**Tasks:**
1. Create `.env` file:
   ```
   VITE_API_BASE_URL=https://abc123.execute-api.us-east-1.amazonaws.com/prod
   VITE_WEBSOCKET_URL=wss://xyz789.execute-api.us-east-1.amazonaws.com/prod
   VITE_USER_POOL_ID=us-east-1_XXXXXXXXX
   VITE_USER_POOL_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
   VITE_REGION=us-east-1
   ```

**Validation:**
- Environment variables accessible via `import.meta.env`

#### Step 11.3: Implement Authentication
**Tasks:**
1. Configure Amplify (`src/services/auth.ts`):
   ```typescript
   import { Amplify } from 'aws-amplify';
   
   Amplify.configure({
     Auth: {
       region: import.meta.env.VITE_REGION,
       userPoolId: import.meta.env.VITE_USER_POOL_ID,
       userPoolWebClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID
     }
   });
   ```

2. Create Auth context (`src/contexts/AuthContext.tsx`):
   ```typescript
   import React, { createContext, useState, useEffect } from 'react';
   import { Auth } from '@aws-amplify/auth';
   
   export const AuthContext = createContext(null);
   
   export const AuthProvider = ({ children }) => {
     const [user, setUser] = useState(null);
     const [loading, setLoading] = useState(true);
     
     useEffect(() => {
       checkUser();
     }, []);
     
     const checkUser = async () => {
       try {
         const currentUser = await Auth.currentAuthenticatedUser();
         setUser(currentUser);
       } catch {
         setUser(null);
       } finally {
         setLoading(false);
       }
     };
     
     const login = async (email, password) => {
       const user = await Auth.signIn(email, password);
       setUser(user);
     };
     
     const logout = async () => {
       await Auth.signOut();
       setUser(null);
     };
     
     return (
       <AuthContext.Provider value={{ user, login, logout, loading }}>
         {children}
       </AuthContext.Provider>
     );
   };
   ```

3. Create Login component (`src/components/Auth/Login.tsx`)

4. Create Protected Route component

**Validation:**
- Can log in with test user
- Token stored correctly
- Protected routes redirect to login

#### Step 11.4: Implement API Service Layer
**Tasks:**
1. Create API client (`src/services/api.ts`):
   ```typescript
   import axios from 'axios';
   import { Auth } from '@aws-amplify/auth';
   
   const api = axios.create({
     baseURL: import.meta.env.VITE_API_BASE_URL
   });
   
   // Add auth token to requests
   api.interceptors.request.use(async (config) => {
     const session = await Auth.currentSession();
     const token = session.getIdToken().getJwtToken();
     config.headers.Authorization = `Bearer ${token}`;
     return config;
   });
   
   export const summariesApi = {
     list: (params) => api.get('/summaries', { params }),
     getById: (callId) => api.get(`/summaries/${callId}`),
     getAudioUrl: (callId) => api.get(`/summaries/${callId}/audio`),
     getTranscript: (callId) => api.get(`/summaries/${callId}/transcript`)
   };
   ```

**Validation:**
- API calls include auth token
- Can fetch data from backend

#### Step 11.5: Implement Dashboard Components
**Tasks:**
1. Create Summary List component (`src/components/Dashboard/SummaryList.tsx`):
   - Display grid/table of summaries
   - Implement filters
   - Implement pagination
   - Add loading states

2. Create Summary Detail component (`src/components/Dashboard/SummaryDetail.tsx`):
   - Display full summary
   - Embed audio player
   - Show transcript

3. Create Audio Player component

4. Implement status badges

**Validation:**
- Components render correctly
- Data displays from API
- Navigation works

#### Step 11.6: Implement WebSocket Integration
**Tasks:**
1. Create WebSocket hook (`src/hooks/useWebSocket.ts`):
   ```typescript
   import { useEffect, useRef, useState } from 'react';
   import { Auth } from '@aws-amplify/auth';
   
   export const useWebSocket = (onMessage) => {
     const [status, setStatus] = useState('disconnected');
     const ws = useRef(null);
     
     useEffect(() => {
       connect();
       return () => disconnect();
     }, []);
     
     const connect = async () => {
       const session = await Auth.currentSession();
       const token = session.getAccessToken().getJwtToken();
       const url = `${import.meta.env.VITE_WEBSOCKET_URL}?token=${token}`;
       
       ws.current = new WebSocket(url);
       
       ws.current.onopen = () => setStatus('connected');
       ws.current.onclose = () => {
         setStatus('disconnected');
         setTimeout(connect, 5000); // Reconnect after 5s
       };
       ws.current.onmessage = (event) => {
         const data = JSON.parse(event.data);
         onMessage(data);
       };
     };
     
     const disconnect = () => {
       if (ws.current) ws.current.close();
     };
     
     return { status };
   };
   ```

2. Integrate in Dashboard component

**Validation:**
- WebSocket connects on login
- Receives notifications
- Reconnects on disconnect
- List updates in real-time

#### Step 11.7: Build and Test Frontend
**Tasks:**
1. Build for production:
   ```bash
   npm run build
   ```

2. Test locally:
   ```bash
   npm run dev
   ```

3. Test user flows:
   - Login flow
   - View summary list
   - Filter and search
   - View summary detail
   - Play audio
   - Real-time notification

**Validation:**
- Build succeeds
- All user flows work
- No console errors
- Responsive on mobile/tablet

**Outputs from Stage 11:**
- ✓ React application built
- ✓ Authentication integrated
- ✓ Dashboard implemented
- ✓ WebSocket notifications working
- ✓ All user flows tested

---

## Stage 12: Monitoring and Observability

### Duration: 1-2 days

### Objectives
- Create CloudWatch dashboards
- Configure alarms
- Set up SNS notifications
- Test alerting

### Steps

#### Step 12.1: Create CloudWatch Dashboards
**Tasks:**
1. Create Monitoring Stack (`lib/stacks/monitoring-stack.ts`):
   ```typescript
   import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
   
   export class MonitoringStack extends cdk.Stack {
     constructor(scope: Construct, id: string, props) {
       super(scope, id, props);
       
       // Dashboard 1: Processing Pipeline
       const processingDashboard = new cloudwatch.Dashboard(this, 'ProcessingDashboard', {
         dashboardName: 'customer-care-processing'
       });
       
       // Add widgets for:
       // - Calls uploaded per hour
       // - Processing time (P50, P95, P99)
       // - Success/failure rates
       // - Step Functions execution metrics
       
       // Dashboard 2: API Performance
       // Dashboard 3: Cost Tracking
     }
   }
   ```

**Validation:**
- CDK synth succeeds

#### Step 12.2: Configure CloudWatch Alarms
**Tasks:**
1. Add alarms to Monitoring Stack:
   ```typescript
   // Critical: Step Function failure rate
   const sfnFailureAlarm = new cloudwatch.Alarm(this, 'SfnFailureAlarm', {
     metric: stateMachine.metricFailed(),
     threshold: 10,
     evaluationPeriods: 1,
     datapointsToAlarm: 1,
     comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
   });
   
   // Critical: API Gateway 5xx errors
   // Warning: Average processing time
   // etc.
   ```

**Validation:**
- Alarms defined

#### Step 12.3: Set Up SNS Notifications
**Tasks:**
1. Create SNS topic:
   ```typescript
   const alarmTopic = new sns.Topic(this, 'AlarmTopic', {
     displayName: 'Customer Care Alarms'
   });
   
   alarmTopic.addSubscription(
     new subscriptions.EmailSubscription('team@example.com')
   );
   ```

2. Link alarms to topic:
   ```typescript
   sfnFailureAlarm.addAlarmAction(new actions.SnsAction(alarmTopic));
   ```

**Validation:**
- SNS topic created
- Email subscription confirmed

#### Step 12.4: Deploy Monitoring Stack
**Tasks:**
1. Deploy:
   ```bash
   cdk deploy MonitoringStack --profile customer-care-dev
   ```

**Validation:**
- Dashboards visible in CloudWatch console
- Alarms active

#### Step 12.5: Test Alerting
**Tasks:**
1. Trigger test alarm:
   - Force Step Functions failure
   - Wait for alarm state change
   - Verify email notification received

**Validation:**
- Alarm triggers correctly
- Notification received within 5 minutes
- Alarm provides actionable information

**Outputs from Stage 12:**
- ✓ CloudWatch dashboards created
- ✓ Alarms configured
- ✓ SNS notifications set up
- ✓ Alerting tested

---

## Stage 13: Security Hardening

### Duration: 1-2 days

### Objectives
- Enable encryption everywhere
- Configure WAF rules
- Enable CloudTrail
- Run security audit

### Steps

#### Step 13.1: Enable Encryption
**Tasks:**
1. Verify S3 encryption enabled (done in Stage 3)
2. Verify DynamoDB encryption enabled (done in Stage 3)
3. Verify Secrets Manager encryption enabled (done in Stage 4)
4. Enable CloudWatch Logs encryption:
   ```bash
   aws logs associate-kms-key \
     --log-group-name /aws/lambda/webhook-handler \
     --kms-key-id arn:aws:kms:us-east-1:123456789012:key/XXXXXXXX \
     --profile customer-care-dev
   ```

**Validation:**
- All data encrypted at rest
- All communications use TLS

#### Step 13.2: Configure AWS WAF
**Tasks:**
1. Create WAF WebACL:
   ```bash
   aws wafv2 create-web-acl \
     --name customer-care-waf \
     --scope REGIONAL \
     --default-action Allow={} \
     --rules file://waf-rules.json \
     --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=CustomerCareWAF \
     --profile customer-care-dev
   ```

2. Associate with API Gateway

**Validation:**
- WAF rules active
- Rate limiting configured

#### Step 13.3: Enable CloudTrail
**Tasks:**
1. Create trail:
   ```bash
   aws cloudtrail create-trail \
     --name customer-care-audit-trail \
     --s3-bucket-name customer-care-cloudtrail-logs \
     --is-multi-region-trail \
     --profile customer-care-dev
   
   aws cloudtrail start-logging \
     --name customer-care-audit-trail \
     --profile customer-care-dev
   ```

**Validation:**
- CloudTrail logging active
- Logs being written to S3

#### Step 13.4: Run Security Audit
**Tasks:**
1. Run AWS Security Hub assessment (if enabled)
2. Run IAM Access Analyzer
3. Review security group rules
4. Review S3 bucket policies
5. Check for overly permissive IAM policies

**Validation:**
- No critical findings
- Security best practices followed

**Outputs from Stage 13:**
- ✓ Encryption enabled everywhere
- ✓ WAF configured
- ✓ CloudTrail enabled
- ✓ Security audit completed
- ✓ All critical findings resolved

---

## Stage 14: Testing and Validation

### Duration: 2-3 days

### Objectives
- Run end-to-end tests
- Perform load testing
- Validate all acceptance criteria
- Document test results

### Steps

#### Step 14.1: End-to-End Testing
**Tasks:**
1. Upload test audio file
2. Verify processing completes successfully
3. Verify summary appears in dashboard
4. Verify real-time notification received
5. Test audio playback
6. Test transcript viewing

**Validation:**
- All steps complete without errors
- Processing time < 5 minutes
- Data accuracy verified

#### Step 14.2: Load Testing
**Tasks:**
1. Create load test script (`scripts/load-test.py`):
   ```python
   import boto3
   import concurrent.futures
   from datetime import datetime
   
   def upload_test_file(file_num):
       # Upload to Google Drive
       # Wait for processing
       # Verify completion
       pass
   
   # Test with 100 concurrent uploads
   with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
       futures = [executor.submit(upload_test_file, i) for i in range(100)]
       concurrent.futures.wait(futures)
   ```

2. Run load test:
   ```bash
   python scripts/load-test.py
   ```

3. Monitor CloudWatch metrics during test

**Validation:**
- System handles 100 concurrent calls
- No throttling errors
- Processing time remains < 5 minutes (P95)
- No Lambda timeouts

#### Step 14.3: Security Testing
**Tasks:**
1. Test unauthorized access:
   - API calls without token → 401
   - Invalid tokens → 401
   - Expired tokens → 401

2. Test CORS:
   - Allowed origins work
   - Disallowed origins blocked

3. Test SQL injection attempts (should fail safely)

**Validation:**
- All security controls working
- No vulnerabilities identified

#### Step 14.4: Browser Compatibility Testing
**Tasks:**
1. Test frontend on:
   - Chrome (latest)
   - Firefox (latest)
   - Safari (latest)
   - Edge (latest)

2. Test responsive design:
   - Desktop (1920x1080)
   - Tablet (768x1024)
   - Mobile (375x667)

**Validation:**
- Works on all browsers
- Responsive on all screen sizes
- No visual bugs

#### Step 14.5: Document Test Results
**Tasks:**
1. Create test report:
   - Test cases executed
   - Pass/fail status
   - Performance metrics
   - Issues found and resolved

**Validation:**
- Test report complete
- All tests passing
- No critical issues outstanding

**Outputs from Stage 14:**
- ✓ End-to-end tests passing
- ✓ Load testing successful
- ✓ Security testing passed
- ✓ Browser compatibility confirmed
- ✓ Test report documented

---

## Stage 15: Production Deployment

### Duration: 2-3 days

### Objectives
- Deploy to production environment
- Configure DNS and SSL
- Run smoke tests
- Go live

### Steps

#### Step 15.1: Prepare Production Environment
**Tasks:**
1. Create production AWS account (if using multi-account)
2. Bootstrap CDK in production:
   ```bash
   cdk bootstrap aws://PROD-ACCOUNT-ID/us-east-1 --profile customer-care-prod
   ```

3. Create production configuration:
   - Update CDK context for prod
   - Set production environment variables
   - Configure production secrets

**Validation:**
- Production account ready
- Configuration reviewed

#### Step 15.2: Deploy All Stacks to Production
**Tasks:**
1. Deploy in order:
   ```bash
   cdk deploy StorageStack --profile customer-care-prod
   cdk deploy AuthStack --profile customer-care-prod
   cdk deploy ApiStack --profile customer-care-prod
   cdk deploy ProcessingStack --profile customer-care-prod
   cdk deploy WebSocketStack --profile customer-care-prod
   cdk deploy MonitoringStack --profile customer-care-prod
   ```

2. Verify all stacks deployed successfully

**Validation:**
- All stacks show CREATE_COMPLETE
- No deployment errors

#### Step 15.3: Configure DNS and SSL
**Tasks:**
1. Register domain or use existing (e.g., customercare.yourdomain.com)

2. Create ACM certificate:
   ```bash
   aws acm request-certificate \
     --domain-name customercare.yourdomain.com \
     --validation-method DNS \
     --profile customer-care-prod
   ```

3. Validate certificate via DNS

4. Configure custom domain for API Gateway:
   ```bash
   aws apigateway create-domain-name \
     --domain-name api.customercare.yourdomain.com \
     --certificate-arn arn:aws:acm:us-east-1:ACCOUNT:certificate/XXXXX \
     --endpoint-configuration types=REGIONAL \
     --profile customer-care-prod
   ```

5. Create Route53 records pointing to API Gateway and CloudFront (for frontend)

**Validation:**
- SSL certificate validated
- DNS resolves correctly
- HTTPS working

#### Step 15.4: Deploy Frontend to Production
**Tasks:**
1. Build production frontend:
   ```bash
   cd customer-care-frontend
   npm run build
   ```

2. Deploy to AWS Amplify or S3 + CloudFront:
   ```bash
   aws s3 sync dist/ s3://customercare-frontend-prod --profile customer-care-prod
   aws cloudfront create-invalidation --distribution-id XXXXX --paths "/*" --profile customer-care-prod
   ```

**Validation:**
- Frontend accessible via production URL
- All features working

#### Step 15.5: Run Production Smoke Tests
**Tasks:**
1. Upload test call
2. Verify processing completes
3. Login to dashboard
4. Verify summary appears
5. Test all critical user flows

**Validation:**
- All smoke tests pass
- No errors in production logs

#### Step 15.6: Go Live
**Tasks:**
1. Create production users in Cognito
2. Send credentials to users
3. Notify team of go-live
4. Monitor system for first 24 hours

**Validation:**
- Users can log in
- System stable
- No critical issues

#### Step 15.7: Post-Launch Monitoring
**Tasks:**
1. Monitor CloudWatch dashboards
2. Review logs for errors
3. Check cost metrics
4. Gather user feedback

**Validation:**
- System healthy
- Users satisfied
- Costs within budget

**Outputs from Stage 15:**
- ✓ Production environment deployed
- ✓ DNS and SSL configured
- ✓ Frontend deployed
- ✓ Smoke tests passed
- ✓ System live and stable
- ✓ Post-launch monitoring active

---

## Post-Deployment Checklist

### Week 1 - Hypercare
- [ ] Daily dashboard reviews
- [ ] Monitor all CloudWatch alarms
- [ ] Respond to user feedback immediately
- [ ] Track processing times and success rates
- [ ] Adjust configurations as needed
- [ ] Document lessons learned

### Month 1 - Stabilization
- [ ] Weekly monitoring reviews
- [ ] First cost optimization review
- [ ] User satisfaction survey
- [ ] Feature enhancement planning
- [ ] Performance tuning based on real usage

### Ongoing Maintenance
- [ ] Monthly system health reviews
- [ ] Quarterly capacity planning
- [ ] Quarterly security audits
- [ ] Annual disaster recovery testing
- [ ] Regular dependency updates
- [ ] Continuous improvement initiatives

---

*Document Version: 1.0*  
*Last Updated: January 31, 2026*  
*For questions, contact: Platform Team*
