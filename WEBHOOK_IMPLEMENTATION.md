# Google Drive to AWS S3: Webhook Implementation Guide

## Overview

This comprehensive guide provides step-by-step instructions for implementing a real-time data pipeline from Google Drive to AWS S3 using webhooks, including detailed prerequisite setup, channel renewal management, and custom validation checks.

**Total Implementation Time: 3-5 days**

Whether you're new to cloud development or an experienced engineer, this guide will walk you through every step needed to build a production-ready webhook pipeline.

---

## Table of Contents

1. [Architecture](#1-architecture)
2. [Prerequisites and Environment Setup](#2-prerequisites-and-environment-setup) ⏱️ 1-2 days
   - 2.1 [Development Tools Installation](#21-development-tools-installation)
   - 2.2 [Version Control Setup](#22-version-control-setup)
   - 2.3 [Local Development Environment](#23-local-development-environment)
3. [Google Cloud Platform Setup](#3-google-cloud-platform-setup) ⏱️ 1 day
   - 3.1 [Create Google Cloud Project](#31-create-google-cloud-project)
   - 3.2 [Enable Google Drive API](#32-enable-google-drive-api)
   - 3.3 [Create Service Account](#33-create-service-account)
   - 3.4 [Generate and Secure Service Account Key](#34-generate-and-secure-service-account-key)
   - 3.5 [Create and Share Google Drive Folder](#35-create-and-share-google-drive-folder)
   - 3.6 [Test Service Account Access](#36-test-service-account-access)
4. [Channel Management](#4-channel-management) ⏱️ 4-6 hours
5. [Webhook Handler Implementation](#5-webhook-handler-validate-fetch-upload) ⏱️ 4-6 hours
6. [Custom Checks Summary](#6-custom-checks-summary)
7. [Infrastructure as Code (Terraform)](#7-infrastructure-as-code-terraform) ⏱️ 2-3 hours
8. [Monitoring & Alerts](#8-monitoring--alerts) ⏱️ 1-2 hours
9. [Deployment Checklist](#9-deployment-checklist)
10. [Testing](#10-testing) ⏱️ 2-3 hours
11. [Troubleshooting Common Issues](#11-troubleshooting-common-issues)
12. [Summary](#12-summary)

---

## 1. Architecture

```
┌─────────────────────────────────────┐
│     Google Drive                    │
│  (Files created/modified)           │
└────────────────┬────────────────────┘
                 │
                 │ Webhook notification
                 │ (URL + change token)
                 ▼
         ┌───────────────────┐
         │  API Gateway      │
         │  /webhook         │
         └──────────┬────────┘
                    │
                    ▼
        ┌──────────────────────┐
        │  Lambda: Webhook     │
        │  Handler             │
        │  ┌──────────────────┐│
        │  │1. Validate sig   ││
        │  │2. Extract token  ││
        │  │3. Query changes  ││
        │  │4. Fetch files    ││
        │  │5. Upload to S3   ││
        │  │6. Log success    ││
        │  └──────────────────┘│
        └──────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
    ┌─────────┐         ┌─────────────┐
    │AWS S3   │         │DynamoDB     │
    │(Data)   │         │(State)      │
    └─────────┘         └─────────────┘
        ▲
        │
    ┌───┴────────────────────────┐
    │  Lambda: Channel Renewal    │
    │  (Scheduled every 12h)      │
    │  ┌───────────────────────┐  │
    │  │1. Load current channel│  │
    │  │2. Check expiration    │  │
    │  │3. Renew if <6h left   │  │
    │  │4. Store new channel   │  │
    │  └───────────────────────┘  │
    └────────────────────────────┘
```

---

## 2. Prerequisites and Environment Setup

**Duration: 1-2 days**

Before diving into the implementation, we need to set up your development environment with the necessary tools and configurations. This section ensures you have everything needed to build, test, and deploy the webhook pipeline.

### 2.1 Development Tools Installation

#### Why These Tools Matter:
- **Node.js & Python**: Core runtimes for Lambda functions
- **AWS CLI & CDK**: Infrastructure management and deployment
- **Google Cloud SDK**: Interact with Google APIs
- **VS Code**: Recommended IDE with excellent cloud development support

#### 2.1.1 Install Node.js (v18 or later)

Node.js is required for AWS CDK and various development tools.

**macOS Installation:**
```bash
# Using Homebrew (recommended)
brew install node@18

# Verify installation
node --version  # Should show v18.x.x or higher
npm --version   # Should show 9.x.x or higher
```

✓ **Verification:** Run `node --version` and ensure it shows v18 or higher.

#### 2.1.2 Install Python (3.11 or later)

Python 3.11+ is used for Lambda functions and deployment scripts.

**macOS Installation:**
```bash
# Using Homebrew
brew install python@3.11

# Verify installation
python3 --version  # Should show Python 3.11.x or higher
pip3 --version     # Should show pip 23.x.x or higher
```

💡 **Tip:** Use `python3` explicitly to avoid conflicts with system Python 2.x.

✓ **Verification:** Run `python3 --version` and ensure it shows 3.11 or higher.

#### 2.1.3 Install AWS CLI (v2)

The AWS CLI enables you to interact with AWS services from the command line.

**macOS Installation:**
```bash
# Download and install AWS CLI v2
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Verify installation
aws --version  # Should show aws-cli/2.x.x
```

**Configure AWS Credentials:**
```bash
# Run configuration wizard
aws configure

# You'll be prompted for:
# AWS Access Key ID: [Your access key]
# AWS Secret Access Key: [Your secret key]
# Default region name: us-east-1 (or your preferred region)
# Default output format: json
```

⚠️ **Security Warning:** Never commit AWS credentials to version control. Store them securely in `~/.aws/credentials`.

✓ **Verification:** Run `aws sts get-caller-identity` to confirm your credentials work.

#### 2.1.4 Install AWS CDK

AWS Cloud Development Kit (CDK) allows infrastructure-as-code in familiar programming languages.

```bash
# Install AWS CDK globally
npm install -g aws-cdk

# Verify installation
cdk --version  # Should show 2.x.x or higher

# Bootstrap your AWS environment (one-time setup)
cdk bootstrap aws://ACCOUNT-ID/REGION
```

💡 **Tip:** Replace `ACCOUNT-ID` with your AWS account ID and `REGION` with your preferred region (e.g., us-east-1).

✓ **Verification:** Run `cdk --version` to confirm installation.

#### 2.1.5 Install Google Cloud SDK

The Google Cloud SDK provides tools to interact with Google Cloud services.

**macOS Installation:**
```bash
# Download and install Google Cloud SDK
curl https://sdk.cloud.google.com | bash

# Restart shell
exec -l $SHELL

# Initialize and authenticate
gcloud init

# This will:
# 1. Open browser for Google account authentication
# 2. Let you select or create a project
# 3. Set default compute region/zone

# Verify installation and authentication
gcloud --version  # Should show Google Cloud SDK version
gcloud auth list   # Should show your authenticated account
```

⚠️ **Note:** If you only want to authenticate without full setup, use `gcloud auth login` instead.

✓ **Verification:** Run `gcloud config get-value project` to see your active project.

#### 2.1.6 Install Visual Studio Code (Optional but Recommended)

VS Code provides excellent support for Python, AWS, and cloud development.

**macOS Installation:**
```bash
# Using Homebrew Cask
brew install --cask visual-studio-code

# Launch VS Code
code --version
```

**Recommended VS Code Extensions:**
```bash
# Install extensions from command line
code --install-extension ms-python.python
code --install-extension amazonwebservices.aws-toolkit-vscode
code --install-extension googlecloudtools.cloudcode
code --install-extension hashicorp.terraform
```

#### 2.1.7 Install Terraform (Optional)

If you prefer Terraform over AWS CDK for infrastructure management.

```bash
# Using Homebrew
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Verify installation
terraform --version  # Should show Terraform v1.x.x
```

✓ **Verification:** Run `terraform --version` to confirm installation.

---

### 2.2 Version Control Setup

#### 2.2.1 Create GitHub Repository

If you haven't already created a repository:

```bash
# Create a new directory for your project
mkdir customer-care-call-processor
cd customer-care-call-processor

# Initialize Git repository
git init

# Create initial README
echo "# Google Drive to S3 Webhook Pipeline" > README.md

# Create .gitignore file
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# AWS
.aws/
*.pem

# Secrets (CRITICAL: Never commit these!)
*service-account*.json
secrets.json
*.env
.env.local

# IDE
.vscode/
.idea/

# Terraform
*.tfstate
*.tfstate.*
.terraform/

# Node
node_modules/
package-lock.json

# OS
.DS_Store
Thumbs.db
EOF

# Initial commit
git add .
git commit -m "Initial commit"

# Create GitHub repository (using GitHub CLI if installed)
gh repo create customer-care-call-processor --public --source=. --remote=origin

# Or manually: Create repo on github.com, then:
# git remote add origin https://github.com/YOUR-USERNAME/customer-care-call-processor.git
# git branch -M main
# git push -u origin main
```

⚠️ **Critical Security Note:** The `.gitignore` file MUST be committed before adding any sensitive files. Double-check that `*service-account*.json` is in `.gitignore` before downloading your Google service account key.

#### 2.2.2 Set Up Branch Protection (Optional but Recommended)

For production projects, enable branch protection on GitHub:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Branches**
3. Click **Add rule** for `main` branch
4. Enable:
   - ✓ Require pull request reviews before merging
   - ✓ Require status checks to pass before merging
   - ✓ Include administrators

---

### 2.3 Local Development Environment

#### 2.3.1 Create Project Structure

```bash
# Navigate to your project directory
cd customer-care-call-processor

# Create directory structure
mkdir -p src/lambda/{webhook_handler,channel_renewal}
mkdir -p terraform
mkdir -p config
mkdir -p scripts
mkdir -p tests/{unit,integration}
mkdir -p monitoring

# Create README files
touch src/lambda/webhook_handler/README.md
touch src/lambda/channel_renewal/README.md
touch terraform/README.md
```

Your project structure should now look like:
```
customer-care-call-processor/
├── .gitignore
├── README.md
├── config/
├── monitoring/
├── scripts/
├── src/
│   └── lambda/
│       ├── channel_renewal/
│       └── webhook_handler/
├── terraform/
└── tests/
    ├── integration/
    └── unit/
```

#### 2.3.2 Set Up Python Virtual Environment

Python virtual environments isolate project dependencies.

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Upgrade pip
pip install --upgrade pip

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Google Drive API
google-auth==2.23.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
google-api-python-client==2.100.0

# AWS SDK
boto3==1.28.85
botocore==1.31.85

# Utilities
requests==2.31.0
python-dateutil==2.8.2

# Development & Testing
pytest==7.4.3
pytest-mock==3.12.0
pytest-cov==4.1.0
moto==4.2.5  # AWS service mocking
black==23.10.0  # Code formatting
flake8==6.1.0  # Linting
mypy==1.6.1  # Type checking
EOF

# Install dependencies
pip install -r requirements.txt
```

💡 **Why Virtual Environments?** They prevent dependency conflicts between projects and make deployment packages cleaner.

✓ **Verification:** Run `pip list` and verify all packages are installed.

#### 2.3.3 Create Development Configuration File

```bash
# Create config/dev.yaml
cat > config/dev.yaml << 'EOF'
# Development Configuration
# DO NOT commit sensitive values - use environment variables or AWS Secrets Manager

google_drive:
  folder_id: "REPLACE_WITH_YOUR_FOLDER_ID"
  service_account_secret: "google-drive-service-account-dev"

aws:
  region: "us-east-1"
  s3_bucket: "gdrive-s3-pipeline-dev-RANDOM_SUFFIX"
  dynamodb_table_channels: "gdrive_channels_dev"
  dynamodb_table_sync_log: "gdrive_s3_sync_log_dev"

webhook:
  token: "REPLACE_WITH_RANDOM_TOKEN"  # Generate with: openssl rand -hex 32
  url: "https://REPLACE_AFTER_API_GATEWAY_DEPLOYMENT.execute-api.us-east-1.amazonaws.com/prod/webhook"

monitoring:
  alert_email: "your-email@example.com"
  enable_debug_logging: true
EOF
```

⚠️ **Security Note:** This file can be committed to Git as it contains placeholders. Replace values during deployment using environment variables or AWS Secrets Manager.

---

### 2.3.4 Validation Checklist

Before proceeding to Google Cloud setup, verify all tools are installed:

✓ **Run these verification commands:**
```bash
# Check all required tools
echo "Node.js: $(node --version)"
echo "NPM: $(npm --version)"
echo "Python: $(python3 --version)"
echo "Pip: $(pip3 --version)"
echo "AWS CLI: $(aws --version)"
echo "AWS CDK: $(cdk --version)"
echo "Google Cloud SDK: $(gcloud --version | head -n 1)"

# Check AWS credentials
aws sts get-caller-identity

# Check Google Cloud authentication
gcloud auth list

# Check virtual environment
which python  # Should point to venv/bin/python
pip list | grep -E "(google-api|boto3)"  # Should show installed packages
```

If all commands succeed, you're ready to proceed! 🎉

---

## 3. Google Cloud Platform Setup

**Duration: 1 day**

In this section, we'll set up Google Cloud Platform to enable your application to access Google Drive programmatically. We'll create a service account (a special type of account for applications, not humans) and grant it access to a specific Google Drive folder.

### 3.1 Create Google Cloud Project

Google Cloud projects are containers that organize your cloud resources. Think of it as a workspace for your application.

#### Step-by-Step Instructions:

1. **Navigate to Google Cloud Console**
   - Open your browser and go to: [https://console.cloud.google.com](https://console.cloud.google.com)
   - Sign in with your Google account

2. **Create a New Project**
   - Click the project dropdown at the top of the page (next to "Google Cloud")
   - Click **"New Project"** button
   
3. **Configure Project Details**
   - **Project Name**: `customer-care-call-processor`
   - **Project ID**: `gdrive-s3-pipeline-XXXXX` (auto-generated, but you can customize)
     - 💡 **Tip:** Project IDs must be globally unique across all Google Cloud
     - 💡 **Tip:** Write down your Project ID - you'll need it later!
   - **Organization**: Select your organization (or leave as "No organization")
   - **Location**: Select your organization or leave default
   
4. **Create the Project**
   - Click **"Create"** button
   - Wait 10-30 seconds for project creation (you'll see a notification)

5. **Verify Project Creation**
   - Ensure the new project is selected in the project dropdown
   - The dashboard should show your project name

6. **Add Environment Tag to Project** (required by Google Cloud)
   
   **Option A: Using Google Cloud Console (Recommended)**
   
   1. In Google Cloud Console, go to **"IAM & Admin"** → **"Tags"**
   2. If `environment` tag key doesn't exist:
      - Click **"Create Tag Key"**
      - Enter: `environment`
      - Click **"Create"**
   3. Select the `environment` key
   4. Click **"Create Tag Value"** or **"Manage tag values"**
   5. Enter value: `Development` (or Test, Staging, Production)
   6. Go to **"Manage Resources"** and select your project
   7. In the right panel, click **"Tags"**
   8. Select `environment` tag with value `Development`
   9. Click **"Update"**
   
   **Option B: Using gcloud CLI** (requires tag key to exist first)
   
   ```bash
   gcloud resource-manager tags bindings create \
     --tag-value=tagValues/TAGVALUE_ID \
     --parent=//cloudresourcemanager.googleapis.com/projects/gdrive-s3-pipeline-XXXXX
   ```
   > See [Attaching tags to resources](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#attaching) for the full command reference.
   > See [Listing tags](https://cloud.google.com/resource-manager/docs/tags/tags-creating-and-managing#listing_tags) for how to find your tag key and value IDs.
   
   **Tag Values:**
   - `Development` - Development/testing environments
   - `Test` - QA and testing environments
   - `Staging` - Pre-production staging
   - `Production` - Production environments

✓ **Verification:** 
```bash
# First, authenticate if you haven't already
gcloud auth login  # Opens browser for authentication

# Set your project
gcloud config set project gdrive-s3-pipeline-XXXXX  # Use your actual project ID

# Verify project exists
gcloud projects describe gdrive-s3-pipeline-XXXXX

# Verify tag was created
gcloud resource-manager tags bindings list --parent=//cloudresourcemanager.googleapis.com/projects/gdrive-s3-pipeline-XXXXX
```

**Note:** If you get "You do not currently have an active account selected", run `gcloud auth login` first.

⏱️ **Time Required:** 5 minutes

---

### 3.2 Enable Google Drive API

APIs must be explicitly enabled in Google Cloud projects. This controls which services your project can access and helps with billing.

#### Step-by-Step Instructions:

1. **Navigate to APIs & Services**
   - In Google Cloud Console, click the hamburger menu (☰) in the top-left
   - Select **"APIs & Services"** → **"Library"**

2. **Search for Google Drive API**
   - In the search bar, type: `Google Drive API`
   - Click on **"Google Drive API"** from the search results
   
3. **Enable the API**
   - Click the blue **"Enable"** button
   - Wait 10-20 seconds for enablement
   - You should see a green checkmark with "API enabled"

4. **Verify API is Enabled**
   - Navigate to **"APIs & Services"** → **"Dashboard"**
   - You should see "Google Drive API" listed under "Enabled APIs"

✓ **Verification:**
```bash
# Using gcloud CLI
gcloud services list --enabled --filter="name:drive.googleapis.com"

# Expected output:
# NAME                    TITLE
# drive.googleapis.com    Google Drive API
```

💡 **Why Enable APIs?** Google Cloud uses explicit enablement to:
- Control which services incur charges
- Improve security by limiting access
- Provide usage metrics per API

⏱️ **Time Required:** 3 minutes

---

### 3.3 Create Service Account

Service accounts are special Google accounts designed for applications (not humans). They allow your Lambda functions to authenticate with Google Drive without storing personal credentials.

#### Step-by-Step Instructions:

1. **Navigate to Service Accounts**
   - In Google Cloud Console, go to **"IAM & Admin"** → **"Service Accounts"**
   - Or use direct link: [https://console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)

2. **Create Service Account**
   - Click **"+ CREATE SERVICE ACCOUNT"** at the top
   
3. **Configure Service Account Details (Step 1 of 3)**
   - **Service account name**: `gdrive-s3-pipeline-sa`
     - This is a human-readable name
   - **Service account ID**: `gdrive-s3-pipeline-sa` (auto-filled)
     - This becomes part of the email address
   - **Service account description**: `Service account for Google Drive to S3 webhook pipeline`
   - Click **"CREATE AND CONTINUE"**

4. **Grant Permissions (Step 2 of 3)**
   - **Important:** Skip this step by clicking **"CONTINUE"**
   - 💡 **Why skip?** We'll grant permissions directly on the Google Drive folder, not at the project level. This follows the principle of least privilege.

5. **Grant Users Access (Step 3 of 3)**
   - **Important:** Skip this step by clicking **"DONE"**
   - This would allow other users to impersonate this service account - not needed for our use case

6. **Verify Service Account Created**
   - You should see your new service account in the list
   - The email will look like: `gdrive-s3-pipeline-sa@gdrive-s3-pipeline-XXXXX.iam.gserviceaccount.com`
   - **📝 Copy this email address** - you'll need it to share the Google Drive folder

✓ **Verification:**
```bash
# List service accounts
gcloud iam service-accounts list

# Expected output should include:
# DISPLAY NAME              EMAIL                                                          DISABLED
# gdrive-s3-pipeline-sa     gdrive-s3-pipeline-sa@PROJECT-ID.iam.gserviceaccount.com      False
```

💡 **Key Concept:** Service accounts authenticate using cryptographic keys (not passwords). We'll create this key in the next step.

⏱️ **Time Required:** 5 minutes

---

### 3.4 Generate and Secure Service Account Key

The service account key is a JSON file containing credentials that allow your application to authenticate as the service account. This is the most critical security step in the entire setup.

#### Step-by-Step Instructions:

1. **Navigate to Your Service Account**
   - In **"IAM & Admin"** → **"Service Accounts"**, click on the service account you just created
   - Or click the email address: `gdrive-s3-pipeline-sa@...`

2. **Open Keys Tab**
   - Click the **"KEYS"** tab at the top
   - You should see "No keys" initially

3. **Create New Key**
   - Click **"ADD KEY"** → **"Create new key"**
   
4. **Select Key Type**
   - Choose **"JSON"** (recommended)
   - Click **"CREATE"**

5. **Download and Secure the Key**
   - The JSON key file will automatically download to your computer
   - **Default filename:** `gdrive-s3-pipeline-XXXXX-xxxxxxxxx.json`
   - **Move it immediately to a secure location:**
     ```bash
     # Move to your project directory (which is in .gitignore)
     mv ~/Downloads/gdrive-s3-pipeline-*.json ~/customer-care-call-processor/service-account-key.json
     
     # Set restrictive permissions
     chmod 600 ~/customer-care-call-processor/service-account-key.json
     ```

⚠️ **CRITICAL SECURITY WARNINGS:**

1. **Never commit this file to Git:**
   ```bash
   # Verify it's in .gitignore
   grep "service-account" .gitignore
   # Should output: *service-account*.json
   
   # Double-check it won't be committed
   git status --ignored | grep service-account-key.json
   # Should show: service-account-key.json (if in ignored list)
   ```

2. **This key grants full access** to anything the service account can access. Treat it like a password!

3. **If compromised:**
   - Go to Google Cloud Console → Service Accounts → Keys
   - Delete the compromised key immediately
   - Generate a new key
   - Update your application configuration

4. **Store in AWS Secrets Manager** (recommended for production):
   ```bash
   # After AWS setup is complete, store the key securely
   aws secretsmanager create-secret \
     --name google-drive-service-account \
     --description "Service account key for Google Drive API access" \
     --secret-string file://service-account-key.json \
     --region us-east-1
   
   # Verify it's stored
   aws secretsmanager describe-secret --secret-id google-drive-service-account
   
   # Now you can delete the local file (optional but recommended)
   # rm service-account-key.json
   ```

💡 **Best Practice:** In production, never store this key in Lambda function code or environment variables. Always use AWS Secrets Manager or Parameter Store.

✓ **Verification:**
```bash
# Verify the JSON key structure
cat service-account-key.json | python3 -m json.tool | head -n 10

# Expected fields:
# - "type": "service_account"
# - "project_id": "gdrive-s3-pipeline-XXXXX"
# - "private_key_id": "..."
# - "private_key": "-----BEGIN PRIVATE KEY-----\n..."
# - "client_email": "gdrive-s3-pipeline-sa@..."
```

⏱️ **Time Required:** 5 minutes

---

### 3.5 Create and Share Google Drive Folder

Now we'll create a dedicated Google Drive folder for the pipeline and share it with the service account. This is where you'll upload files that should be synced to S3.

#### Step-by-Step Instructions:

1. **Create Google Drive Folder**
   - Go to [Google Drive](https://drive.google.com)
   - Click **"+ New"** → **"Folder"**
   - Name it: `S3 Webhook Pipeline` (or any name you prefer)
   - Click **"Create"**

2. **Get Folder ID**
   - Open the folder you just created
   - Look at the URL in your browser's address bar:
     ```
     https://drive.google.com/drive/folders/1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                            This is your Folder ID
     ```
   - **📝 Copy this Folder ID** - you'll need it for configuration
   - Example: `1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV`

3. **Share Folder with Service Account**
   - While viewing the folder, click the **"Share"** button (top-right)
   - In the "Add people and groups" field, paste your service account email:
     ```
     gdrive-s3-pipeline-sa@gdrive-s3-pipeline-XXXXX.iam.gserviceaccount.com
     ```
   - **Permission level:** Select **"Editor"**
     - 💡 **Why Editor?** Allows the service account to read files and metadata. You can use "Viewer" if you only need read access.
   - **IMPORTANT:** Uncheck **"Notify people"**
     - The service account is not a real person and can't read emails
   - Click **"Share"** or **"Send"**

4. **Verify Sharing**
   - Click the folder's **"Share"** button again
   - You should see the service account email listed with "Editor" access

✓ **Verification:**
```bash
# Update your config file with the folder ID
# Edit config/dev.yaml and replace REPLACE_WITH_YOUR_FOLDER_ID with your actual folder ID

# Test using gcloud (optional advanced verification)
# This requires setting up oauth2 - skip for now, we'll test in next section
```

💡 **Key Concept:** By sharing the folder with the service account, you're granting your application specific access to just this folder, not your entire Google Drive. This is a security best practice called "principle of least privilege."

⏱️ **Time Required:** 5 minutes

---

### 3.6 Test Service Account Access

Before proceeding with full deployment, let's verify that the service account can actually access the Google Drive folder. This early testing saves hours of debugging later!

#### Step-by-Step Test Script:

1. **Create Test Script**

Create a file called `test_google_drive_auth.py` in your project root:

```python
#!/usr/bin/env python3
"""
Test script to verify Google Drive service account access.

This script:
1. Authenticates using the service account key
2. Lists files in the specified folder
3. Verifies permissions are correctly configured

Run: python3 test_google_drive_auth.py
"""

import json
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
SERVICE_ACCOUNT_FILE = 'service-account-key.json'  # Path to your key file
FOLDER_ID = 'REPLACE_WITH_YOUR_FOLDER_ID'  # Replace with your folder ID
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def test_authentication():
    """Test 1: Verify service account can authenticate"""
    print("=" * 70)
    print("TEST 1: Authentication")
    print("=" * 70)
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        print("✓ Successfully loaded service account credentials")
        print(f"  Service Account: {credentials.service_account_email}")
        return credentials
    except FileNotFoundError:
        print(f"✗ FAILED: Service account key file not found: {SERVICE_ACCOUNT_FILE}")
        print("  Make sure you've downloaded the key and placed it in the project root.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ FAILED: Could not load credentials: {str(e)}")
        sys.exit(1)

def test_api_access(credentials):
    """Test 2: Verify Google Drive API access"""
    print("\n" + "=" * 70)
    print("TEST 2: Google Drive API Access")
    print("=" * 70)
    
    try:
        service = build('drive', 'v3', credentials=credentials)
        print("✓ Successfully connected to Google Drive API")
        return service
    except Exception as e:
        print(f"✗ FAILED: Could not connect to Google Drive API: {str(e)}")
        print("  Make sure the Google Drive API is enabled in your GCP project.")
        sys.exit(1)

def test_folder_access(service):
    """Test 3: Verify access to specific folder"""
    print("\n" + "=" * 70)
    print("TEST 3: Folder Access")
    print("=" * 70)
    
    try:
        # Get folder metadata
        folder = service.files().get(
            fileId=FOLDER_ID,
            fields='id, name, mimeType, permissions'
        ).execute()
        
        print(f"✓ Successfully accessed folder")
        print(f"  Folder ID: {folder['id']}")
        print(f"  Folder Name: {folder['name']}")
        print(f"  MIME Type: {folder['mimeType']}")
        
        return True
        
    except HttpError as e:
        if e.resp.status == 404:
            print(f"✗ FAILED: Folder not found (404)")
            print(f"  Folder ID: {FOLDER_ID}")
            print("  Possible issues:")
            print("  1. Incorrect folder ID - check the URL in Google Drive")
            print("  2. Folder not shared with service account")
            print(f"  3. Share this folder with: {credentials.service_account_email}")
        elif e.resp.status == 403:
            print(f"✗ FAILED: Permission denied (403)")
            print(f"  The service account doesn't have access to this folder.")
            print(f"  Make sure you shared the folder with: {credentials.service_account_email}")
        else:
            print(f"✗ FAILED: HTTP Error {e.resp.status}: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        sys.exit(1)

def test_list_files(service):
    """Test 4: List files in folder"""
    print("\n" + "=" * 70)
    print("TEST 4: List Files in Folder")
    print("=" * 70)
    
    try:
        # Query files in folder
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields='files(id, name, mimeType, createdTime, size)',
            pageSize=10
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            print("⚠ No files found in folder")
            print("  This is normal if you haven't uploaded any files yet.")
            print("  Try uploading a test file to the folder in Google Drive.")
        else:
            print(f"✓ Found {len(files)} file(s):")
            for idx, file in enumerate(files, 1):
                size = int(file.get('size', 0)) if 'size' in file else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                print(f"  {idx}. {file['name']}")
                print(f"     ID: {file['id']}")
                print(f"     Type: {file['mimeType']}")
                print(f"     Size: {size_mb:.2f} MB" if size > 0 else "     Size: N/A (folder or Google Doc)")
                print(f"     Created: {file['createdTime']}")
        
        return True
        
    except Exception as e:
        print(f"✗ FAILED: Could not list files: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("Google Drive Service Account Access Test")
    print("=" * 70)
    print()
    
    # Check configuration
    if FOLDER_ID == 'REPLACE_WITH_YOUR_FOLDER_ID':
        print("✗ ERROR: Please update FOLDER_ID in this script with your actual folder ID")
        print("  Find it in the Google Drive folder URL:")
        print("  https://drive.google.com/drive/folders/YOUR_FOLDER_ID")
        sys.exit(1)
    
    # Run tests
    credentials = test_authentication()
    service = test_api_access(credentials)
    test_folder_access(service)
    test_list_files(service)
    
    # Summary
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nYour service account is correctly configured and can access the folder.")
    print("You're ready to proceed with the webhook implementation!")
    print("\nNext steps:")
    print("1. Store the service account key in AWS Secrets Manager (see Section 3.4)")
    print("2. Update config/dev.yaml with your folder ID")
    print("3. Proceed to Section 4: Channel Management")

if __name__ == '__main__':
    main()
```

2. **Update Configuration**

Edit the script and replace `FOLDER_ID`:
```python
FOLDER_ID = '1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV'  # Your actual folder ID
```

3. **Run the Test**

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run test script
python3 test_google_drive_auth.py
```

4. **Expected Output (Success)**

```
======================================================================
Google Drive Service Account Access Test
======================================================================

======================================================================
TEST 1: Authentication
======================================================================
✓ Successfully loaded service account credentials
  Service Account: gdrive-s3-pipeline-sa@gdrive-s3-pipeline-XXXXX.iam.gserviceaccount.com

======================================================================
TEST 2: Google Drive API Access
======================================================================
✓ Successfully connected to Google Drive API

======================================================================
TEST 3: Folder Access
======================================================================
✓ Successfully accessed folder
  Folder ID: 1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV
  Folder Name: S3 Webhook Pipeline
  MIME Type: application/vnd.google-apps.folder

======================================================================
TEST 4: List Files in Folder
======================================================================
⚠ No files found in folder
  This is normal if you haven't uploaded any files yet.
  Try uploading a test file to the folder in Google Drive.

======================================================================
✓ ALL TESTS PASSED!
======================================================================

Your service account is correctly configured and can access the folder.
You're ready to proceed with the webhook implementation!

Next steps:
1. Store the service account key in AWS Secrets Manager (see Section 3.4)
2. Update config/dev.yaml with your folder ID
3. Proceed to Section 4: Channel Management
```

5. **Troubleshooting Failed Tests**

If TEST 1 fails:
- Verify the service account key file exists: `ls -la service-account-key.json`
- Check file permissions: `chmod 600 service-account-key.json`

If TEST 2 fails:
- Verify Google Drive API is enabled in GCP Console
- Run: `gcloud services list --enabled --filter="name:drive.googleapis.com"`

If TEST 3 fails with 404:
- Double-check the folder ID from the Google Drive URL
- Verify you're using the correct Google account

If TEST 3 fails with 403:
- Verify the folder is shared with the service account email
- Check that you granted "Editor" or "Viewer" permission
- Wait 1-2 minutes after sharing, then try again (propagation delay)

✓ **Success Criteria:** All four tests pass, and you see the "ALL TESTS PASSED!" message.

⏱️ **Time Required:** 10 minutes (including troubleshooting)

---

### 3.7 Store Configuration Securely

Now that everything is tested and working, let's store configuration securely in AWS Secrets Manager (as configured in Section 2.1.3).

```bash
# Store service account key in Secrets Manager
aws secretsmanager create-secret \
  --name google-drive-service-account \
  --description "Google Drive service account key for webhook pipeline" \
  --secret-string file://service-account-key.json \
  --region us-east-1

# Store pipeline configuration
aws secretsmanager create-secret \
  --name gdrive-s3-config \
  --description "Configuration for Google Drive to S3 pipeline" \
  --secret-string "{
    \"GOOGLE_DRIVE_FOLDER_ID\": \"YOUR_FOLDER_ID\",
    \"S3_BUCKET\": \"gdrive-s3-pipeline-dev-$(openssl rand -hex 4)\",
    \"WEBHOOK_TOKEN\": \"$(openssl rand -hex 32)\"
  }" \
  --region us-east-1

# Verify secrets are stored
aws secretsmanager list-secrets --region us-east-1 | grep gdrive
```

💡 **Security Best Practice:** Now that secrets are in AWS Secrets Manager, you can optionally delete the local `service-account-key.json` file. Your Lambda functions will retrieve it from Secrets Manager.

✓ **Section 3 Complete!** You've successfully:
- ✓ Created a Google Cloud project
- ✓ Enabled Google Drive API
- ✓ Created and configured a service account
- ✓ Generated and secured the service account key
- ✓ Created and shared a Google Drive folder
- ✓ Tested and verified service account access
- ✓ Stored secrets securely in AWS Secrets Manager

You're now ready to implement the webhook handler! 🎉

---

## 4. Channel Management

**Duration: 4-6 hours**

Google Drive webhooks use "channels" to notify your application of changes. Understanding channels is crucial for building a reliable pipeline.

### Understanding Google Drive Webhooks

- **Channel ID**: Unique identifier for your subscription to changes
- **Expiration**: Channels expire after 24 hours maximum (Google's limit)
- **Renewal**: Must renew channels before expiration to maintain continuous monitoring
- **Watch endpoint**: Requires a change token to track which changes you've already processed

💡 **Why Renewal Matters:** Without automatic renewal, your pipeline would stop receiving notifications after 24 hours, requiring manual intervention.

### DynamoDB Table for Channel State

```python
# Table: gdrive_channels
# Primary Key: folder_id (String)
# Attributes:
#   - channel_id (String)
#   - resource_id (String)
#   - expiration (Number) - Unix timestamp
#   - created_at (Number) - Unix timestamp
#   - change_token (String) - For resuming watches
#   - status (String) - active, renewing, failed
```

### Lambda Function: Create/Renew Channel

```python
import json
import boto3
import time
import uuid
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')
s3_client = boto3.client('s3')

CHANNELS_TABLE = 'gdrive_channels'
WEBHOOK_URL = 'https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod/webhook'

def get_secrets():
    """Retrieve secrets from Secrets Manager"""
    response = secrets_client.get_secret_value(
        SecretId='google-drive-service-account'
    )
    return json.loads(response['SecretString'])

def get_drive_service():
    """Authenticate and return Google Drive service"""
    secrets = get_secrets()
    creds = service_account.Credentials.from_service_account_info(
        secrets,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=creds)

def create_channel(service, folder_id):
    """Create a new Google Drive watch channel"""
    try:
        # Generate unique channel ID
        channel_id = f"gdrive-s3-{folder_id}-{uuid.uuid4()}"
        
        # Create watch request
        body = {
            'id': channel_id,
            'type': 'webhook',
            'address': WEBHOOK_URL,
            'expiration': str(int((time.time() + 86400) * 1000))  # 24 hours
        }
        
        # Start watching folder changes
        response = service.files().watch(
            fileId=folder_id,
            body=body,
            supportsAllDrives=True
        ).execute()
        
        # Store channel info in DynamoDB
        table = dynamodb.Table(CHANNELS_TABLE)
        expiration = int(time.time()) + 86400
        
        table.put_item(
            Item={
                'folder_id': folder_id,
                'channel_id': channel_id,
                'resource_id': response.get('resourceId'),
                'expiration': expiration,
                'created_at': int(time.time()),
                'status': 'active'
            }
        )
        
        print(f"✓ Channel created: {channel_id}")
        print(f"  Expires at: {datetime.fromtimestamp(expiration)}")
        
        return response
        
    except Exception as e:
        print(f"✗ Failed to create channel: {str(e)}")
        raise

def renew_channel(service, folder_id):
    """Renew an existing channel before expiration"""
    try:
        table = dynamodb.Table(CHANNELS_TABLE)
        
        # Get current channel
        response = table.get_item(Key={'folder_id': folder_id})
        
        if 'Item' not in response:
            print(f"No channel found for {folder_id}. Creating new one...")
            return create_channel(service, folder_id)
        
        current_channel = response['Item']
        expiration = current_channel['expiration']
        time_until_expiry = expiration - int(time.time())
        
        print(f"Channel expires in: {time_until_expiry / 3600:.1f} hours")
        
        # Renew if less than 6 hours remaining
        if time_until_expiry < 21600:  # 6 hours
            print("Renewing channel...")
            
            # Stop existing channel
            try:
                service.files().stop(
                    fileId=folder_id,
                    body={
                        'id': current_channel['channel_id'],
                        'resourceId': current_channel['resource_id']
                    }
                ).execute()
            except Exception as e:
                print(f"Warning: Could not stop old channel: {str(e)}")
            
            # Create new channel
            new_response = create_channel(service, folder_id)
            
            # Update status in table
            table.update_item(
                Key={'folder_id': folder_id},
                UpdateExpression='SET #status = :status, renewed_at = :renewed_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'renewed',
                    ':renewed_at': int(time.time())
                }
            )
            
            return new_response
        else:
            print(f"Channel still valid. No renewal needed.")
            return current_channel
            
    except Exception as e:
        print(f"✗ Failed to renew channel: {str(e)}")
        raise

def lambda_handler(event, context):
    """Lambda entry point for channel renewal"""
    try:
        service = get_drive_service()
        folder_id = event.get('folder_id')  # Pass from CloudWatch event
        
        if not folder_id:
            raise ValueError("folder_id not provided in event")
        
        result = renew_channel(service, folder_id)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Channel renewal check completed',
                'folder_id': folder_id
            })
        }
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### CloudWatch Rule: Trigger Renewal Every 12 Hours

```bash
# Create rule to trigger Lambda every 12 hours
aws events put-rule \
  --name gdrive-channel-renewal \
  --schedule-expression "rate(12 hours)"

# Add Lambda as target
aws events put-targets \
  --rule gdrive-channel-renewal \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:gdrive-channel-renewal","RoleArn"="arn:aws:iam::ACCOUNT:role/service-role/EventBridgeRole"
```

---

## 5. Webhook Handler: Validate, Fetch, Upload

**Duration: 4-6 hours**

This is the core of your pipeline - the Lambda function that receives webhook notifications from Google Drive, validates them, and uploads files to S3. As configured in Section 2 and Section 3, this handler uses the service account credentials stored in AWS Secrets Manager.

### Lambda Function: Process Webhook Events

```python
import json
import boto3
import hmac
import hashlib
import base64
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

S3_BUCKET = 'your-bucket-name'
WEBHOOK_TOKEN = 'your-webhook-verification-token'

def get_secrets():
    response = secrets_client.get_secret_value(
        SecretId='google-drive-service-account'
    )
    return json.loads(response['SecretString'])

def get_drive_service():
    secrets = get_secrets()
    creds = service_account.Credentials.from_service_account_info(
        secrets,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=creds)

def validate_webhook_signature(headers, body):
    """
    Validate Google Drive webhook signature.
    
    Google sends: X-Goog-Channel-Token header
    We verify it matches our token.
    """
    token = headers.get('X-Goog-Channel-Token', '')
    
    if token != WEBHOOK_TOKEN:
        print(f"✗ Invalid webhook token: {token}")
        return False
    
    print("✓ Webhook signature validated")
    return True

def check_sync_token(service, folder_id, change_token):
    """
    Custom Check #1: Validate change token is valid
    (prevents replaying old webhooks)
    """
    try:
        changes = service.changes().list(
            pageToken=change_token,
            spaces='drive',
            maxResults=1
        ).execute()
        
        print(f"✓ Sync token valid. Changes available: {len(changes.get('changes', []))}")
        return True
    except Exception as e:
        print(f"✗ Invalid change token: {str(e)}")
        return False

def is_file_supported(file_metadata):
    """
    Custom Check #2: Filter files by type, size, name pattern
    """
    # Skip if it's a folder
    if file_metadata['mimeType'] == 'application/vnd.google-apps.folder':
        return False
    
    # Skip if it's a shortcut
    if file_metadata.get('shortcutDetails'):
        return False
    
    # Optional: Filter by file size (e.g., max 100MB)
    file_size = int(file_metadata.get('size', 0))
    max_size_bytes = 100 * 1024 * 1024
    if file_size > max_size_bytes:
        print(f"⚠ File {file_metadata['name']} too large ({file_size} bytes). Skipping.")
        return False
    
    # Optional: Allowlist file types
    allowed_extensions = ['.csv', '.json', '.parquet', '.xlsx']
    name = file_metadata['name']
    if not any(name.endswith(ext) for ext in allowed_extensions):
        print(f"⚠ File {name} not in allowed types. Skipping.")
        return False
    
    return True

def download_file_from_drive(service, file_id, file_name):
    """Download file from Google Drive"""
    try:
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()
        print(f"✓ Downloaded: {file_name}")
        return file_content
    except Exception as e:
        print(f"✗ Failed to download {file_name}: {str(e)}")
        raise

def upload_to_s3(file_name, file_content, metadata=None):
    """
    Upload file to S3 with metadata.
    
    Custom Check #3: Idempotency check (prevent duplicates)
    """
    try:
        # Check if file already exists
        try:
            existing = s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=file_name
            )
            existing_etag = existing['ETag'].strip('"')
            # Compare MD5
            current_md5 = hashlib.md5(file_content).hexdigest()
            if existing_etag == current_md5:
                print(f"⚠ File {file_name} already in S3 with same content. Skipping.")
                return 'skipped'
        except s3_client.exceptions.NoSuchKey:
            pass  # File doesn't exist, proceed
        
        # Upload file
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=file_name,
            Body=file_content,
            Metadata=metadata or {
                'source': 'google-drive',
                'uploaded-via': 'webhook'
            }
        )
        print(f"✓ Uploaded to S3: s3://{S3_BUCKET}/{file_name}")
        return 'uploaded'
    except Exception as e:
        print(f"✗ Failed to upload {file_name} to S3: {str(e)}")
        raise

def log_sync_event(file_id, file_name, status, error=None):
    """
    Custom Check #4: Log all sync events for audit trail
    """
    table = dynamodb.Table('gdrive_s3_sync_log')
    table.put_item(
        Item={
            'file_id': file_id,
            'timestamp': int(time.time()),
            'file_name': file_name,
            'status': status,  # 'uploaded', 'skipped', 'failed'
            'error': error or ''
        }
    )

def lambda_handler(event, context):
    """
    Main webhook handler.
    
    Triggered by Google Drive changes.
    """
    try:
        # Parse request
        headers = event.get('headers', {})
        body = event.get('body', '{}')
        
        # Check #1: Validate webhook signature
        if not validate_webhook_signature(headers, body):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Parse webhook payload
        payload = json.loads(body) if isinstance(body, str) else body
        
        # Extract change info
        change_token = headers.get('X-Goog-Channel-Token')
        folder_id = payload.get('folder_id')  # You need to pass this
        
        if not folder_id:
            print("⚠ No folder_id in payload. Skipping.")
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing folder_id'})}
        
        service = get_drive_service()
        
        # Check #2: Validate change token
        if not check_sync_token(service, folder_id, change_token):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid sync token'})
            }
        
        # Query what changed
        changes = service.changes().list(
            pageToken=change_token,
            spaces='drive',
            pageSize=100
        ).execute()
        
        processed = 0
        skipped = 0
        failed = 0
        
        for change in changes.get('changes', []):
            try:
                if 'file' not in change:
                    continue
                
                file_metadata = change['file']
                file_id = file_metadata['id']
                file_name = file_metadata['name']
                
                # Check #3: Filter by file type/size/name
                if not is_file_supported(file_metadata):
                    skipped += 1
                    log_sync_event(file_id, file_name, 'skipped')
                    continue
                
                # Download and upload
                file_content = download_file_from_drive(service, file_id, file_name)
                result = upload_to_s3(file_name, file_content)
                
                if result == 'uploaded':
                    processed += 1
                elif result == 'skipped':
                    skipped += 1
                
                log_sync_event(file_id, file_name, result)
                
            except Exception as e:
                failed += 1
                print(f"✗ Error processing {file_name}: {str(e)}")
                log_sync_event(file_id, file_name, 'failed', str(e))
        
        summary = {
            'processed': processed,
            'skipped': skipped,
            'failed': failed,
            'total': processed + skipped + failed
        }
        
        print(f"✓ Webhook processed. Summary: {summary}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(summary)
        }
        
    except Exception as e:
        print(f"✗ Webhook handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

---

## 6. Custom Checks Summary

| Check | Purpose | Location |
|-------|---------|----------|
| **Webhook Signature** | Verify request came from Google | Handler start |
| **Sync Token Validation** | Ensure token is valid | Early in handler |
| **File Type Filtering** | Only process allowed files | Per-file logic |
| **Size Limits** | Skip large files | Per-file logic |
| **Idempotency** | Prevent duplicate uploads | Before S3 put |
| **Audit Logging** | Track all sync events | After each file |

---

## 7. Infrastructure as Code (Terraform)

**Duration: 2-3 hours**

Using Infrastructure as Code (IaC) ensures your infrastructure is reproducible, version-controlled, and can be easily deployed across environments (dev, staging, production). This section uses the AWS resources and secrets configured in Sections 2 and 3.

```hcl
# Lambda execution role
resource "aws_iam_role" "webhook_lambda_role" {
  name = "gdrive-webhook-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Attach policies
resource "aws_iam_role_policy" "webhook_lambda_policy" {
  name = "webhook-lambda-policy"
  role = aws_iam_role.webhook_lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:HeadObject"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.channels.arn,
          aws_dynamodb_table.sync_log.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:google-drive*"
      }
    ]
  })
}

# DynamoDB tables
resource "aws_dynamodb_table" "channels" {
  name = "gdrive_channels"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "folder_id"
  
  attribute {
    name = "folder_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "sync_log" {
  name = "gdrive_s3_sync_log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "file_id"
  range_key = "timestamp"
  
  attribute {
    name = "file_id"
    type = "S"
  }
  
  attribute {
    name = "timestamp"
    type = "N"
  }
}

# API Gateway for webhook
resource "aws_apigatewayv2_api" "webhook" {
  name = "gdrive-webhook"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "webhook" {
  api_id = aws_apigatewayv2_api.webhook.id
  integration_type = "AWS_LAMBDA"
  integration_method = "POST"
  payload_format_version = "2.0"
  target = aws_lambda_function.webhook_handler.arn
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id = aws_apigatewayv2_api.webhook.id
  route_key = "POST /webhook"
  target = "integrations/${aws_apigatewayv2_integration.webhook.id}"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id = aws_apigatewayv2_api.webhook.id
  name = "prod"
  auto_deploy = true
}
```

---

## 8. Monitoring & Alerts

**Duration: 1-2 hours**

Monitoring ensures you're notified when something goes wrong. This section configures CloudWatch metrics and SNS alerts for your pipeline.

### CloudWatch Metrics

```python
import logging
from aws_lambda_powertools import Logger, Tracer, Metrics

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# In webhook handler
metrics.add_metric(
    name="FilesProcessed",
    unit="Count",
    value=processed
)

metrics.add_metric(
    name="FilesSkipped",
    unit="Count",
    value=skipped
)

metrics.add_metric(
    name="SyncFailures",
    unit="Count",
    value=failed
)
```

### SNS Alerts

```bash
# Create SNS topic
aws sns create-topic --name gdrive-s3-alerts

# Subscribe to email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:gdrive-s3-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

---

## 9. Deployment Checklist

Use this checklist to ensure all components are properly configured before going to production:

### Google Cloud Platform
- [ ] Create Google Cloud project (Section 3.1)
- [ ] Enable Google Drive API (Section 3.2)
- [ ] Create service account (Section 3.3)
- [ ] Download service account key (Section 3.4)
- [ ] Create Google Drive folder (Section 3.5)
- [ ] Share folder with service account email (Section 3.5)
- [ ] Test service account access (Section 3.6)
- [ ] Store service account key in AWS Secrets Manager (Section 3.7)

### AWS Infrastructure
- [ ] Store secrets in Secrets Manager (Sections 2.1.3 and 3.7)
- [ ] Deploy Lambda functions (webhook handler + channel renewal) (Sections 4 & 5)
- [ ] Create DynamoDB tables (Section 7)
- [ ] Set up API Gateway (Section 7)
- [ ] Configure IAM roles and policies (Section 7)
- [ ] Create S3 bucket for file storage (Section 7)

### Automation
- [ ] Configure CloudWatch Events for 12-hour renewal trigger (Section 4)
- [ ] Set up SNS topic for alerts (Section 8)
- [ ] Subscribe to alert notifications (Section 8)
- [ ] Enable CloudWatch logging (Section 8)

### Testing & Validation
- [ ] Test webhook with sample file upload (Section 10)
- [ ] Verify file appears in S3 (Section 10)
- [ ] Test channel renewal Lambda (Section 10)
- [ ] Monitor CloudWatch logs for 24 hours (Section 8)
- [ ] Validate automated renewal triggers (Section 10)

### Production Readiness
- [ ] Review and update resource quotas
- [ ] Set up backup strategy for DynamoDB
- [ ] Configure S3 lifecycle policies
- [ ] Enable AWS CloudTrail for audit logging
- [ ] Document runbook for common operations
- [ ] Set up on-call rotation (if applicable)

✓ **Ready for Production:** All items checked

---

## 10. Testing

**Duration: 2-3 hours**

Thorough testing ensures your pipeline works correctly before processing production data.

### Manual Webhook Test

```bash
# Invoke webhook Lambda directly
aws lambda invoke \
  --function-name gdrive-webhook-handler \
  --payload '{
    "headers": {
      "X-Goog-Channel-Token": "your-webhook-token"
    },
    "body": "{\"folder_id\": \"your-folder-id\"}"
  }' \
  response.json

cat response.json
```

### Test Channel Renewal

```bash
aws lambda invoke \
  --function-name gdrive-channel-renewal \
  --payload '{"folder_id": "your-folder-id"}' \
  renewal_response.json

cat renewal_response.json
```

---

## 11. Troubleshooting Common Issues

This section covers common problems you might encounter and their solutions.

### 11.1 Google Drive API Issues

#### Error: "Service account does not have access to the folder" (403)

**Symptoms:**
- Test script fails with 403 Forbidden error
- Webhook handler logs show permission errors

**Solutions:**
1. **Verify folder is shared:**
   - Go to Google Drive
   - Right-click the folder → "Share"
   - Confirm service account email is listed
   
2. **Check permission level:**
   - Service account needs "Editor" or "Viewer" access
   - Update permission if set to "Commenter" or "Reader"

3. **Wait for propagation:**
   - Google Drive permissions can take 1-2 minutes to propagate
   - Wait and try again

4. **Verify service account email:**
   ```bash
   # Check service account email
   cat service-account-key.json | grep client_email
   # Should match the email you shared the folder with
   ```

#### Error: "API key not valid" or "API key expired"

**Symptoms:**
- Authentication failures
- "Invalid authentication credentials" errors

**Solutions:**
1. **Regenerate service account key:**
   - Go to GCP Console → IAM & Admin → Service Accounts
   - Click your service account → Keys tab
   - Delete old key
   - Create new key
   - Update AWS Secrets Manager

2. **Verify API is enabled:**
   ```bash
   gcloud services list --enabled --filter="name:drive.googleapis.com"
   # Should show drive.googleapis.com
   ```

3. **Check project ID:**
   ```bash
   # Verify you're using the correct project
   gcloud config get-value project
   ```

#### Error: "Invalid folder ID" (404)

**Symptoms:**
- Cannot find folder
- 404 Not Found errors

**Solutions:**
1. **Double-check folder ID from URL:**
   ```
   https://drive.google.com/drive/folders/1aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1uV
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                            Copy this part
   ```

2. **Verify you're logged into correct Google account:**
   - The folder must be in the same Google account that owns the GCP project
   - Or the folder must be shared with the service account

3. **Check folder wasn't deleted:**
   - Open Google Drive and verify folder exists
   - Check trash if accidentally deleted

---

### 11.2 AWS Lambda Issues

#### Error: "Secret not found" in Lambda logs

**Symptoms:**
- Lambda fails immediately with "SecretNotFoundException"
- Handler can't retrieve Google credentials

**Solutions:**
1. **Verify secret exists:**
   ```bash
   aws secretsmanager list-secrets --region us-east-1 | grep google-drive
   ```

2. **Check IAM permissions:**
   ```bash
   # Lambda execution role needs secretsmanager:GetSecretValue
   aws iam get-role-policy \
     --role-name webhook-lambda-role \
     --policy-name webhook-lambda-policy
   ```

3. **Verify region:**
   - Secrets Manager is region-specific
   - Ensure Lambda and secret are in same region

4. **Update Lambda IAM policy:**
   ```json
   {
     "Effect": "Allow",
     "Action": "secretsmanager:GetSecretValue",
     "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:google-drive*"
   }
   ```

#### Error: "Unable to import module 'lambda_function'"

**Symptoms:**
- Lambda fails with import errors
- Missing dependencies like `google-api-python-client`

**Solutions:**
1. **Create deployment package with dependencies:**
   ```bash
   # Create package directory
   mkdir lambda_package
   cd lambda_package
   
   # Install dependencies locally
   pip install \
     google-api-python-client \
     google-auth-httplib2 \
     google-auth-oauthlib \
     boto3 \
     -t .
   
   # Copy your Lambda code
   cp ../webhook_handler.py lambda_function.py
   
   # Create ZIP
   zip -r ../webhook_handler.zip .
   
   # Upload to Lambda
   aws lambda update-function-code \
     --function-name webhook-handler \
     --zip-file fileb://../webhook_handler.zip
   ```

2. **Use Lambda Layers (alternative):**
   ```bash
   # Create layer for Google libraries
   mkdir -p layer/python
   pip install google-api-python-client google-auth-httplib2 -t layer/python
   cd layer
   zip -r ../google-drive-layer.zip .
   
   # Upload as Lambda layer
   aws lambda publish-layer-version \
     --layer-name google-drive-dependencies \
     --zip-file fileb://../google-drive-layer.zip \
     --compatible-runtimes python3.11
   ```

#### Error: Lambda timeout after 3 seconds

**Symptoms:**
- Lambda times out before completing
- Large files fail to sync

**Solutions:**
1. **Increase Lambda timeout:**
   ```bash
   aws lambda update-function-configuration \
     --function-name webhook-handler \
     --timeout 60  # 60 seconds
   ```

2. **Increase memory (improves CPU too):**
   ```bash
   aws lambda update-function-configuration \
     --function-name webhook-handler \
     --memory-size 512  # MB
   ```

3. **Optimize code:**
   - Use streaming for large files
   - Implement pagination for large change lists
   - Process files in batches

---

### 11.3 Channel Renewal Issues

#### Error: "Channel already expired"

**Symptoms:**
- Renewal Lambda runs but channel is already expired
- Webhook stops receiving notifications

**Solutions:**
1. **Reduce renewal interval:**
   ```bash
   # Change from 12 hours to 6 hours
   aws events put-rule \
     --name gdrive-channel-renewal \
     --schedule-expression "rate(6 hours)"
   ```

2. **Manually create new channel:**
   ```bash
   # Invoke renewal Lambda manually
   aws lambda invoke \
     --function-name channel-renewal \
     --payload '{"folder_id": "YOUR_FOLDER_ID"}' \
     response.json
   ```

3. **Check CloudWatch rule is enabled:**
   ```bash
   aws events list-rules --name-prefix gdrive-channel
   # Verify State is "ENABLED"
   ```

#### Error: "Cannot renew - old channel not found"

**Symptoms:**
- DynamoDB doesn't have channel record
- Renewal fails to find existing channel

**Solutions:**
1. **Initialize channel manually:**
   ```bash
   # Run renewal Lambda to create initial channel
   aws lambda invoke \
     --function-name channel-renewal \
     --payload '{"folder_id": "YOUR_FOLDER_ID"}' \
     response.json
   ```

2. **Verify DynamoDB table exists:**
   ```bash
   aws dynamodb describe-table --table-name gdrive_channels
   ```

3. **Check Lambda has DynamoDB permissions:**
   - Verify IAM policy includes `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem`

---

### 11.4 S3 Upload Issues

#### Error: "Access Denied" when uploading to S3

**Symptoms:**
- Lambda can't write to S3 bucket
- Files don't appear in S3

**Solutions:**
1. **Verify Lambda IAM policy:**
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "s3:PutObject",
       "s3:GetObject"
     ],
     "Resource": "arn:aws:s3:::YOUR-BUCKET/*"
   }
   ```

2. **Check S3 bucket exists:**
   ```bash
   aws s3 ls s3://YOUR-BUCKET/
   ```

3. **Verify bucket policy allows Lambda:**
   ```bash
   aws s3api get-bucket-policy --bucket YOUR-BUCKET
   ```

#### Error: "File already exists" or duplicate uploads

**Symptoms:**
- Same file uploaded multiple times
- Unnecessary storage costs

**Solutions:**
1. **Implement idempotency check (already in code):**
   - The webhook handler checks MD5 hash before uploading
   - If file exists with same content, it skips

2. **Enable S3 versioning (optional):**
   ```bash
   aws s3api put-bucket-versioning \
     --bucket YOUR-BUCKET \
     --versioning-configuration Status=Enabled
   ```

3. **Add DynamoDB tracking:**
   - Use `gdrive_s3_sync_log` table to track processed files
   - Check table before downloading from Drive

---

### 11.5 Webhook Issues

#### Error: Webhook receives no notifications

**Symptoms:**
- Files uploaded to Drive but Lambda not triggered
- API Gateway shows no requests

**Solutions:**
1. **Verify channel is active:**
   ```bash
   aws dynamodb get-item \
     --table-name gdrive_channels \
     --key '{"folder_id": {"S": "YOUR_FOLDER_ID"}}'
   # Check expiration timestamp
   ```

2. **Check API Gateway URL is correct:**
   ```bash
   # Get API Gateway URL
   aws apigatewayv2 get-apis
   # Verify webhook was created with this URL
   ```

3. **Test API Gateway directly:**
   ```bash
   curl -X POST https://YOUR-API-GATEWAY-URL/webhook \
     -H "X-Goog-Channel-Token: YOUR-TOKEN" \
     -d '{"folder_id": "YOUR_FOLDER_ID"}'
   ```

4. **Recreate channel:**
   - Channels may fail silently
   - Delete and recreate using renewal Lambda

#### Error: "Invalid token" (401)

**Symptoms:**
- Webhook receives request but rejects it
- Authentication failures in logs

**Solutions:**
1. **Verify token matches:**
   ```bash
   # Check token in Secrets Manager
   aws secretsmanager get-secret-value \
     --secret-id gdrive-s3-config \
     | jq -r '.SecretString | fromjson | .WEBHOOK_TOKEN'
   
   # Should match token used when creating channel
   ```

2. **Regenerate token and channel:**
   ```bash
   # Generate new token
   NEW_TOKEN=$(openssl rand -hex 32)
   
   # Update secret
   aws secretsmanager update-secret \
     --secret-id gdrive-s3-config \
     --secret-string "{\"WEBHOOK_TOKEN\": \"$NEW_TOKEN\", ...}"
   
   # Recreate channel with new token
   aws lambda invoke \
     --function-name channel-renewal \
     --payload "{\"folder_id\": \"YOUR_FOLDER_ID\"}" \
     response.json
   ```

---

### 11.6 Testing Issues

#### Error: Test script can't find credentials

**Symptoms:**
- `test_google_drive_auth.py` fails with FileNotFoundError
- Credentials not loaded

**Solutions:**
1. **Verify file exists:**
   ```bash
   ls -la service-account-key.json
   ```

2. **Check file path in script:**
   ```python
   # Make sure path is correct relative to where you run the script
   SERVICE_ACCOUNT_FILE = 'service-account-key.json'  # Or full path
   ```

3. **Run from project root:**
   ```bash
   cd customer-care-call-processor
   python3 test_google_drive_auth.py
   ```

---

### 11.7 General Debugging Tips

#### Enable Debug Logging

**Lambda Functions:**
```python
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Change from INFO to DEBUG
```

**CloudWatch Logs Insights:**
```sql
# Query Lambda errors
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

#### Check Service Quotas

```bash
# Lambda
aws service-quotas get-service-quota \
  --service-code lambda \
  --quota-code L-B99A9384  # Concurrent executions

# API Gateway
aws service-quotas get-service-quota \
  --service-code apigateway \
  --quota-code L-A93DB0CB  # Requests per second
```

#### Verify All Services in Same Region

```bash
# Check Lambda region
aws lambda list-functions --region us-east-1

# Check S3 bucket region
aws s3api get-bucket-location --bucket YOUR-BUCKET

# Check DynamoDB table region
aws dynamodb list-tables --region us-east-1
```

---

### 11.8 Getting Help

If you're still stuck after trying these solutions:

1. **Check AWS CloudWatch Logs:**
   - Navigate to CloudWatch → Log Groups
   - Find `/aws/lambda/webhook-handler` or `/aws/lambda/channel-renewal`
   - Review recent log streams

2. **Check Google Cloud Logs:**
   ```bash
   gcloud logging read "resource.type=api" --limit 50
   ```

3. **Review GitHub Issues:**
   - Check the repository's Issues tab for similar problems
   - Search closed issues for solutions

4. **Enable X-Ray Tracing (Advanced):**
   ```bash
   aws lambda update-function-configuration \
     --function-name webhook-handler \
     --tracing-config Mode=Active
   ```

5. **Ask for Help:**
   - Include: CloudWatch logs, error messages, and steps you've tried
   - Redact sensitive information (account IDs, secrets, tokens)

---

## 12. Summary

This webhook implementation provides a production-ready, real-time data pipeline from Google Drive to AWS S3.

### What You've Built

✅ **Real-time sync** - Files appear in S3 within seconds of upload to Google Drive  
✅ **Automatic channel renewal** - No manual intervention needed, renews every 12 hours (configurable to 6 hours)  
✅ **Custom validation checks** - 4 levels of filtering ensure only valid files are processed  
✅ **Audit logging** - Every file transfer is tracked in DynamoDB for compliance  
✅ **Error handling** - Robust retry logic and alerting via SNS  
✅ **Cost efficiency** - Typical cost: $2–5/month for moderate usage  
✅ **Security** - Credentials stored in AWS Secrets Manager, never in code  
✅ **Scalability** - Lambda auto-scales to handle traffic spikes

### Architecture Benefits

**vs. Polling-based approach:**
- 🚀 **Faster:** Seconds vs. minutes latency
- 💰 **Cheaper:** Only pay for actual changes, not continuous polling
- 🔋 **More efficient:** No wasted API calls checking for changes

**vs. Manual uploads:**
- ⏰ **Automatic:** Zero human intervention required
- 🎯 **Reliable:** No missed files or human errors
- 📊 **Auditable:** Full history of all transfers

### Cost Breakdown (Estimated)

For 1,000 files/month with average 5MB size:

| Service | Usage | Cost/Month |
|---------|-------|------------|
| Lambda (Webhook) | 1,000 invocations | $0.00 (within free tier) |
| Lambda (Renewal) | 60 invocations/month | $0.00 (within free tier) |
| API Gateway | 1,000 requests | $0.0035 |
| DynamoDB | 1,000 writes, 2,000 reads | $0.00 (within free tier) |
| S3 Storage | 5GB stored | $0.12 |
| S3 PUT requests | 1,000 requests | $0.005 |
| Secrets Manager | 2 secrets | $0.80 |
| **Total** | | **~$1-2/month** |

💡 **Note:** Costs scale linearly with usage. Google Drive API is free up to 1 billion queries/day.

### Performance Characteristics

- **Latency:** < 5 seconds from upload to S3
- **Throughput:** Limited by Lambda concurrency (default: 1,000 concurrent executions)
- **File size limit:** 100MB (configurable in code, AWS Lambda has 6MB payload limit so uses streaming)
- **Supported file types:** Configurable whitelist (default: .csv, .json, .parquet, .xlsx)

### Next Steps

Now that your pipeline is built and tested:

1. **Deploy to Production:**
   - Create prod configuration: `config/prod.yaml`
   - Update resource names with `-prod` suffix
   - Deploy Terraform with `terraform workspace select prod`

2. **Set Up Monitoring Dashboard:**
   - Create CloudWatch dashboard with key metrics
   - Set up alerts for error rates > 5%
   - Monitor costs weekly

3. **Document for Your Team:**
   - Add operational runbook
   - Document common troubleshooting scenarios
   - Create on-call guide

4. **Optimize and Iterate:**
   - Review logs to identify bottlenecks
   - Adjust Lambda memory/timeout based on actual usage
   - Add custom metrics for business KPIs

5. **Extend Functionality:**
   - Add file validation (e.g., CSV schema checks)
   - Implement data transformation before S3 upload
   - Add notifications to Slack/Teams when files are processed
   - Create S3 lifecycle policies for archival
   - Add encryption at rest with AWS KMS

### Additional Resources

- **Google Drive API Documentation:** [https://developers.google.com/drive/api](https://developers.google.com/drive/api)
- **Google Drive Push Notifications:** [https://developers.google.com/drive/api/v3/push](https://developers.google.com/drive/api/v3/push)
- **AWS Lambda Best Practices:** [https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- **Terraform AWS Provider:** [https://registry.terraform.io/providers/hashicorp/aws/latest/docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

### Support

For questions or issues:
- **Repository Issues:** [https://github.com/olajio/customer-care-call-processor/issues](https://github.com/olajio/customer-care-call-processor/issues)
- **Troubleshooting Guide:** See Section 11 above
- **AWS Support:** [https://console.aws.amazon.com/support](https://console.aws.amazon.com/support)
- **Google Cloud Support:** [https://console.cloud.google.com/support](https://console.cloud.google.com/support)

---

**Congratulations! 🎉** You've built a production-ready, serverless data pipeline using webhooks, Lambda, and modern cloud practices. This implementation demonstrates:
- Cloud architecture best practices
- Security-first design with Secrets Manager
- Infrastructure as Code with Terraform
- Comprehensive error handling and monitoring
- Cost-effective serverless design

Keep this guide as a reference and share it with your team. Happy building! 🚀

