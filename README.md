# Google Drive to AWS S3 Data Pipeline

A real-time, event-driven data pipeline that automatically syncs files from Google Drive to AWS S3 using webhooks. Built for scalability, reliability, and ease of maintenance.

## 📖 Overview

This project provides a complete implementation guide for migrating data from Google Drive to AWS S3 with continuous synchronization. Files are synced automatically as soon as they're created or modified in Google Drive, with zero manual intervention required.

**Key Features:**
- ⚡ **Real-time Sync** - Files synced within seconds of creation/modification
- 🔄 **Automatic Channel Renewal** - Manages Google Drive webhook lifecycle automatically
- ✅ **Smart Validation** - Custom checks to filter, validate, and deduplicate files
- 📊 **Audit Logging** - Complete tracking of all sync events
- 🛡️ **Error Handling** - Robust retry logic and alerting
- 💰 **Cost Efficient** - Serverless architecture (~$2–5/month)

## 📁 Repository Structure

```
README.md                         # This file
IMPLEMENTATION_GUIDE.md           # End-to-end deployment & operations playbook
STRATEGY_RANKING.md               # Comparison of 4 migration strategies
WEBHOOK_IMPLEMENTATION.md         # Webhook setup with code & IaC
WEBHOOK_TECHNICAL_DOCUMENTATION.md# Deep technical reference (internal)
WEBHOOK_ARCHITECTURE_PROPOSAL.md  # Customer/architect presentation
PIPELINE_STRATEGY_NOTES.md        # Tree-of-thought strategy notes
Google_Drive_to_S3_Migration_Plan.docx # Word version of strategy
config/                           # Env-specific configs
scripts/                          # Deployment and setup scripts
src/lambda/                       # Lambda source code
terraform/                        # Infrastructure as code
tests/                            # Unit, integration, E2E tests
```

## 🚀 Quick Start

### 1. Choose Your Strategy

We evaluated four different approaches:

| Strategy | Speed | Reliability | Complexity | Cost | Best For |
|----------|-------|-------------|-----------|------|----------|
| **Webhook (Recommended)** | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | Medium | $$$ | Production |
| Hybrid (Webhook + Polling) | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | High | $$$$ | Critical |
| Polling | ⚡⚡ | ⭐⭐⭐⭐ | Low | $$ | Non-urgent |
| Third-Party | ⚡⚡⚡ | ⭐⭐⭐ | ⚡⚡⚡⚡⚡ | $$$$$ | Quick POC |

**→ See [STRATEGY_RANKING.md](STRATEGY_RANKING.md) for detailed comparison**

### 2. Implement Webhook Solution

We recommend the **Webhook** approach for most use cases. It provides:
- Real-time sync (seconds latency)
- Automatic channel renewal every 12 hours
- 4-level custom validation system
- Complete audit logging

**→ Follow [WEBHOOK_IMPLEMENTATION.md](WEBHOOK_IMPLEMENTATION.md) for complete step-by-step guide**

### 3. Deploy to AWS

```bash
# Prerequisites
- AWS Account with Lambda, API Gateway, S3, DynamoDB, Secrets Manager
- Google Cloud Project with Drive API enabled
- Terraform (optional, for IaC)

# Steps
1. Create Google Drive service account
2. Configure AWS resources
3. Deploy Lambda functions
4. Set up API Gateway webhook endpoint
5. Configure CloudWatch Events for channel renewal
6. Test and monitor
```

## 📚 Documentation

### Main Guides

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Step-by-step deployment and operations playbook
- **[WEBHOOK_IMPLEMENTATION.md](WEBHOOK_IMPLEMENTATION.md)** - Webhook setup with channel renewal and validation checks
- **[STRATEGY_RANKING.md](STRATEGY_RANKING.md)** - Comparison and scoring of the 4 migration strategies
- **[Google_Drive_to_S3_Migration_Plan.docx](Google_Drive_to_S3_Migration_Plan.docx)** - Word-format strategy for sharing with stakeholders
- **[PIPELINE_STRATEGY_NOTES.md](PIPELINE_STRATEGY_NOTES.md)** - Tree-of-thought strategy exploration

### Key Sections in WEBHOOK_IMPLEMENTATION.md

1. **Architecture** - System diagram and component overview
2. **Setup** - Google Drive API and service account configuration
3. **Channel Management** - Handling 24-hour webhook expiration
4. **Webhook Handler** - Processing files with 4 custom checks
5. **Infrastructure as Code** - Terraform templates
6. **Monitoring & Alerts** - CloudWatch and SNS setup
7. **Testing** - Manual test commands
8. **Deployment Checklist** - Step-by-step deployment

## 🔑 Key Concepts

### Google Drive Webhooks

- **What:** Google Drive notifications that trigger when files change
- **Expiration:** Channels expire after 24 hours
- **Solution:** Auto-renew via scheduled Lambda every 12 hours

### Custom Validation Checks

The implementation includes 4 levels of validation:

1. **Webhook Signature** - Verify request authenticity
2. **Sync Token** - Prevent replaying old changes
3. **File Filtering** - Skip unsupported types/sizes
4. **Idempotency** - Prevent duplicate uploads

### State Management

Uses DynamoDB to track:
- Active webhook channels and expiration times
- Change tokens for resuming syncs
- Complete audit log of all file transfers

## 💡 Architecture

```
Google Drive (Files)
         │
         ├─ File created/modified
         │
         ▼
    [Webhook] (Event-driven, <5 seconds)
         │
         ▼
    [API Gateway]
         │
         ▼
    [Lambda Webhook Handler]
         ├─ Validate signature
         ├─ Query changes
         ├─ Filter files
         ├─ Check for duplicates
         │
         ▼
    [AWS S3] ← Files stored
    
    [Parallel: Channel Renewal Lambda]
    ├─ Scheduled every 12 hours
    ├─ Check channel expiration
    ├─ Renew if <6 hours remaining
    └─ Store state in DynamoDB
```

## 📊 Cost Estimate

| Component | Estimate |
|-----------|----------|
| Lambda (webhook + renewal) | $0.50–$5/month |
| API Gateway | Free (first 1M requests) |
| DynamoDB | $1–$2/month (on-demand) |
| S3 Storage | $0.023/GB/month |
| CloudWatch Logs | $0.50–$1/month |
| **Total** | **~$2–$9/month + storage** |

## ⚙️ Configuration

### Required Secrets (AWS Secrets Manager)

```json
{
  "google-drive-service-account": {
    "type": "service_account",
    "project_id": "your-project",
    "private_key_id": "...",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
    "client_email": "drive-to-s3@project.iam.gserviceaccount.com",
    "client_id": "..."
  },
  "gdrive-s3-config": {
    "GOOGLE_DRIVE_FOLDER_ID": "1ABC...",
    "S3_BUCKET": "my-data-bucket",
    "WEBHOOK_TOKEN": "random-secret-token"
  }
}
```

### Environment Variables (Lambda)

```python
WEBHOOK_URL = "https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod/webhook"
CHANNELS_TABLE = "gdrive_channels"
SYNC_LOG_TABLE = "gdrive_s3_sync_log"
S3_BUCKET = "my-data-bucket"
```

## 🧪 Testing

### Test Webhook Handler

```bash
aws lambda invoke \
  --function-name gdrive-webhook-handler \
  --payload '{
    "headers": {"X-Goog-Channel-Token": "your-token"},
    "body": "{\"folder_id\": \"your-folder-id\"}"
  }' \
  response.json
```

### Test Channel Renewal

```bash
aws lambda invoke \
  --function-name gdrive-channel-renewal \
  --payload '{"folder_id": "your-folder-id"}' \
  renewal.json
```

### Monitor Logs

```bash
aws logs tail /aws/lambda/gdrive-webhook-handler --follow
aws logs tail /aws/lambda/gdrive-channel-renewal --follow
```

## 📈 Monitoring

### CloudWatch Metrics

- `FilesProcessed` - Files successfully uploaded to S3
- `FilesSkipped` - Files filtered out (wrong type/size)
- `SyncFailures` - Upload errors
- `ChannelRenewalStatus` - Webhook channel renewal success/failure

### CloudWatch Alarms

Set up alerts for:
- Failed channel renewals (indicates potential downtime)
- High error rates (>5% failures)
- Webhook invocation latency (>10 seconds)

### DynamoDB Audit Log

Query sync history:

```bash
aws dynamodb scan \
  --table-name gdrive_s3_sync_log \
  --filter-expression "sync_status = :status" \
  --expression-attribute-values "{\":status\": {\"S\": \"failed\"}}"
```

## 🔧 Troubleshooting

### Common Issues

**Q: Webhooks stopped working**
- Check channel expiration in DynamoDB
- Verify renewal Lambda is running
- Review CloudWatch logs for errors

**Q: Files not syncing**
- Confirm service account has folder access
- Check file filtering rules
- Verify S3 bucket permissions

**Q: High latency**
- Review Lambda duration in CloudWatch
- Check Google Drive API quota
- Consider parallel uploads

**Q: Duplicate files in S3**
- Verify idempotency check is running
- Check MD5 hash comparison logic
- Review DynamoDB sync log

## 📖 Full Implementation Guide

For complete step-by-step instructions, see **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** (one-stop playbook).

This includes:
- Google Drive API setup
- Service account configuration
- DynamoDB schema design
- Lambda function code (complete, production-ready)
- Terraform infrastructure templates
- Deployment checklist
- Testing procedures

## 🚦 Getting Started

1. **Read** [STRATEGY_RANKING.md](STRATEGY_RANKING.md) to understand the options
2. **Review** [WEBHOOK_IMPLEMENTATION.md](WEBHOOK_IMPLEMENTATION.md) for full details
3. **Follow** the deployment checklist in WEBHOOK_IMPLEMENTATION.md
4. **Test** using the provided test commands
5. **Monitor** using CloudWatch dashboards

## 🤝 Contributing

This is a reference implementation. Feel free to:
- Adapt to your specific use case
- Customize validation rules
- Extend with additional checks
- Add support for other data sources

## 📝 License

MIT

## 👤 Author

Data Pipeline Team

---

**Questions or Issues?** Check [WEBHOOK_IMPLEMENTATION.md](WEBHOOK_IMPLEMENTATION.md) troubleshooting section or review CloudWatch logs for detailed error messages.
