# Internal Technical Documentation: Google Drive to AWS S3 Webhook Pipeline

**Document Version:** 1.0  
**Last Updated:** January 25, 2026  
**Audience:** Engineering Team, DevOps, Solutions Architects  
**Confidentiality:** Internal Use Only

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Detailed Component Breakdown](#detailed-component-breakdown)
4. [Workflow & Data Flow](#workflow--data-flow)
5. [Implementation Guide](#implementation-guide)
6. [State Management & Persistence](#state-management--persistence)
7. [Error Handling & Recovery](#error-handling--recovery)
8. [Performance & Scalability](#performance--scalability)
9. [Security Considerations](#security-considerations)
10. [Operations & Maintenance](#operations--maintenance)
11. [Testing Strategy](#testing-strategy)
12. [Troubleshooting Guide](#troubleshooting-guide)

---

## Executive Summary

The Google Drive to AWS S3 Webhook Pipeline is a real-time, event-driven data synchronization system that automatically transfers files from Google Drive to AWS S3 storage as they are created or modified.

**Key Characteristics:**
- **Event-Driven:** Uses Google Drive webhooks (push notifications) for real-time synchronization
- **Serverless:** Entirely Lambda-based with zero servers to manage
- **Scalable:** Can handle 1,000s of concurrent file uploads
- **Self-Healing:** Automatic channel renewal prevents synchronization interruptions
- **Cost-Efficient:** ~$2–9/month for typical usage
- **Auditable:** Complete logging of all sync operations

**Architecture Decision:** Webhook approach chosen over polling due to:
- **Speed:** <5 second latency vs 5–30 minutes with polling
- **Efficiency:** Event-driven eliminates unnecessary API calls
- **Cost:** Lower API usage and Lambda invocations
- **Reliability:** Custom validation checks prevent data integrity issues

---

## System Architecture

### High-Level Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         GOOGLE DRIVE                               │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ User uploads/modifies files in monitored folder             │ │
│  │ Google Drive detects change                                 │ │
│  │ Sends webhook notification                                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────┬───────────────────────────────────────────┘
                         │
                         │ HTTPS POST
                         │ X-Goog-Channel-Token: <token>
                         │ X-Goog-Message-Number: <number>
                         │ X-Goog-Resource-ID: <resource_id>
                         │
                         ▼
    ┌────────────────────────────────────────────────┐
    │           AWS API GATEWAY                      │
    │                                                │
    │  ┌──────────────────────────────────────────┐ │
    │  │ POST /webhook                            │ │
    │  │ - Route to Lambda                        │ │
    │  │ - Add API key validation (optional)      │ │
    │  │ - Enable CloudWatch logging              │ │
    │  └──────────────────────────────────────────┘ │
    └────────────────────┬───────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────┐
    │    AWS LAMBDA: WEBHOOK HANDLER                │
    │    (gdrive-webhook-handler)                   │
    │                                                │
    │  STAGE 1: VALIDATION                          │
    │  ┌──────────────────────────────────────────┐ │
    │  │ • Verify webhook signature               │ │
    │  │ • Validate sync token                    │ │
    │  │ • Check request authenticity             │ │
    │  └──────────────────────────────────────────┘ │
    │                   │                            │
    │                   ▼                            │
    │  STAGE 2: DATA RETRIEVAL                      │
    │  ┌──────────────────────────────────────────┐ │
    │  │ • Connect to Google Drive API            │ │
    │  │ • Query changes.list() with token        │ │
    │  │ • Fetch file metadata                    │ │
    │  │ • Download file content                  │ │
    │  └──────────────────────────────────────────┘ │
    │                   │                            │
    │                   ▼                            │
    │  STAGE 3: FILTERING & VALIDATION              │
    │  ┌──────────────────────────────────────────┐ │
    │  │ • Skip folders/shortcuts                 │ │
    │  │ • Check file size limits                 │ │
    │  │ • Validate file type                     │ │
    │  │ • Check idempotency (MD5)                │ │
    │  └──────────────────────────────────────────┘ │
    │                   │                            │
    │                   ▼                            │
    │  STAGE 4: UPLOAD & LOGGING                    │
    │  ┌──────────────────────────────────────────┐ │
    │  │ • Upload to S3 with metadata             │ │
    │  │ • Log to DynamoDB sync table             │ │
    │  │ • Publish metrics to CloudWatch          │ │
    │  │ • Return status response                 │ │
    │  └──────────────────────────────────────────┘ │
    └────────────────────┬───────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
           ▼             ▼             ▼
    ┌───────────┐  ┌──────────────┐  ┌────────────┐
    │  AWS S3   │  │   DynamoDB   │  │CloudWatch  │
    │           │  │   Sync Log   │  │  Metrics   │
    │ Data Files│  │              │  │            │
    └───────────┘  └──────────────┘  └────────────┘


PARALLEL: CHANNEL RENEWAL (Every 12 Hours)

    ┌────────────────────────────────────────────────┐
    │      AWS CLOUDWATCH EVENTS                     │
    │      (cron: rate(12 hours))                    │
    └────────────────────┬───────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────┐
    │  AWS LAMBDA: CHANNEL RENEWAL                   │
    │  (gdrive-channel-renewal)                      │
    │                                                │
    │  1. Load channel info from DynamoDB            │
    │  2. Check expiration (< 6 hours left?)         │
    │  3. Stop old channel if renewing               │
    │  4. Create new webhook channel                 │
    │  5. Update DynamoDB with new channel info      │
    │  6. Send SNS alert if renewal fails            │
    └────────────────────┬───────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────┐
    │      DynamoDB: gdrive_channels                 │
    │                                                │
    │  Stores current webhook channel state          │
    │  - Channel ID & Resource ID                    │
    │  - Expiration timestamp                        │
    │  - Status (active/renewing/failed)             │
    │  - Created/renewed timestamps                  │
    └────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS ECOSYSTEM                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Secrets Manager                                      │  │
│  │ • google-drive-service-account (JSON)               │  │
│  │ • gdrive-s3-config (WEBHOOK_TOKEN, folder ID)       │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │ (Read on startup)                           │
│               │                                             │
│  ┌────────────▼─────────────────────────────────────────┐  │
│  │ Lambda Execution Role (IAM)                         │  │
│  │ • s3:PutObject, s3:GetObject                        │  │
│  │ • dynamodb:PutItem, GetItem, UpdateItem            │  │
│  │ • secretsmanager:GetSecretValue                     │  │
│  │ • logs:CreateLogGroup, CreateLogStream, PutLogEvents│ │
│  │ • cloudwatch:PutMetricData                          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ API Gateway (HTTP)                                 │  │
│  │ • Route: POST /webhook                             │  │
│  │ • Auth: X-Goog-Channel-Token header validation     │  │
│  │ • Logging: CloudWatch Logs                         │  │
│  │ • Metrics: Invocations, errors, duration           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Lambda: Webhook Handler (gdrive-webhook-handler)   │  │
│  │ Memory: 512 MB | Timeout: 60 seconds               │  │
│  │ Concurrent Executions: 100 (auto-scale)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Lambda: Channel Renewal (gdrive-channel-renewal)   │  │
│  │ Memory: 256 MB | Timeout: 30 seconds               │  │
│  │ Scheduled: Every 12 hours (CloudWatch Events)      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ DynamoDB Tables (On-Demand Billing)                │  │
│  │                                                     │  │
│  │ 1. gdrive_channels                                 │  │
│  │    Partition Key: folder_id (S)                    │  │
│  │    Attributes: channel_id, resource_id,            │  │
│  │                expiration, status                  │  │
│  │                                                     │  │
│  │ 2. gdrive_s3_sync_log                              │  │
│  │    Partition Key: file_id (S)                      │  │
│  │    Sort Key: timestamp (N)                         │  │
│  │    Attributes: file_name, status, error            │  │
│  │    TTL: 90 days (auto-cleanup)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ S3 Bucket (my-data-bucket)                         │  │
│  │ • Versioning: Disabled (single version)            │  │
│  │ • Lifecycle: Archive to Glacier after 90 days     │  │
│  │ • Encryption: SSE-S3 (default)                     │  │
│  │ • Logging: All API calls to separate bucket        │  │
│  │ • Metadata: source, uploaded-via, md5              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ CloudWatch                                          │  │
│  │                                                     │  │
│  │ Metrics:                                            │  │
│  │ • FilesProcessed (count/min)                       │  │
│  │ • FilesSkipped (count/min)                         │  │
│  │ • SyncFailures (count/min)                         │  │
│  │ • WebhookLatency (milliseconds)                    │  │
│  │ • ChannelRenewalStatus (1=success, 0=fail)        │  │
│  │                                                     │  │
│  │ Alarms:                                             │  │
│  │ • HighErrorRate (>5% failures) → SNS              │  │
│  │ • ChannelRenewalFailure → SNS                      │  │
│  │ • LambdaDuration > 30s → SNS                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SNS Topic (gdrive-s3-alerts)                        │  │
│  │ • Subscribers: Email, PagerDuty (optional)         │  │
│  │ • Triggered by: CloudWatch Alarms                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Breakdown

### 1. Google Drive API

**Authentication:**
- Uses **Service Account** (not user OAuth)
- Service account email: `drive-to-s3@project-id.iam.gserviceaccount.com`
- Credentials stored in AWS Secrets Manager (JSON key file)
- Scopes: `https://www.googleapis.com/auth/drive.readonly`

**API Methods Used:**

```python
# 1. Watch for changes (creates webhook channel)
service.files().watch(fileId=folder_id, body={
    'id': channel_id,
    'type': 'webhook',
    'address': 'https://api.example.com/webhook',
    'expiration': expires_ms
}).execute()

# 2. Stop watching (cleanup old channel)
service.files().stop(fileId=folder_id, body={
    'id': channel_id,
    'resourceId': resource_id
}).execute()

# 3. Query changes since last sync
service.changes().list(
    pageToken=change_token,
    spaces='drive',
    pageSize=100
).execute()

# 4. Get file metadata
service.files().get(
    fileId=file_id,
    fields='id,name,mimeType,size,createdTime,modifiedTime'
).execute()

# 5. Download file
service.files().get_media(fileId=file_id).execute()
```

**Webhook Payload Structure:**

```json
{
  "kind": "drive#changes",
  "changes": [
    {
      "kind": "drive#change",
      "id": "12345",
      "fileId": "1ABC...XYZ",
      "file": {
        "kind": "drive#file",
        "id": "1ABC...XYZ",
        "name": "data.csv",
        "mimeType": "text/csv",
        "size": "1024",
        "createdTime": "2026-01-25T10:30:00Z",
        "modifiedTime": "2026-01-25T10:35:00Z"
      },
      "removed": false
    }
  ],
  "newStartPageToken": "12345"
}
```

### 2. API Gateway

**Route Configuration:**
```
POST /webhook HTTP/1.1
Host: {api-id}.execute-api.{region}.amazonaws.com
X-Goog-Channel-Token: {google-webhook-token}
X-Goog-Message-Number: {message-number}
X-Goog-Resource-ID: {resource-id}
```

**Response Codes:**
- **200 OK** - Successfully processed
- **202 Accepted** - Queued for processing (async)
- **400 Bad Request** - Invalid token or payload
- **401 Unauthorized** - Authentication failed
- **500 Internal Server Error** - Lambda execution error

**Rate Limiting:**
- API Gateway: 10,000 requests/second per account
- Our volume: Typically <10 requests/minute
- No rate limiting needed for webhook

### 3. Lambda: Webhook Handler

**Function Configuration:**
- **Memory:** 512 MB (balance between cost and performance)
- **Timeout:** 60 seconds (max for API Gateway)
- **Concurrent Executions:** 100 (auto-scaling)
- **Ephemeral Storage:** 512 MB (sufficient for file downloads)

**Execution Flow (Pseudocode):**

```
FUNCTION webhook_handler(event, context)
  
  STAGE 1: VALIDATE
    ├─ Check X-Goog-Channel-Token header
    ├─ Verify signature matches WEBHOOK_TOKEN
    └─ Return 401 if invalid
  
  STAGE 2: AUTHENTICATE & CONNECT
    ├─ Retrieve Google service account from Secrets Manager
    ├─ Build authenticated Google Drive service
    ├─ Retrieve folder_id from event (or config)
    └─ Return 400 if missing required parameters
  
  STAGE 3: QUERY CHANGES
    ├─ Get current channel info from DynamoDB
    ├─ Extract change_token from channel record
    ├─ Call changes.list(pageToken=change_token)
    ├─ Retrieve up to 100 changes in batch
    └─ Return 400 if change_token invalid
  
  STAGE 4: PROCESS EACH FILE
    FOR EACH change IN changes:
      
      STEP 4.1: SKIP IF REMOVED
        IF change.removed == true:
          ├─ Log deletion event
          └─ CONTINUE to next change
      
      STEP 4.2: FILTER BY TYPE
        ├─ Skip if mimeType == 'folder'
        ├─ Skip if shortcutDetails present
        ├─ Skip if not in allowed_extensions
        └─ LOG as 'skipped'
      
      STEP 4.3: CHECK SIZE
        ├─ IF size > 100MB:
        │   ├─ LOG as 'skipped' (too large)
        │   └─ CONTINUE
        └─ PROCEED to download
      
      STEP 4.4: CHECK IDEMPOTENCY
        ├─ Try S3 head_object(Key=file_name)
        ├─ IF exists:
        │   ├─ Calculate MD5 of local file
        │   ├─ Compare with existing ETag
        │   ├─ IF match: LOG as 'skipped' (duplicate)
        │   ├─ IF different: overwrite (update)
        │   └─ CONTINUE
        └─ IF not exists: proceed to download
      
      STEP 4.5: DOWNLOAD FROM GOOGLE DRIVE
        ├─ Call get_media(fileId)
        ├─ Stream content to memory
        ├─ Calculate MD5 hash
        └─ Handle connection errors
      
      STEP 4.6: UPLOAD TO S3
        ├─ Call put_object(
        │     Bucket=S3_BUCKET,
        │     Key=file_name,
        │     Body=content,
        │     Metadata={
        │       'source': 'google-drive',
        │       'uploaded-via': 'webhook',
        │       'md5': md5_hash
        │     }
        │   )
        ├─ Catch S3 errors (permissions, quota)
        └─ LOG result
      
      STEP 4.7: LOG SYNC EVENT
        ├─ Write to DynamoDB gdrive_s3_sync_log
        ├─ Include:
        │   ├─ file_id
        │   ├─ timestamp
        │   ├─ file_name
        │   ├─ status (uploaded/skipped/failed)
        │   └─ error (if any)
        └─ Set TTL for 90 days
  
  END LOOP
  
  STAGE 5: PUBLISH METRICS
    ├─ CloudWatch.put_metric_data(
    │     Namespace='GoogleDrive-S3-Pipeline',
    │     MetricData=[
    │       {'MetricName': 'FilesProcessed', 'Value': count},
    │       {'MetricName': 'FilesSkipped', 'Value': count},
    │       {'MetricName': 'SyncFailures', 'Value': count}
    │     ]
    │   )
    └─ Include dimensions: folder_id, status
  
  STAGE 6: RETURN RESPONSE
    └─ Return {
         'statusCode': 200,
         'body': {
           'processed': X,
           'skipped': Y,
           'failed': Z,
           'total': X+Y+Z
         }
       }

END FUNCTION
```

### 4. Lambda: Channel Renewal

**Execution Flow:**

```
FUNCTION channel_renewal(event, context)
  
  STAGE 1: LOAD CONFIGURATION
    ├─ Get folder_id from event (or scan DynamoDB)
    ├─ Retrieve Google service account from Secrets
    ├─ Load current channel from DynamoDB
    └─ Calculate time until expiration
  
  STAGE 2: CHECK IF RENEWAL NEEDED
    ├─ IF time_to_expiry > 6 hours:
    │   ├─ LOG: "Channel still valid"
    │   └─ RETURN success
    ├─ ELSE (expiring soon):
    │   └─ PROCEED to renewal
  
  STAGE 3: STOP OLD CHANNEL
    ├─ Call files().stop(fileId, {id, resourceId})
    ├─ Log success/failure (may fail if already expired)
    └─ CONTINUE regardless of failure
  
  STAGE 4: CREATE NEW CHANNEL
    ├─ Generate new channel_id: f"gdrive-s3-{folder_id}-{uuid}"
    ├─ Set expiration to now + 24 hours
    ├─ Call files().watch(...) with new channel_id
    ├─ Retrieve resource_id from response
    └─ Handle errors: quota exceeded, permissions
  
  STAGE 5: PERSIST NEW CHANNEL STATE
    ├─ Write to DynamoDB:
    │   ├─ folder_id (partition key)
    │   ├─ channel_id (new)
    │   ├─ resource_id (new)
    │   ├─ expiration (timestamp)
    │   ├─ created_at (old)
    │   ├─ renewed_at (now)
    │   └─ status: 'renewed'
    └─ Handle DynamoDB write errors
  
  STAGE 6: PUBLISH METRICS
    ├─ CloudWatch.put_metric_data:
    │   ├─ ChannelRenewalStatus: 1 (success)
    │   ├─ Include folder_id dimension
    │   └─ Timestamp: now
    └─ Include old expiration time as metadata
  
  STAGE 7: HANDLE FAILURES
    ├─ TRY/CATCH around entire renewal process
    ├─ IF error:
    │   ├─ LOG error details
    │   ├─ Publish SNS alert to ops team
    │   ├─ Update status to 'failed' in DynamoDB
    │   ├─ CloudWatch metric: ChannelRenewalStatus = 0
    │   └─ RETURN error response
    └─ ELSE:
        └─ RETURN success
  
  STAGE 8: RETURN RESPONSE
    └─ Return {
         'statusCode': 200,
         'body': {
           'channel_renewed': true,
           'new_expiration': expiration_timestamp,
           'folder_id': folder_id
         }
       }

END FUNCTION
```

### 5. DynamoDB Tables

**Table 1: gdrive_channels**

```
Primary Key: folder_id (String)

Attributes:
  folder_id (S) [PARTITION KEY]
    └─ Google Drive folder ID being monitored
  
  channel_id (S)
    └─ Current webhook channel ID
    └─ Format: "gdrive-s3-{folder_id}-{uuid}"
  
  resource_id (S)
    └─ Google's internal resource ID for this watch
  
  expiration (N)
    └─ Unix timestamp when channel expires
    └─ Renewed when < 6 hours remaining
  
  created_at (N)
    └─ Unix timestamp when original channel created
  
  renewed_at (N, Optional)
    └─ Unix timestamp of last renewal
  
  status (S)
    └─ Values: 'active', 'renewing', 'failed'
  
  last_change_token (S, Optional)
    └─ Last valid change token from Google
    └─ Used to resume syncing after failure

GSI (Global Secondary Index):
  status-expiration-index
    └─ Partition Key: status
    └─ Sort Key: expiration
    └─ Use case: Query all expiring channels for renewal
```

**Table 2: gdrive_s3_sync_log**

```
Primary Key: file_id (String), timestamp (Number)

Attributes:
  file_id (S) [PARTITION KEY]
    └─ Google Drive file ID
  
  timestamp (N) [SORT KEY]
    └─ Unix timestamp when sync occurred
    └─ Allows multiple entries per file
  
  file_name (S)
    └─ Name of the file (e.g., "data.csv")
  
  file_size (N, Optional)
    └─ Size in bytes
  
  status (S)
    └─ Values: 'uploaded', 'skipped', 'failed'
  
  error (S, Optional)
    └─ Error message if status == 'failed'
  
  s3_key (S, Optional)
    └─ S3 path where file was uploaded
  
  duration_ms (N, Optional)
    └─ Time taken to process file
  
  md5_hash (S, Optional)
    └─ MD5 hash of uploaded file
    └─ Used for idempotency checks

TTL Configuration:
  TTL Attribute: timestamp
  TTL Duration: 90 days (7,776,000 seconds)
  └─ Automatically delete old log entries after 90 days
  └─ Saves storage costs

GSI (Global Secondary Index):
  status-timestamp-index
    └─ Partition Key: status
    └─ Sort Key: timestamp
    └─ Use case: Query failures in time range
```

### 6. S3 Bucket Configuration

**Bucket Name:** `my-data-bucket` (adjust to your naming)

**Key Features:**

```yaml
Versioning: Disabled
  └─ Each upload overwrites previous version
  └─ Saves storage costs (single version per file)

Encryption:
  └─ SSE-S3 (Server-Side Encryption)
  └─ Default encryption, no key management needed

Lifecycle Policies:
  Rule 1: Archive to Glacier
    └─ Days: 90
    └─ Storage Class: GLACIER
    └─ Saves retrieval costs for old data
  
  Rule 2: Delete Incomplete Multipart
    └─ Days: 7
    └─ Cleans up aborted uploads

Object Metadata (added by Lambda):
  {
    "source": "google-drive",
    "uploaded-via": "webhook",
    "md5": "abc123...",
    "google-file-id": "1ABC...XYZ",
    "sync-timestamp": "1674691800"
  }

Logging:
  └─ All API calls logged to separate bucket
  └─ Bucket: my-data-bucket-logs
  └─ Prefix: s3-access-logs/
  └─ Use for compliance and debugging

Block Public Access:
  └─ All public access blocked
  └─ Only IAM roles can access

CORS (if needed for web access):
  └─ Configure only if frontend requires direct S3 access
```

---

## Workflow & Data Flow

### End-to-End Workflow

**Step 1: Initial Setup (One-time)**
```
Engineer
  ├─ Creates Google Service Account
  ├─ Shares Google Drive folder with service account
  ├─ Creates AWS resources (Lambda, DynamoDB, S3)
  ├─ Deploys Lambda functions
  ├─ Stores credentials in Secrets Manager
  ├─ Runs channel-renewal Lambda manually
  │   └─ Creates initial webhook channel
  │   └─ Stores channel info in DynamoDB
  └─ Tests webhook with sample file upload
```

**Step 2: Normal Operation (Ongoing)**
```
User in Google Drive
  └─ Uploads/modifies file: "sales_data.csv"
       │
       ▼
   Google Drive
     └─ Detects change
     └─ Queries webhook channel list
     └─ Sends HTTPS POST to: {api-gateway}/webhook
        │
        │ Headers:
        │   X-Goog-Channel-Token: {our-token}
        │   X-Goog-Message-Number: 12345
        │   X-Goog-Resource-ID: resource-xyz
        │
        │ Body:
        │   {
        │     "changes": [{
        │       "fileId": "1ABC...",
        │       "file": {
        │         "name": "sales_data.csv",
        │         "mimeType": "text/csv",
        │         "size": "45678"
        │       }
        │     }]
        │   }
        │
        ▼
   API Gateway
     ├─ Receives POST /webhook
     ├─ Routes to Lambda
     ├─ Lambda cold start (if needed)
     └─ Executes webhook handler
        │
        ├─ VALIDATE:
        │   ├─ Check X-Goog-Channel-Token header
        │   └─ Verify it matches stored WEBHOOK_TOKEN
        │
        ├─ AUTHENTICATE:
        │   ├─ Load Google service account from Secrets Manager
        │   └─ Create authenticated Google Drive API client
        │
        ├─ FILTER:
        │   ├─ Is it a CSV file? ✓ Yes
        │   ├─ Is it < 100 MB? ✓ Yes (45 KB)
        │   └─ Is it already in S3 with same content? ✗ No (new file)
        │
        ├─ DOWNLOAD:
        │   ├─ Call Google Drive API: files().get_media(fileId=1ABC...)
        │   ├─ Stream content to memory
        │   └─ Calculate MD5: "abc123..."
        │
        ├─ UPLOAD TO S3:
        │   ├─ Call s3.put_object(
        │   │     Bucket='my-data-bucket',
        │   │     Key='sales_data.csv',
        │   │     Body=<file-content>,
        │   │     Metadata={
        │   │       'source': 'google-drive',
        │   │       'md5': 'abc123...',
        │   │       'google-file-id': '1ABC...'
        │   │     }
        │   │   )
        │   └─ S3 confirms upload
        │
        ├─ LOG:
        │   ├─ Write to DynamoDB:
        │   │   {
        │   │     'file_id': '1ABC...',
        │   │     'timestamp': 1674691800,
        │   │     'file_name': 'sales_data.csv',
        │   │     'status': 'uploaded',
        │   │     's3_key': 'sales_data.csv'
        │   │   }
        │   └─ TTL set to 90 days from now
        │
        ├─ METRICS:
        │   ├─ CloudWatch.put_metric_data:
        │   │   ├─ FilesProcessed: 1
        │   │   ├─ FilesSkipped: 0
        │   │   └─ SyncFailures: 0
        │   └─ Duration: 2.5 seconds
        │
        └─ RETURN:
           {
             "statusCode": 200,
             "body": {
               "processed": 1,
               "skipped": 0,
               "failed": 0,
               "total": 1
             }
           }
```

**Step 3: Scheduled Channel Renewal (Every 12 hours)**
```
CloudWatch Events
  └─ Trigger: rate(12 hours)
  └─ Invokes Lambda: gdrive-channel-renewal
     │
     ├─ LOAD CHANNEL:
     │   ├─ Query DynamoDB for folder_id
     │   ├─ Retrieve: channel_id, expiration
     │   └─ Calculate: time_until_expiry
     │
     ├─ CHECK IF RENEWAL NEEDED:
     │   ├─ IF expiry > 6 hours:
     │   │   └─ LOG: "Channel still valid, no renewal needed"
     │   │   └─ RETURN success
     │   │
     │   └─ IF expiry <= 6 hours:
     │       └─ PROCEED to renewal
     │
     ├─ STOP OLD CHANNEL:
     │   ├─ Call: files().stop(fileId, {id, resourceId})
     │   └─ LOG result (may fail if already expired)
     │
     ├─ CREATE NEW CHANNEL:
     │   ├─ Generate new channel_id
     │   ├─ Call: files().watch(fileId, {id, address, expiration})
     │   ├─ Receive: new resource_id
     │   └─ Set expiration: now + 24 hours
     │
     ├─ PERSIST:
     │   ├─ Update DynamoDB:
     │   │   {
     │   │     'folder_id': key,
     │   │     'channel_id': new_id,
     │   │     'resource_id': new_resource_id,
     │   │     'expiration': new_expiration_timestamp,
     │   │     'renewed_at': now,
     │   │     'status': 'renewed'
     │   │   }
     │   └─ Confirm write
     │
     ├─ METRICS:
     │   └─ CloudWatch: ChannelRenewalStatus = 1 (success)
     │
     └─ RETURN:
        {
          "statusCode": 200,
          "body": {
            "channel_renewed": true,
            "new_expiration": 1674778200
          }
        }
```

---

## Implementation Guide

### Prerequisites

**Software:**
- Python 3.9+ (for Lambda runtime)
- Terraform 1.0+ (for IaC)
- AWS CLI v2
- Git

**AWS Services:**
- Lambda
- API Gateway (HTTP API)
- DynamoDB
- S3
- Secrets Manager
- CloudWatch Logs
- CloudWatch Metrics
- SNS (optional, for alerting)

**Google Cloud:**
- Google Cloud Project with Drive API enabled
- Service Account with Editor access to target Drive folder

### Phase 1: Google Drive Setup

**1.1 Create Service Account**

```bash
# In Google Cloud Console
gcloud iam service-accounts create drive-to-s3 \
  --display-name="Drive to S3 Pipeline"

# Grant Drive API access (at folder level, not project-wide)
# In Google Drive: Share folder with service account email
```

**1.2 Create and Download Key**

```bash
# Generate key
gcloud iam service-accounts keys create key.json \
  --iam-account=drive-to-s3@project-id.iam.gserviceaccount.com

# Contents of key.json:
{
  "type": "service_account",
  "project_id": "my-project",
  "private_key_id": "...",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n",
  "client_email": "drive-to-s3@project-id.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### Phase 2: AWS Infrastructure

**2.1 Create IAM Role**

```terraform
resource "aws_iam_role" "lambda_execution_role" {
  name = "gdrive-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Attach policies
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda-policy"
  role = aws_iam_role.lambda_execution_role.id

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
          "dynamodb:UpdateItem",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.channels.arn,
          aws_dynamodb_table.sync_log.arn
        ]
      },
      {
        Effect = "Allow"
        Action = "secretsmanager:GetSecretValue"
        Resource = "arn:aws:secretsmanager:*:*:secret:google-drive*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = "cloudwatch:PutMetricData"
        Resource = "*"
      }
    ]
  })
}
```

**2.2 Create DynamoDB Tables**

```terraform
resource "aws_dynamodb_table" "channels" {
  name           = "gdrive_channels"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "folder_id"

  attribute {
    name = "folder_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "expiration"
    type = "N"
  }

  global_secondary_index {
    name            = "status-expiration-index"
    hash_key        = "status"
    range_key       = "expiration"
    projection_type = "ALL"
  }

  tags = {
    Name = "Google Drive Webhook Channels"
  }
}

resource "aws_dynamodb_table" "sync_log" {
  name           = "gdrive_s3_sync_log"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "file_id"
  range_key      = "timestamp"

  attribute {
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "status"
    type = "S"
  }

  ttl {
    attribute_name = "timestamp"
    enabled        = true
  }

  global_secondary_index {
    name            = "status-timestamp-index"
    hash_key        = "status"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  tags = {
    Name = "Google Drive S3 Sync Log"
  }
}
```

**2.3 Create S3 Bucket**

```terraform
resource "aws_s3_bucket" "data_bucket" {
  bucket = "my-org-data-bucket"
}

resource "aws_s3_bucket_versioning" "data_bucket_versioning" {
  bucket = aws_s3_bucket.data_bucket.id
  
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket_encryption" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_bucket_lifecycle" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    id     = "archive-to-glacier"
    status = "Enabled"

    transitions {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}
```

**2.4 Create Secrets Manager Secrets**

```bash
# Store Google service account credentials
aws secretsmanager create-secret \
  --name google-drive-service-account \
  --secret-string file://key.json

# Store configuration
aws secretsmanager create-secret \
  --name gdrive-s3-config \
  --secret-string '{
    "GOOGLE_DRIVE_FOLDER_ID": "1ABC...XYZ",
    "S3_BUCKET": "my-org-data-bucket",
    "WEBHOOK_TOKEN": "super-secret-random-token-here"
  }'
```

### Phase 3: Deploy Lambda Functions

**3.1 Package Dependencies**

```bash
# Create deployment package
mkdir lambda_package
cd lambda_package

# Install dependencies
pip install -r requirements.txt -t .

# Include lambda code
cp ../lambda_handler.py .

# Create zip
zip -r ../lambda_function.zip .
```

**3.2 Deploy Webhook Handler**

```terraform
resource "aws_lambda_function" "webhook_handler" {
  filename         = "lambda_function.zip"
  function_name    = "gdrive-webhook-handler"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_handler.webhook_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512
  
  source_code_hash = filebase64sha256("lambda_function.zip")

  environment {
    variables = {
      S3_BUCKET     = aws_s3_bucket.data_bucket.id
      CHANNELS_TABLE = aws_dynamodb_table.channels.name
      SYNC_LOG_TABLE = aws_dynamodb_table.sync_log.name
    }
  }

  reserved_concurrent_executions = 100
}
```

**3.3 Deploy Channel Renewal Function**

```terraform
resource "aws_lambda_function" "channel_renewal" {
  filename         = "lambda_function.zip"
  function_name    = "gdrive-channel-renewal"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_handler.channel_renewal"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256
  
  source_code_hash = filebase64sha256("lambda_function.zip")

  environment {
    variables = {
      CHANNELS_TABLE = aws_dynamodb_table.channels.name
    }
  }
}
```

### Phase 4: API Gateway Setup

```terraform
resource "aws_apigatewayv2_api" "webhook_api" {
  name          = "gdrive-webhook"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "webhook_integration" {
  api_id           = aws_apigatewayv2_api.webhook_api.id
  integration_type = "AWS_LAMBDA"
  integration_method = "POST"
  payload_format_version = "2.0"
  target = aws_lambda_function.webhook_handler.arn
}

resource "aws_apigatewayv2_route" "webhook_route" {
  api_id    = aws_apigatewayv2_api.webhook_api.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.webhook_integration.id}"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.webhook_api.id
  name        = "prod"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format          = jsonencode({
      requestId      = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      requestTime   = "$context.requestTime"
      httpMethod    = "$context.httpMethod"
      routeKey      = "$context.routeKey"
      status        = "$context.status"
      protocol      = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integration.latency"
    })
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhook_api.execution_arn}/*"
}
```

### Phase 5: CloudWatch Events (Scheduler)

```terraform
resource "aws_cloudwatch_event_rule" "channel_renewal_schedule" {
  name                = "gdrive-channel-renewal-schedule"
  description         = "Trigger channel renewal every 12 hours"
  schedule_expression = "rate(12 hours)"
}

resource "aws_cloudwatch_event_target" "channel_renewal_lambda" {
  rule      = aws_cloudwatch_event_rule.channel_renewal_schedule.name
  target_id = "GdriveChannelRenewal"
  arn       = aws_lambda_function.channel_renewal.arn
  
  input = jsonencode({
    operation = "renew_all_channels"
  })
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.channel_renewal.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.channel_renewal_schedule.arn
}
```

---

## State Management & Persistence

### DynamoDB State Model

**Channels Table Life Cycle:**

```
[CREATED]
  └─ New entry in gdrive_channels
  ├─ folder_id: "1ABC...XYZ"
  ├─ channel_id: "gdrive-s3-1ABC...XYZ-uuid123"
  ├─ resource_id: "resource-id-from-google"
  ├─ expiration: 1674778200 (now + 24 hours)
  ├─ created_at: 1674691800
  ├─ status: "active"
  └─ Time until expiry: 86,400 seconds (24 hours)

    [RUNS NORMALLY]
    └─ Webhooks received and processed
    ├─ Each webhook handler reads this record
    ├─ Extracts change_token if present
    └─ Processes changes...

    [AFTER 12 HOURS]
    └─ Channel renewal Lambda triggered
    ├─ Checks: time_to_expiry = 12 hours (> 6 hours)
    ├─ LOG: "Channel still valid"
    └─ Returns success (no action needed)

    [AFTER 18 HOURS]
    └─ Channel renewal Lambda triggered again
    ├─ Checks: time_to_expiry = 6 hours (RENEW!)
    ├─ Calls files().stop() with old channel_id
    ├─ Calls files().watch() with new channel_id
    ├─ Receives new resource_id
    └─ Updates DynamoDB:
        ├─ channel_id: "gdrive-s3-1ABC...XYZ-uuid456"
        ├─ resource_id: "new-resource-id"
        ├─ expiration: 1674864600 (now + 24 hours)
        ├─ renewed_at: 1674778200
        ├─ status: "renewed"
        └─ Time until expiry: 86,400 seconds (24 hours again)

    [CONTINUES...]
    └─ Cycle repeats every 12 hours
```

**Change Token Management:**

```
Google Drive maintains a "change token" for each folder:
  └─ Token represents a point in time
  ├─ Used to query only changes AFTER that point
  └─ Prevents re-processing of old changes

Stored in DynamoDB (gdrive_channels):
  └─ last_change_token: "12345" (example)

On each webhook:
  1. Webhook handler calls changes.list(pageToken=last_change_token)
  2. Google returns all changes SINCE that token
  3. Handler processes each change
  4. Google provides new startPageToken in response
  5. Store new token in DynamoDB (optional optimization)

Benefits:
  ├─ Resumable: If Lambda crashes, restart from saved token
  ├─ Efficient: Never re-process old changes
  └─ Reliable: Don't lose track of what's been synced
```

### Audit Trail

**Sync Log Table:**

```
Every sync operation creates a DynamoDB entry:

{
  "file_id": "1ABC...XYZ",
  "timestamp": 1674691800,
  "file_name": "sales_data.csv",
  "file_size": 45678,
  "status": "uploaded",
  "s3_key": "sales_data.csv",
  "duration_ms": 2500,
  "md5_hash": "abc123...",
  "error": null
}

Queries:

1. Find all failed syncs in last 24 hours:
   aws dynamodb query \
     --table-name gdrive_s3_sync_log \
     --index-name status-timestamp-index \
     --key-condition-expression "status = :status AND timestamp > :24h_ago" \
     --expression-attribute-values '{
       ":status": {"S": "failed"},
       ":24h_ago": {"N": "1674605400"}
     }'

2. Find all syncs for a specific file:
   aws dynamodb query \
     --table-name gdrive_s3_sync_log \
     --key-condition-expression "file_id = :file_id" \
     --expression-attribute-values '{
       ":file_id": {"S": "1ABC...XYZ"}
     }' \
     --scan-index-forward false  # newest first

3. Calculate sync statistics:
   aws dynamodb scan \
     --table-name gdrive_s3_sync_log \
     --filter-expression "timestamp BETWEEN :start AND :end" \
     --projection-expression "status, duration_ms"
```

---

## Error Handling & Recovery

### Lambda Error Scenarios

**Scenario 1: Invalid Webhook Signature**
```
Request arrives with wrong X-Goog-Channel-Token header

Response:
  ├─ HTTP 401 Unauthorized
  ├─ Body: {"error": "Invalid webhook token"}
  ├─ DO NOT process request
  ├─ Log attempt (security issue?)
  └─ CloudWatch alarm (multiple 401s = attack?)
```

**Scenario 2: Google Drive API Quota Exceeded**
```
changes.list() returns 429 Too Many Requests

Lambda handler:
  ├─ Catch googleapiclient.errors.HttpError
  ├─ Check error.resp.status == 429
  ├─ Return HTTP 202 Accepted (tell Google to retry)
  ├─ Log: "Google API quota exceeded"
  ├─ CloudWatch metric: GoogleAPIErrors++
  └─ SNS alert if this happens 3+ times in 1 hour
```

**Scenario 3: S3 Upload Fails**
```
put_object() fails (permissions, bucket doesn't exist, etc.)

Lambda handler:
  ├─ Catch s3_client.exceptions.ClientError
  ├─ Log detailed error
  ├─ Add to DynamoDB:
  │   {
  │     "file_id": "...",
  │     "status": "failed",
  │     "error": "NoSuchBucket: my-data-bucket"
  │   }
  ├─ Increment SyncFailures metric
  ├─ Return HTTP 500 (indicate failure to Google)
  └─ SNS alert (ops needs to fix permissions)
```

**Scenario 4: Secrets Manager Unreachable**
```
Secrets retrieval fails at startup

Lambda handler:
  ├─ Catch secretsmanager exceptions
  ├─ Retry with exponential backoff (built-in)
  ├─ If still fails: Return HTTP 503 Service Unavailable
  ├─ Log detailed error
  ├─ CloudWatch alarm: SecretsManagerErrors++
  └─ SNS alert (check AWS service health)
```

### Channel Renewal Failures

**Scenario: files().watch() Returns Error**
```
Google Drive rejects new channel creation:
  └─ Quota exceeded
  ├─ Permission denied
  ├─ Folder ID invalid
  └─ Other API error

Recovery:
  1. Log error with details
  2. Publish CloudWatch metric: ChannelRenewalStatus = 0
  3. Update DynamoDB status to "failed"
  4. Send SNS alert with error details
  5. Next renewal check (12 hours) will retry
  6. If fails 3+ times: escalate to PagerDuty
```

### Webhook Handler Timeout

**Scenario: Lambda exceeds 60-second timeout**
```
Possible causes:
  ├─ Large file download (>500MB)
  ├─ Network latency
  ├─ S3 slowness
  └─ Google Drive API slowness

Prevention:
  ├─ Download file in chunks (stream to S3)
  ├─ Use multipart upload for large files
  ├─ Implement timeout (30s max per file)
  ├─ If timeout: abort, skip file, log error

Response:
  ├─ Return HTTP 503 (tell Google to retry)
  ├─ Mark file as "failed" in sync log
  ├─ Increment SyncFailures metric
  └─ SNS alert if timeouts > 5 per hour
```

---

## Performance & Scalability

### Lambda Performance Characteristics

**Webhook Handler Metrics (Typical):**
```
Cold Start (first invocation after deploy):
  ├─ Time: 1.5–2 seconds
  ├─ Components:
  │   ├─ Lambda runtime initialization: 0.5s
  │   ├─ Library imports: 0.3s
  │   ├─ Secrets retrieval: 0.4s
  │   ├─ Google Drive client creation: 0.3s
  │   └─ Total: ~1.5s
  └─ Solution: Pre-provisioned concurrency

Warm Start (subsequent invocations):
  ├─ Time: 200–300 ms
  ├─ Components:
  │   ├─ Function execution: ~200ms
  │   └─ Network I/O: varies
  └─ Note: Variables are reused across invocations

File Processing (per file):
  ├─ Validate signature: ~10ms
  ├─ Check DynamoDB for idempotency: ~50ms
  ├─ Download from Google Drive: ~500–1000ms (depends on size)
  ├─ Upload to S3: ~300–500ms
  ├─ Write to DynamoDB: ~50ms
  └─ Total per file: ~1–2 seconds

Concurrent Invocations:
  ├─ Reserved: 100 concurrent Lambdas
  ├─ Cost/month: ~$0.50–2 (reserved concurrency is cheap)
  ├─ Handles: 100 files/second (if each takes 1s)
  └─ Scalability: Auto-scales beyond 100 if needed
```

### DynamoDB Performance

**Channel Lookups:**
```
Query: Get current channel for folder_id
  ├─ Operation: GetItem (partition key lookup)
  ├─ Time: ~10–20ms
  ├─ Consistency: Strong read (to get fresh expiration)
  ├─ Cost: 1 RCU (read capacity unit)
  └─ Happens: Once per webhook (~100/minute max)
```

**Sync Log Writes:**
```
Write: Log file sync result
  ├─ Operation: PutItem (every file sync)
  ├─ Time: ~10–20ms
  ├─ Cost: 1 WCU (write capacity unit)
  ├─ Happens: Once per file synced (~100–1000/day)
  ├─ TTL: Automatic deletion after 90 days
  └─ Scaling: On-demand billing (auto-scales)
```

**Channel Renewal Updates:**
```
Update: Change channel_id when renewing
  ├─ Operation: UpdateItem (partition key update)
  ├─ Time: ~10–20ms
  ├─ Cost: 1 WCU
  ├─ Happens: Once per 12 hours
  └─ Scaling: Negligible impact
```

### S3 Performance

**Upload Performance:**
```
Single-part upload (< 100 MB):
  ├─ Request size: < 100 MB
  ├─ Time: 300–500ms (depends on file size & network)
  ├─ Cost: 1 PUT request (~$0.000005)
  └─ Recommended for most files

Multipart upload (> 100 MB):
  ├─ Split into 5–100 MB chunks
  ├─ Upload in parallel (5 parts max in Lambda)
  ├─ Time: Lower total time for large files
  ├─ Cost: Multiple PUT requests (1 per part)
  └─ Recommended for files > 100 MB

Concurrent Uploads:
  ├─ Lambda reserved: 100 concurrent
  ├─ S3 partitions: Auto-scales
  ├─ Max RPS (requests per second): 3,500 (AWS soft limit)
  └─ Note: Highly unlikely to hit this with current volume
```

### Cost Analysis

**Monthly Costs (Typical Usage: 100 files/day, 500 KB average):**

```
Lambda:
  ├─ Webhook handler: ~3,000 invocations/month
  │   ├─ Compute: 3,000 * 2.5 seconds = 7,500 GB-seconds
  │   ├─ Cost: 7,500 * $0.0000166667 = $0.125
  │   └─ Requests: 3,000 * $0.0000002 = $0.0006
  ├─ Channel renewal: 60 invocations/month (2x daily)
  │   ├─ Compute: 60 * 0.5 seconds = 30 GB-seconds
  │   └─ Cost: 30 * $0.0000166667 = $0.0005
  └─ Total Lambda: ~$0.13/month

DynamoDB:
  ├─ Channels table: Minimal writes (1-2/day)
  ├─ Sync log table: 100 writes/day = 3,000/month
  ├─ Cost (on-demand): 3,000 writes * $0.00000125 = $0.0038
  ├─ Plus: ~3,000 reads for idempotency checks
  ├─ Cost: 3,000 reads * $0.00000025 = $0.00075
  └─ Total DynamoDB: ~$0.006/month

S3:
  ├─ Storage: 100 files * 500 KB * 30 days = 1.5 GB
  ├─ Cost (storage): 1.5 GB * $0.023/GB = $0.035
  ├─ PUT requests: 3,000 * $0.000005 = $0.015
  ├─ GET requests (if accessed): 3,000 * $0.0000004 = $0.0012
  └─ Total S3: ~$0.052/month

API Gateway:
  ├─ Requests: 3,000/month (free tier: 1M/month)
  ├─ Cost: $0 (within free tier)
  └─ Total API Gateway: $0/month

CloudWatch:
  ├─ Logs ingestion: ~500 KB/day = 15 MB/month
  ├─ Cost: 15 MB * $0.50/GB = $0.0075
  └─ Total CloudWatch: ~$0.01/month

=== TOTAL: ~$0.25/month ===

Additional costs (optional):
  ├─ Pre-provisioned Lambda concurrency: ~$0.02/hour = ~$15/month
  ├─ SNS alerts: ~$0.50/month (depends on frequency)
  └─ Reserved DynamoDB: ~$15/month (if you want predictable cost)
```

---

## Security Considerations

### Authentication & Authorization

**Google Drive Access:**
```
Service Account (not user credentials):
  ├─ Benefits:
  │   ├─ No user-specific permissions
  │   ├─ Token doesn't expire (refreshed server-to-server)
  │   ├─ Can be revoked independently
  │   └─ Audit trail shows "service account", not user
  └─ Security:
      ├─ Private key stored in AWS Secrets Manager
      ├─ Encrypted at rest (using AWS KMS default)
      ├─ Access controlled by IAM role
      └─ Key rotation recommended annually

Webhook Token (X-Goog-Channel-Token):
  ├─ Random 32+ character string
  ├─ Validates that webhook POST came from Google
  ├─ Stored in Secrets Manager (not in code)
  ├─ Checked on every webhook request
  └─ If mismatched: Request rejected (HTTP 401)
```

**AWS IAM Authorization:**
```
Lambda Execution Role:
  ├─ Permissions: Least privilege (only what's needed)
  ├─ S3: PutObject, GetObject (only for my-data-bucket)
  ├─ DynamoDB: PutItem, GetItem, UpdateItem, Scan
  ├─ Secrets Manager: GetSecretValue (only for gdrive-*)
  ├─ CloudWatch: Put logs and metrics
  └─ Explicitly DENIES: DeleteObject, DeleteBucket, TerminateInstance, etc.

API Gateway Authorization:
  ├─ No API key required (uses webhook token instead)
  ├─ Could add AWS API Keys if needed
  ├─ Rate limiting: Optional via API Gateway throttling
  └─ TLS: All traffic encrypted (HTTPS only)
```

### Data Security

**In Transit:**
```
Google Drive → API Gateway:
  ├─ Protocol: HTTPS (TLS 1.2+)
  ├─ Verification: X-Goog-Channel-Token header
  └─ Man-in-the-middle attack risk: Low

API Gateway → Lambda:
  ├─ Internal AWS network (not exposed)
  └─ Security: AWS-managed (automatic)

Lambda → S3:
  ├─ Protocol: HTTPS (AWS SDK handles)
  ├─ Encryption: In-transit (AES-256)
  └─ Verification: AWS signature (V4)

Lambda → DynamoDB:
  ├─ Protocol: HTTPS (AWS SDK handles)
  ├─ Same account/region: Low latency
  └─ Security: VPC endpoint available
```

**At Rest:**
```
S3 Bucket:
  ├─ Encryption: SSE-S3 (AES-256)
  ├─ Key management: AWS-managed (KMS optional)
  ├─ Object metadata encrypted: Yes
  └─ Can upgrade to SSE-KMS for customer-managed keys

DynamoDB Tables:
  ├─ Encryption: On by default (AWS-managed)
  ├─ Encryption in transit: Yes (TLS)
  ├─ At rest: AES-256
  └─ Can upgrade to customer-managed KMS keys

Secrets Manager:
  ├─ Encryption: KMS (AWS-managed or customer)
  ├─ Access logs: CloudTrail (audit trail)
  ├─ Rotation: Can be automated (optional)
  └─ Minimum: Rotate annually
```

### Access Control

**Who can access what:**
```
AWS Root Account:
  ├─ Full access to all resources
  └─ Use only for billing/account management

DevOps Engineer:
  ├─ IAM policy: Full Lambda, DynamoDB, S3
  ├─ IAM policy: Read-only on Secrets Manager
  ├─ IAM policy: Full CloudWatch Logs
  └─ Restricted from: Modifying IAM, deleting resources

Operations:
  ├─ IAM policy: Read-only Lambda, DynamoDB, S3
  ├─ IAM policy: Full CloudWatch (monitoring)
  ├─ IAM policy: SNS publish (for alerts)
  └─ Restricted from: Modifying code or infrastructure

Application:
  ├─ OAuth2 to access synced files
  ├─ Pre-signed URLs for temporary S3 access
  ├─ Time-limited tokens (1–24 hours)
  └─ Minimal scope (read-only by default)
```

### Compliance & Auditing

**Audit Trail:**
```
CloudTrail (AWS API calls):
  ├─ Logs all API calls to AWS services
  ├─ Includes: Who, What, When, Where, Result
  ├─ Cannot be deleted (immutable)
  ├─ Retained for 90 days (free) or 1+ years (with S3)
  └─ Used for: Compliance, incident investigation

CloudWatch Logs (Application logs):
  ├─ Every webhook processed
  ├─ Every file synced (success/failure)
  ├─ Every channel renewal
  ├─ Search logs: grep, filter, aggregate
  └─ Retention: Configurable (default 30 days)

DynamoDB Sync Log:
  ├─ Complete history of all file transfers
  ├─ Includes: File ID, timestamp, status, error
  ├─ Queryable for compliance reports
  ├─ TTL cleanup: After 90 days
  └─ Backup: Can snapshot DynamoDB tables

Metrics (CloudWatch Metrics):
  ├─ Track: Processed, skipped, failed counts
  ├─ Alarms trigger SNS notifications
  ├─ Dashboard: Visual representation
  └─ Queries: API or CLI access
```

---

## Operations & Maintenance

### Monitoring Checklist

**Daily:**
- [ ] Check CloudWatch dashboards
  - [ ] FilesProcessed > 0? (If expected)
  - [ ] SyncFailures == 0? (Or acceptable level)
  - [ ] WebhookLatency < 10s?
- [ ] Review SNS alerts (email)
  - [ ] Any errors?
  - [ ] Any channel renewal failures?
- [ ] Quick DynamoDB check
  - [ ] Recent entries in sync_log?
  - [ ] channels table up-to-date?

**Weekly:**
- [ ] Review CloudWatch logs
  - [ ] Filter for errors: `[ERROR]`
  - [ ] Any repeated patterns?
  - [ ] Google API errors?
  - [ ] S3 errors?
- [ ] Spot-check S3 files
  - [ ] Latest files present?
  - [ ] File counts match expectations?
  - [ ] No duplicates?
- [ ] Lambda performance
  - [ ] Any timeouts?
  - [ ] Cold start frequency acceptable?
  - [ ] Duration trending up? (memory leak?)

**Monthly:**
- [ ] Cost analysis
  - [ ] AWS bill matches estimate?
  - [ ] Usage trending up/down?
  - [ ] Any cost optimization opportunities?
- [ ] Security review
  - [ ] IAM permissions still minimal?
  - [ ] Secrets Manager keys rotated?
  - [ ] No unused resources?
- [ ] Capacity planning
  - [ ] Growth trajectory?
  - [ ] Need to increase reserved concurrency?
  - [ ] S3 storage costs scaling?

### Troubleshooting Procedures

**Webhook Not Triggering**
```
Symptoms:
  ├─ No new files syncing
  ├─ CloudWatch shows no webhook invocations
  └─ But files are being added to Google Drive

Diagnosis:
  1. Check channel status:
     aws dynamodb get-item \
       --table-name gdrive_channels \
       --key '{"folder_id": {"S": "your-folder-id"}}'
  
  2. Check expiration:
     ├─ If expired (< now): Channel dead, need renewal
     ├─ If > 1 week to expiry: Something else wrong
  
  3. Check permissions:
     ├─ Service account still has access?
     └─ Google Drive folder still shared?
  
  4. Check API Gateway:
     ├─ Webhook URL still correct?
     ├─ API Gateway endpoint alive?
     └─ Any 5xx errors in API logs?

Resolution:
  ├─ If expired: Run channel renewal Lambda manually
  ├─ If permission denied: Re-share folder
  ├─ If API down: Check AWS status page
  └─ If timeout: Increase Lambda timeout
```

**High Failure Rate**
```
Symptoms:
  ├─ SyncFailures metric elevated
  ├─ CloudWatch Alarm triggered
  └─ Many files showing "failed" in sync_log

Diagnosis:
  1. Check most recent errors:
     aws dynamodb scan \
       --table-name gdrive_s3_sync_log \
       --filter-expression "status = :status" \
       --expression-attribute-values '{
         ":status": {"S": "failed"}
       }' \
       --limit 20 \
       --scan-index-forward false
  
  2. Look at common error patterns:
     ├─ "NoSuchBucket": S3 bucket deleted?
     ├─ "AccessDenied": IAM permissions changed?
     ├─ "ServiceUnavailable": AWS service down?
     ├─ "Timeout": Network/latency issues?
     └─ "QuotaExceeded": Google Drive quota?

Resolution:
  ├─ Verify S3 bucket exists and accessible
  ├─ Check IAM role has correct policies
  ├─ Check AWS/Google service status pages
  ├─ Increase Lambda timeout if network slow
  └─ Check Google Drive API quota in Cloud Console
```

**Memory or Timeout Issues**
```
Symptoms:
  ├─ Lambda times out (> 60 seconds)
  ├─ Or "Task timed out" errors in logs
  └─ Large files failing, small files succeeding

Diagnosis:
  1. Check Lambda duration metric:
     aws cloudwatch get-metric-statistics \
       --namespace AWS/Lambda \
       --metric-name Duration \
       --dimensions Name=FunctionName,Value=gdrive-webhook-handler \
       --start-time 2026-01-24T00:00:00Z \
       --end-time 2026-01-25T00:00:00Z \
       --period 3600 \
       --statistics Maximum
  
  2. Identify patterns:
     ├─ Only large files fail? (increase memory/timeout)
     ├─ Slow Google API? (nothing we can do)
     ├─ Slow S3? (check S3 Transfer Acceleration)
  
  3. Check CloudWatch logs:
     aws logs tail /aws/lambda/gdrive-webhook-handler --follow

Resolution:
  ├─ Increase Lambda memory: 512 MB → 1024 MB
  │   └─ Also increases CPU (faster execution)
  ├─ Increase timeout: 60 sec → 120 sec
  ├─ Enable multipart upload for large files
  ├─ Enable S3 Transfer Acceleration
  └─ Implement file chunking
```

### Upgrades & Maintenance

**Lambda Code Updates**
```
1. Update code locally
2. Run tests (unit + integration)
3. Create deployment package
4. Deploy to Lambda (blue-green recommended)
   ├─ Create alias "live" (points to current version)
   ├─ Deploy new version
   ├─ Update alias to point to new version
   ├─ Test with canary (1% traffic)
   ├─ Gradually increase traffic to 100%
5. Monitor metrics for 1 hour
6. If issues: Immediately rollback alias to previous version
```

**Dependency Updates**
```
Required monthly:
  └─ pip install --upgrade {library} (security patches)

Optional quarterly:
  ├─ google-api-python-client (new Drive API features)
  ├─ boto3 (new AWS features)
  └─ requests (performance improvements)

Steps:
  1. Test updates locally
  2. Run full integration test
  3. Deploy to staging Lambda
  4. Monitor for 24 hours
  5. Deploy to production
```

**Google Drive API Changes**
```
Keep updated on:
  ├─ Google API documentation
  ├─ Google Cloud release notes
  └─ Deprecation warnings in API responses

If breaking change:
  1. Google provides 12-month notice
  2. Update code with new API version
  3. Test thoroughly
  4. Deploy before deprecation date
```

---

## Testing Strategy

### Unit Tests

```python
# test_webhook_handler.py

def test_webhook_signature_validation():
    """Test that invalid webhook token is rejected"""
    event = {
        'headers': {'X-Goog-Channel-Token': 'INVALID'},
        'body': '{}'
    }
    response = webhook_handler(event, None)
    assert response['statusCode'] == 401

def test_file_filtering():
    """Test that folders and large files are skipped"""
    # Folder (should skip)
    file_meta_folder = {'mimeType': 'application/vnd.google-apps.folder'}
    assert not is_file_supported(file_meta_folder)
    
    # Large file (should skip)
    file_meta_large = {'size': '100000000000', 'name': 'big.zip'}
    assert not is_file_supported(file_meta_large)
    
    # Valid CSV (should process)
    file_meta_csv = {'size': '1000', 'name': 'data.csv', 'mimeType': 'text/csv'}
    assert is_file_supported(file_meta_csv)

def test_idempotency_check():
    """Test that duplicate files aren't uploaded twice"""
    # Mock S3 response (file exists with same MD5)
    s3_client.head_object = Mock(return_value={
        'ETag': '"abc123..."'
    })
    
    # Try to upload same file
    result = upload_to_s3('data.csv', b'content', md5='abc123...')
    assert result == 'skipped'

def test_channel_renewal():
    """Test channel renewal logic"""
    # Channel expiring in 3 hours (< 6 hours threshold)
    channel = {
        'expiration': int(time.time()) + 10800,  # 3 hours
        'channel_id': 'old-id'
    }
    
    # Should trigger renewal
    assert should_renew_channel(channel)
    
    # Channel expiring in 12 hours (> 6 hours threshold)
    channel['expiration'] = int(time.time()) + 43200  # 12 hours
    assert not should_renew_channel(channel)
```

### Integration Tests

```python
# test_integration.py

def test_end_to_end_sync():
    """Test complete sync flow"""
    # 1. Create test file in Google Drive
    test_file = create_test_file('test_data.csv')
    
    # 2. Simulate webhook notification
    webhook_event = {
        'headers': {'X-Goog-Channel-Token': WEBHOOK_TOKEN},
        'body': json.dumps({
            'changes': [{
                'fileId': test_file['id'],
                'file': {
                    'name': 'test_data.csv',
                    'size': '1000',
                    'mimeType': 'text/csv'
                }
            }]
        })
    }
    
    # 3. Call webhook handler
    response = webhook_handler(webhook_event, None)
    assert response['statusCode'] == 200
    
    # 4. Verify file in S3
    s3_object = s3_client.get_object(Bucket='test-bucket', Key='test_data.csv')
    assert s3_object['Body'].read() == test_file['content']
    
    # 5. Verify log entry in DynamoDB
    log_entry = dynamodb.get_item(
        TableName='gdrive_s3_sync_log',
        Key={'file_id': test_file['id']}
    )
    assert log_entry['Item']['status'] == 'uploaded'
    
    # Cleanup
    delete_test_file(test_file['id'])
```

### Performance Tests

```bash
# Load test: 100 concurrent webhook requests
ab -n 100 -c 10 \
  -H "X-Goog-Channel-Token: $WEBHOOK_TOKEN" \
  -p webhook_payload.json \
  https://api.example.com/webhook

# Expected results:
# ├─ All requests succeed (HTTP 200)
# ├─ p50 latency: < 500ms
# ├─ p99 latency: < 2000ms
# └─ 0 errors
```

---

## Troubleshooting Guide

### Quick Reference Table

| Issue | Symptoms | Root Cause | Fix |
|-------|----------|-----------|-----|
| Webhook not triggering | No syncs for 1+ hour | Channel expired | Run renewal Lambda |
| High failure rate | >5% SyncFailures metric | Permissions/quota | Check S3/Google permissions |
| Slow performance | Latency >10 seconds | Large files or network | Increase timeout, enable multipart |
| Memory errors | Lambda OOM kills | Large file in memory | Increase memory or stream to S3 |
| Duplicate files | Same file in S3 twice | Idempotency check failed | Verify MD5 comparison logic |
| Cannot access Secrets | SecretManager errors | IAM policy missing | Add SecretsManager permissions |

---

## Conclusion

This webhook-based pipeline provides a robust, scalable, and cost-effective solution for real-time Google Drive to S3 synchronization. The architecture handles edge cases with custom validation checks, automatically manages webhook channel lifecycle, and provides comprehensive audit logging.

Key strengths:
- Real-time event-driven architecture (<5 second latency)
- Automatic self-healing (channel renewal)
- Complete audit trail (DynamoDB sync log)
- Cost-efficient (~$2–9/month)
- Minimal operational overhead

For questions or issues, refer to the troubleshooting guide or contact the DevOps team.

**Document prepared by:** Data Pipeline Engineering Team  
**Last reviewed:** January 25, 2026  
**Next review date:** April 25, 2026
