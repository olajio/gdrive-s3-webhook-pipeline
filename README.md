# Enterprise Customer Care Call Processing System

An AI-powered, serverless system that automatically transcribes and summarizes customer care call recordings. Upload audio to Google Drive → Automated transcription (Amazon Transcribe) → AI-generated summaries (Amazon Bedrock Claude 3.5) → Real-time dashboard with insights delivered in under 5 minutes.

## 📖 Overview

This system transforms customer care operations by automating call analysis, reducing manual review time by 80%. Caseworkers upload call recordings to Google Drive, triggering a fully automated pipeline that delivers actionable summaries with sentiment analysis, action items, and key details to a real-time web dashboard.

**Key Capabilities:**
- 🤖 **Zero-Touch Processing** - Upload → Transcribe → Summarize → Deliver (fully automated)
- 🧠 **AI-Powered Analysis** - Claude 3.5 Sonnet extracts issues, action items, sentiment
- ⚡ **Real-Time Dashboard** - WebSocket-based live updates, no page refresh needed
- 🎯 **Sub-5-Minute SLA** - From upload to summary in under 5 minutes per call
- 📊 **Structured Insights** - Consistent output: issue, key details, action items, next steps
- 🔒 **Enterprise-Grade Security** - Encryption at rest/transit, IAM roles, audit logging
- 📈 **Scalable Architecture** - Handle 100-10,000 calls/day with AWS serverless
- 💰 **Cost Efficient** - ~$0.50-$1.00 per call processed

## 🏗️ System Architecture

### High-Level Flow

```
📞 Audio File → Google Drive → Webhook → AWS Lambda → S3 Storage
                                              ↓
                                    AWS Step Functions
                                    (Orchestration)
                                              ↓
                        ┌─────────────────────┴─────────────────────┐
                        ↓                                           ↓
                Amazon Transcribe                          Amazon Bedrock
                (Speech-to-Text)                    (Claude 3.5 Sonnet AI)
                Speaker ID + Timestamps                  Structured Summaries
                        ↓                                           ↓
                        └─────────────────────┬─────────────────────┘
                                              ↓
                                        DynamoDB Storage
                                              ↓
                                    WebSocket Notification
                                              ↓
                                    📱 React Dashboard
                            (Real-time updates, no refresh)
```

### Core Components

1. **Data Ingestion Layer**
   - Google Drive API with Push Notifications (real-time webhooks)
   - API Gateway webhook endpoint
   - Lambda: File download → S3 upload → DynamoDB record creation

2. **AI Processing Pipeline**
   - **Step Functions**: Orchestrates multi-stage workflow with error handling
   - **Amazon Transcribe**: Converts audio to text with speaker identification
   - **Process Lambda**: Parses and formats transcripts
   - **Amazon Bedrock (Claude 3.5 Sonnet)**: Generates structured summaries with sentiment analysis
   - **Save Lambda**: Persists results to DynamoDB and S3

3. **Storage Layer**
   - **S3**: Audio files, transcripts, summaries (organized by date)
   - **DynamoDB**: Call metadata, summaries, processing status (3 tables with GSIs)

4. **Backend API Layer**
   - API Gateway REST endpoints (list, detail, audio URLs, transcripts)
   - Amazon Cognito for authentication (JWT tokens)
   - Lambda functions for API handlers

5. **Real-Time Notification System**
   - API Gateway WebSocket API
   - Lambda: Connection management, message broadcasting
   - DynamoDB: Active WebSocket connections tracking

6. **Frontend Application**
   - React 18 + TypeScript dashboard
   - Features: Summary list, detail view, audio player, filters, search
   - WebSocket integration for real-time updates
   - AWS Amplify hosting

**→ See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation**

## 🚀 Quick Start

### Prerequisites
- **AWS Account** with access to Lambda, S3, DynamoDB, Transcribe, Bedrock, Step Functions
- **Google Cloud Project** with Drive API enabled
- **Development Tools**: AWS CLI v2, AWS CDK, Python 3.11+, Node.js 18+, Google Cloud SDK
- **Credentials**: Google service account with Drive access

### Implementation Path

**Choose your guide based on experience level:**

#### 🎓 New to AWS/GCP or Want Step-by-Step Guide
**Start here:** [SETUP_GUIDE.md](SETUP_GUIDE.md)

This comprehensive guide provides:
- **Section 1**: Prerequisites (AWS, Google Cloud, development tools)
- **Section 2-3**: Google Cloud Platform and AWS setup with step-by-step instructions
- **Section 4-10**: Deployment, testing, monitoring, and troubleshooting

**Time Estimate**: 2-4 hours for initial setup

#### ⚡ Experienced with AWS/GCP and Want Quick Deploy
**Start here:** [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)

This concise guide assumes familiarity with:
- AWS CDK and serverless architecture
- Google Cloud Platform and service accounts
- Infrastructure as Code principles

**Time Estimate**: 30-60 minutes for core infrastructure

### Deployment Steps (High-Level)

```bash
# 1. Set up Google Drive integration (Section 2 in SETUP_GUIDE.md)
- Create Google Cloud Project
- Enable Google Drive API
- Create service account and download credentials
- Share Google Drive folder with service account
- Test authentication

# 2. Configure AWS foundation (covered in implementation guides)
- Set up AWS account and CLI
- Initialize Terraform project
- Configure S3, DynamoDB, Secrets Manager

# 3. Deploy AI processing pipeline
- Configure Amazon Transcribe
- Set up Amazon Bedrock (Claude 3.5 Sonnet)
- Deploy Step Functions state machine
- Create processing Lambda functions

# 4. Deploy backend APIs
- Set up API Gateway (REST + WebSocket)
- Configure Amazon Cognito for authentication
- Deploy API Lambda functions

# 5. Deploy frontend dashboard
- Build React application
- Configure Amplify or CloudFront hosting
- Set up WebSocket connection

# 6. Test end-to-end
- Upload test audio file to Google Drive
- Verify webhook triggers processing
- Confirm summary appears in dashboard
- Validate WebSocket notifications
```

**💡 Tip**: First-time users should follow [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed guidance. Experienced users can use [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for faster deployment.

## 📚 Documentation

### 📖 Core Documentation

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** ⭐ **START HERE**
   - Complete system architecture and data flow
   - Component specifications for all 12 system components
   - Technology stack breakdown
   - High-level and detailed architecture diagrams
   
2. **[case_study_file.md](case_study_file.md)** - Complete Project Specification
   - Executive summary and business requirements
   - Detailed technical specifications for all components
   - Implementation phases (16 stages)
   - Success metrics and budget estimates
   - Risk mitigation strategies
   
3. **[01_features_and_stories.md](01_features_and_stories.md)** - User Stories & Features
   - 8 major epics with user stories
   - Acceptance criteria for each feature
   - Non-functional requirements
   - Future enhancement backlog
   
4. **[02_build_process_steps.md](02_build_process_steps.md)** - Implementation Guide
   - 16 detailed implementation stages with commands
   - Code snippets and configuration examples
   - Validation procedures for each step
   - Deliverables tracking
   
5. **[03_stage_completion_checklist.md](03_stage_completion_checklist.md)** - Validation Checklists
   - Completion criteria for all 16 stages
   - Verification commands and tests
   - Sign-off forms for accountability
   - Security checklists
   
6. **[04_navigation_guide.md](04_navigation_guide.md)** - Documentation Roadmap
   - Stage-by-stage navigation map
   - Which document to use at each phase
   - Quick reference guide

### 🚀 Quick Reference Guides

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete deployment walkthrough including:
  - **Section 1**: Prerequisites and environment setup
   - Development tools installation (Node.js, Python, AWS CLI, Terraform, Google Cloud SDK)
   - Version control configuration
   - Python virtual environment setup
  - **Section 2**: Google Cloud Platform setup
   - Creating Google Cloud Project
   - Enabling Google Drive API
   - Service account creation and configuration
   - Security best practices
   - Testing service account access with provided test script
  - **Section 10**: Troubleshooting common issues

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Quick deployment reference for experienced users

### 📁 Repository Structure

```
README.md                              # This file
ARCHITECTURE.md                        # System architecture (START HERE)
SETUP_GUIDE.md                         # Complete deployment walkthrough
IMPLEMENTATION_GUIDE.md                # Quick deployment guide
case_study_file.md                     # Complete specification
01_features_and_stories.md             # User stories and features
02_build_process_steps.md              # Implementation steps
03_stage_completion_checklist.md       # Validation checklists
04_navigation_guide.md                 # Documentation roadmap
config/                                # Environment configs
scripts/                               # Deployment scripts
src/lambda/                            # Lambda functions
  ├── webhook/                         # Webhook handler
  ├── processing/                      # AI processing (Transcribe, Bedrock)
  ├── api/                             # REST API handlers
  └── websocket/                       # WebSocket handlers
stepfunctions/                         # Step Functions definitions
terraform/                             # Infrastructure as Code
tests/                                 # Test suites
```

## 🔑 Key Technologies

### AWS Services
- **Lambda**: Serverless compute (Python 3.11)
- **Step Functions**: Workflow orchestration
- **Transcribe**: Speech-to-text with speaker ID
- **Bedrock**: AI models (Claude 3.5 Sonnet)
- **S3**: Object storage (audio, transcripts, summaries)
- **DynamoDB**: NoSQL database with GSIs
- **API Gateway**: REST + WebSocket APIs
- **Cognito**: User authentication (JWT)
- **CloudWatch**: Monitoring, dashboards, alarms
- **Secrets Manager**: Credential storage

### Google Cloud Platform
- **Google Drive API**: File storage and webhooks
- **Service Account**: Programmatic access

### Frontend
- **React 18** + TypeScript
- **Vite** build tool
- **Material-UI** or Tailwind CSS
- **React Query** for state management
- **AWS Amplify** for hosting


### Data Management

Uses DynamoDB to track:
- **call-summaries**: All call metadata, transcripts, and AI summaries with GSIs
- **websocket-connections**: Active WebSocket clients for real-time updates
- **users**: User profiles and roles (supplements Cognito)

### Processing States
```
UPLOADED → TRANSCRIBING → SUMMARIZING → COMPLETED
                                      ↘ FAILED
```

## 📊 Cost Estimate

### Monthly Cost (200 calls/day)
| Component | Estimate |
|-----------|----------|
| Amazon Transcribe | $24 |
| Amazon Bedrock (Claude 3.5 Sonnet) | $60 |
| Lambda Functions | $5 |
| API Gateway (REST + WebSocket) | $2 |
| S3 Storage | $2 |
| DynamoDB | $3 |
| Step Functions | $1 |
| CloudWatch | $10 |
| Amplify Hosting | $12 |
| **Total** | **~$124/month** |

### Scaling Projections
| Volume | Monthly Cost |
|--------|-------------|
| 200 calls/day | ~$124 |
| 500 calls/day | ~$280 |
| 1,000 calls/day | ~$520 |
| 5,000 calls/day | ~$2,400 |

**Cost per call**: ~$0.50-$1.00 depending on call duration

## ⚙️ Configuration

### Required Secrets (AWS Secrets Manager)

```json
{
  "google-drive-service-account": {
    "type": "service_account",
    "project_id": "customer-care-audio-processor",
    "private_key_id": "...",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
    "client_email": "customer-care-drive-reader@project.iam.gserviceaccount.com",
    "client_id": "..."
  }
}
```

### Environment Variables

```python
# Webhook Handler Lambda
GOOGLE_DRIVE_FOLDER_ID = "1ABC..."
S3_BUCKET = "customer-care-audio-prod"
WEBHOOK_TOKEN = "random-secret-token"
CALL_SUMMARIES_TABLE = "call-summaries"

# Processing Lambdas
BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
TRANSCRIBE_LANGUAGE = "en-US"  # or "auto"
COGNITO_USER_POOL_ID = "us-east-1_xxxxx"

# Frontend Configuration
API_ENDPOINT = "https://api.yourdomain.com/v1"
WEBSOCKET_ENDPOINT = "wss://ws.yourdomain.com"
```

## 🧪 Testing

### End-to-End Test

1. **Upload a test audio file** to the Google Drive folder
2. **Monitor Step Functions** execution in AWS Console
3. **Verify DynamoDB** record is created with status COMPLETED
4. **Check frontend dashboard** for the new summary
5. **Test WebSocket** notification appears in browser

### Test Google Drive Authentication

```bash
# Run the provided test script
python test_google_drive.py
```

### Monitor Processing

```bash
# Watch webhook handler logs
aws logs tail /aws/lambda/webhook-handler --follow

# Watch Step Functions executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:call-processing

# Check call summary in DynamoDB
aws dynamodb get-item \
  --table-name call-summaries \
  --key '{"call_id": {"S": "YOUR_CALL_ID"}}'
```

### Validate Summary Quality

```bash
# Download summary from S3
aws s3 cp s3://customer-care-audio-prod/summaries/2026-01-31/call-id-summary.json .

# Check summary contains required fields
cat call-id-summary.json | jq '.issue_sentence, .key_details, .action_items'
```

## 📈 Monitoring

### CloudWatch Dashboards

1. **Processing Pipeline Dashboard**
   - Calls processed per hour
   - Processing time (P50, P95, P99)
   - Success/failure rates by stage

2. **API Performance Dashboard**
   - API latency by endpoint
   - Request counts and error rates
   - WebSocket connection metrics

3. **Cost Tracking Dashboard**
   - Transcribe minutes used
   - Bedrock token consumption
   - Monthly cost projections

### CloudWatch Alarms

**Critical (immediate notification):**
- Step Function failure rate > 10%
- API Gateway 5xx errors > 5/minute
- Lambda function errors > 10/minute

**Warning (business hours):**
- Average processing time > 10 minutes
- Bedrock throttling events

### Query Failed Calls

```bash
aws dynamodb query \
  --table-name call-summaries \
  --index-name status-timestamp-index \
  --key-condition-expression "#status = :status" \
  --expression-attribute-names '{"#status": "status"}' \
  --expression-attribute-values '{":status": {"S": "FAILED"}}'
```

## 🔧 Troubleshooting

### Common Issues

**Q: Transcription fails or takes too long**
- Check audio format is supported (mp3, wav, m4a, flac, ogg)
- Verify file size < 500MB
- Check Transcribe service quotas in AWS Console

**Q: Summary quality is poor**
- Review Bedrock prompt in Lambda function
- Check if transcript was properly formatted
- Verify Claude 3.5 Sonnet model access is enabled

**Q: WebSocket notifications not received**
- Verify WebSocket connection established (check browser DevTools)
- Check connection exists in websocket-connections DynamoDB table
- Review WebSocket Lambda logs for errors

**Q: Dashboard shows no summaries**
- Verify Cognito authentication is working
- Check API Gateway logs for 401/403 errors
- Confirm DynamoDB table has data

**Q: Step Functions execution fails**
- Check execution details in AWS Step Functions console
- Review individual Lambda function logs
- Verify IAM roles have required permissions

**→ See [SETUP_GUIDE.md](SETUP_GUIDE.md#10-troubleshooting) for detailed troubleshooting**

## 🚦 Getting Started

1. **Read** [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
2. **Review** [case_study_file.md](case_study_file.md) for complete specifications
3. **Follow** [02_build_process_steps.md](02_build_process_steps.md) for implementation
4. **Verify** using [03_stage_completion_checklist.md](03_stage_completion_checklist.md)
5. **Navigate** using [04_navigation_guide.md](04_navigation_guide.md) for stage-specific guidance

## 🤝 Contributing

This is a reference implementation for enterprise customer care call processing. Contributions are welcome:

- **Bug fixes**: Submit PRs with clear descriptions
- **Feature requests**: Open issues with use case details
- **Documentation**: Help improve guides and examples
- **Custom integrations**: Share adapters for other cloud storage providers

### Areas for Extension

- Additional AI models (GPT-4, Gemini)
- Multi-language transcription support
- Custom summary templates by industry
- Integration with CRM systems (Salesforce, HubSpot)
- Advanced analytics and reporting

## 📝 License

MIT

## 👤 Author

Olamide Olajide - [@olajio](https://github.com/olajio)

---

## 💬 Need Help?

1. **Check documentation**: [ARCHITECTURE.md](ARCHITECTURE.md) and [SETUP_GUIDE.md](SETUP_GUIDE.md)
2. **Review troubleshooting**: [SETUP_GUIDE.md](SETUP_GUIDE.md#10-troubleshooting)
3. **Check CloudWatch logs**: For detailed error messages and stack traces
4. **Open an issue**: On GitHub with reproduction steps

---

**Repository**: [github.com/olajio/customer-care-call-processor](https://github.com/olajio/customer-care-call-processor)  
**Last Updated**: January 2025
