# Tree of Thought: Google Drive to AWS S3 Continuous Migration

## 1. Problem Decomposition

**Core Requirements:**
- Real-time file detection in Google Drive
- Continuous transfer (not one-time)
- Automated workflow
- File created → S3 bucket updates

**Key Constraints:**
- Google Drive API rate limits (1,000 requests/100 seconds)
- S3 latency acceptable?
- File size range and volume?
- Cost sensitivity?
- Folder structure to preserve?

---

## 2. Solution Approaches (Ranked by Viability)

### **Strategy 1: Event-Driven (Google Drive Webhooks) ⭐ BEST**

**How it works:**
```
Google Drive (file created) 
  → Push notification to HTTP endpoint 
  → API Gateway 
  → Lambda function 
  → Fetch file from Google Drive 
  → Upload to S3
```

**Pros:**
- Near real-time (seconds latency)
- Event-driven (efficient, no polling waste)
- Scalable with AWS Lambda
- Cost-effective for moderate volume

**Cons:**
- Requires public HTTP endpoint
- Google Drive webhooks have 24-hour expiration (need refresh mechanism)
- Need to handle webhook verification

**Implementation:**
1. Set up Google Drive API with service account or OAuth
2. Create CloudWatch Rules or API Gateway + Lambda for webhook endpoint
3. Lambda: Validate webhook → fetch file metadata → download → upload to S3
4. Add retry/DLQ for failures

---

### **Strategy 2: Polling with Lambda + CloudWatch (Reliable Fallback)**

**How it works:**
```
CloudWatch Events (every N minutes) 
  → Lambda 
  → Query Google Drive changes API 
  → Download new/modified files 
  → Upload to S3
```

**Pros:**
- No webhook setup needed
- Handles all file changes (create, update, delete)
- Built-in retry with Lambda + DLQ
- Easy to schedule and monitor

**Cons:**
- Lag (5–30 min depending on schedule)
- Higher API call volume
- Not true real-time

**Implementation:**
1. CloudWatch Events rule (every 5–15 minutes)
2. Lambda with Google Drive API (watch for changes using `changeNotifications`)
3. Batch download and S3 upload

---

### **Strategy 3: Hybrid (Event + Polling)**

**How it works:**
- **Primary:** Webhooks for fast sync
- **Secondary:** Scheduled Lambda polling as fallback
  - Catches missed webhook events
  - Handles webhook failures
  - Periodically validates S3 matches Google Drive

**Pros:**
- Fault-tolerant
- Near real-time with safety net
- Handles transient failures

**Cons:**
- More complex
- Slightly higher cost

---

### **Strategy 4: Third-Party Integration Tools**

**Options:** Zapier, Make.com, PipedreamKey features:
- Zapier: Google Drive trigger → Webhook → AWS S3 action
- Make: Visual workflow builder
- PipeDream: Code-based, serverless

**Pros:**
- No infrastructure to manage
- GUI-based setup
- Built-in error handling

**Cons:**
- Monthly cost per automation (~$15–100)
- Rate limits and quotas
- Less control over workflow

---

## 3. Recommended Architecture

**For most use cases: Strategy 1 + Strategy 2 (Hybrid)**

```
┌─────────────────────────────────────┐
│ Google Drive (New File)              │
└────────────┬────────────────────────┘
             │
        ┌────┴──────┐
        │            │
    (Fast Path)  (Fallback)
        │            │
        ▼            ▼
    ┌───────────┐  ┌──────────────┐
    │ Webhook   │  │CloudWatch    │
    │(Event)    │  │(Every 5 min) │
    └─────┬─────┘  └──────┬───────┘
          │               │
          └───────┬───────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ Lambda Function     │
        │ - Validate/auth     │
        │ - Fetch from GDrive │
        │ - Upload to S3      │
        │ - Log/retry logic   │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ AWS S3 Bucket       │
        │ (Data stored)       │
        └─────────────────────┘
```

---

## 4. Implementation Checklist

### **Phase 1: Setup**
- [ ] Create AWS S3 bucket
- [ ] Create IAM role for Lambda (S3 write permissions)
- [ ] Set up Google Drive API + service account (or OAuth)
- [ ] Store API credentials in AWS Secrets Manager

### **Phase 2: Webhook Path (Primary)**
- [ ] Create API Gateway endpoint
- [ ] Implement Lambda webhook handler
  - Validate Google Drive signature
  - Fetch file metadata
  - Download file
  - Upload to S3
- [ ] Set up Google Drive channel (watch/subscription)
- [ ] Implement webhook refresh (24-hour expiration)

### **Phase 3: Polling Fallback**
- [ ] Create CloudWatch rule (5–15 min schedule)
- [ ] Create polling Lambda function
  - Query `changes.list()` API
  - Track change tokens
  - Download and upload new files
- [ ] Add DLQ for failed transfers

### **Phase 4: Monitoring & Reliability**
- [ ] CloudWatch logs for all Lambda executions
- [ ] SNS alerts for failures
- [ ] DLQ monitoring
- [ ] Periodic reconciliation (compare S3 vs Google Drive)
- [ ] Idempotency checks (prevent duplicates)

---

## 5. Cost Estimate (Rough)

| Component | Monthly Cost |
|-----------|-------------|
| Lambda (webhook + polling) | $0.50–$5 |
| API calls (Google Drive) | Free (within limits) |
| S3 storage | Varies (e.g., $0.023/GB) |
| CloudWatch logs | $0.50–$2 |
| **Total** | **$1–$7 + storage** |

---

## 6. Key Code Patterns

**Webhook handler pseudocode:**
```python
@app.route('/webhook', methods=['POST'])
def handle_drive_webhook():
    # Validate Google signature
    validate_signature(request)
    
    # Fetch file from Google Drive
    file_metadata = drive_service.files().get(fileId=file_id).execute()
    file_content = download_from_drive(file_id)
    
    # Upload to S3
    s3_client.put_object(Bucket='my-bucket', Key=file_metadata['name'], Body=file_content)
    
    return 200
```

**Polling handler pseudocode:**
```python
def poll_drive_changes():
    # Get last change token from DynamoDB/S3
    last_token = get_last_change_token()
    
    # Query changes since last check
    changes = drive_service.changes().list(pageToken=last_token).execute()
    
    for change in changes['changes']:
        if change['type'] == 'file' and not change['removed']:
            file_id = change['fileId']
            download_and_upload_to_s3(file_id)
    
    # Save new change token
    save_change_token(changes['newStartPageToken'])
```

---

## 7. Gotchas & Mitigations

| Issue | Mitigation |
|-------|-----------|
| Webhook expiration (24h) | Refresh mechanism + polling fallback |
| Large files (>5GB) | Use multipart upload, S3 Transfer Acceleration |
| Rate limits | Implement exponential backoff, queuing |
| Duplicate uploads | Idempotency check (S3 object metadata/hash) |
| Permission errors | IAM roles, error logging, DLQ |
| Folder structure loss | Store Google Drive path in S3 metadata |

---

## **Recommendation: Start with Strategy 1 + 2**

1. **Week 1:** Set up webhook + Lambda (primary path)
2. **Week 2:** Add polling as fallback
3. **Week 3:** Add monitoring and reconciliation

This gives you fast sync with reliability at minimal cost.
