# System Architecture
## Enterprise Customer Care Call Processing System

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Diagram](#architecture-diagram)
4. [Component Details](#component-details)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Deployment Architecture](#deployment-architecture)

---

## Executive Summary

This system provides **automated, AI-powered transcription and summarization** of customer care call recordings. Caseworkers upload audio files to Google Drive, triggering a fully automated pipeline that transcribes the call using Amazon Transcribe, generates intelligent summaries using Amazon Bedrock (Claude 3.5 Sonnet), and delivers results to a real-time dashboard within 5 minutes.

### Key Capabilities
- **Zero-touch processing**: Upload → Transcribe → Summarize → Deliver (fully automated)
- **AI-powered analysis**: Claude 3.5 Sonnet extracts key issues, action items, sentiment
- **Real-time dashboard**: WebSocket-based live updates as summaries complete
- **Enterprise scale**: Designed for 100-10,000 calls/day with 99.9% uptime
- **Compliance-ready**: Encryption at rest/in-transit, audit logging, PII redaction

---

## System Overview

### Business Problem
Customer care teams spend hours manually reviewing call recordings to extract key information. This manual process is:
- Time-consuming (15-30 minutes per call)
- Inconsistent (different reviewers extract different details)
- Delayed (summaries arrive hours or days after calls)
- Error-prone (critical details sometimes missed)

### Solution
Automated AI pipeline that:
1. Detects new call recordings in Google Drive (real-time webhook)
2. Transcribes audio with speaker identification (Amazon Transcribe)
3. Generates structured summaries with AI (Amazon Bedrock - Claude 3.5 Sonnet)
4. Delivers results to web dashboard (React frontend with live updates)
5. Completes end-to-end in < 5 minutes per call

### Value Delivered
- **80% time savings**: 5 minutes automated vs 20 minutes manual
- **100% consistency**: AI uses same analysis framework every time
- **Real-time insights**: Summaries available within 5 minutes
- **Scalability**: Handle 1000s of calls/day without additional staff

---

## Architecture Diagram

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GOOGLE CLOUD PLATFORM                           │
│                                                                         │
│  ┌──────────────────┐         ┌─────────────────────────┐             │
│  │  Google Drive    │         │  Push Notification      │             │
│  │  Folder          │────────▶│  Webhook                │             │
│  │  (Audio Files)   │         │  (Real-time triggers)   │             │
│  └──────────────────┘         └───────────┬─────────────┘             │
│                                            │                           │
└────────────────────────────────────────────┼───────────────────────────┘
                                             │ HTTPS POST
                                             │
┌────────────────────────────────────────────▼───────────────────────────┐
│                      AWS CLOUD - DATA INGESTION                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  API Gateway - Webhook Endpoint                                 │  │
│  │  POST /webhook/gdrive                                           │  │
│  └──────────────────────────────┬──────────────────────────────────┘  │
│                                 │                                      │
│                                 ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  Lambda: Webhook Handler                                        │ │
│  │  • Validate webhook signature                                   │ │
│  │  • Download audio from Google Drive                             │ │
│  │  • Upload to S3 (raw-audio/ prefix)                             │ │
│  │  • Create DynamoDB record (status: UPLOADED)                    │ │
│  │  • Trigger Step Functions                                       │ │
│  └──────────────────────────────┬───────────────────────────────────┘ │
│                                 │                                      │
└─────────────────────────────────┼──────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│                    AWS CLOUD - STORAGE LAYER                           │
│                                                                         │
│  ┌──────────────────────┐              ┌──────────────────────────┐   │
│  │  S3 Bucket           │              │  DynamoDB Tables         │   │
│  │  ├─ raw-audio/       │              │  ├─ call-summaries       │   │
│  │  ├─ transcripts/     │              │  ├─ websocket-conns      │   │
│  │  └─ summaries/       │              │  └─ users                │   │
│  │  • Versioning        │              │  • GSIs for querying     │   │
│  │  • Encryption        │              │  • Point-in-time backup  │   │
│  │  • Lifecycle rules   │              │  • DynamoDB Streams      │   │
│  └──────────────────────┘              └──────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│              AWS CLOUD - AI PROCESSING ORCHESTRATION                   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  Step Functions State Machine                                    │ │
│  │                                                                  │ │
│  │  1. UpdateStatusTranscribing → DynamoDB status = TRANSCRIBING   │ │
│  │  2. TranscribeAudio → Amazon Transcribe (wait for completion)   │ │
│  │  3. ProcessTranscript → Lambda (parse & format)                 │ │
│  │  4. UpdateStatusSummarizing → DynamoDB status = SUMMARIZING     │ │
│  │  5. GenerateSummary → Lambda (call Bedrock)                     │ │
│  │  6. SaveToDynamoDB → Lambda (persist results)                   │ │
│  │  7. NotifyFrontend → Lambda (WebSocket notification)            │ │
│  │  8. MarkAsFailed → Error handler (if any step fails)            │ │
│  │                                                                  │ │
│  │  • Retry with exponential backoff                               │ │
│  │  • Dead-letter queue for failures                               │ │
│  │  • CloudWatch metrics at each stage                             │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│         ▼                              ▼                                │
│  ┌──────────────────┐         ┌────────────────────────────┐          │
│  │  Amazon          │         │  Amazon Bedrock            │          │
│  │  Transcribe      │         │  Claude 3.5 Sonnet         │          │
│  │                  │         │                            │          │
│  │  • Speaker ID    │         │  • Structured summaries    │          │
│  │  • Timestamps    │         │  • Sentiment analysis      │          │
│  │  • Auto-detect   │         │  • Action item extraction  │          │
│  │  • PII redaction │         │  • JSON output format      │          │
│  └──────────────────┘         └────────────────────────────┘          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│                    AWS CLOUD - API & AUTHENTICATION                    │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  API Gateway - REST API                                          │ │
│  │  GET  /summaries (list with pagination)                          │ │
│  │  GET  /summaries/{call_id} (detail view)                         │ │
│  │  GET  /summaries/{call_id}/audio (presigned URL)                 │ │
│  │  GET  /summaries/{call_id}/transcript (full transcript)          │ │
│  │  POST /auth/login (authentication)                               │ │
│  │  GET  /auth/user (current user profile)                          │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  Amazon Cognito User Pool                                        │ │
│  │  • User groups: caseworkers, supervisors, admins                │ │
│  │  • JWT token authentication                                      │ │
│  │  • Password policies & MFA                                       │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│                AWS CLOUD - REAL-TIME NOTIFICATIONS                     │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  API Gateway - WebSocket API                                     │ │
│  │  wss://ws.yourdomain.com                                         │ │
│  │                                                                  │ │
│  │  $connect → Validate JWT, store connectionId in DynamoDB        │ │
│  │  $disconnect → Remove connectionId from DynamoDB                │ │
│  │  $default → Message router (future bidirectional messaging)     │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  Lambda: WebSocket Notifier                                      │ │
│  │  • Query active connections from DynamoDB                        │ │
│  │  • Send message to all connected clients                         │ │
│  │  • Message: {"type": "NEW_SUMMARY", "data": {summary}}          │ │
│  │  • Handle stale connections (cleanup on error)                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│                         FRONTEND APPLICATION                           │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  React 18 + TypeScript Dashboard                                │ │
│  │                                                                  │ │
│  │  ┌─────────────────┐  ┌──────────────────────────────────────┐ │ │
│  │  │  Authentication │  │  Summary List View                   │ │ │
│  │  │  • Login        │  │  • Pagination (20 per page)          │ │ │
│  │  │  • Session mgmt │  │  • Filters: Status, date, keywords   │ │ │
│  │  └─────────────────┘  │  • Sort by date/sentiment/duration   │ │ │
│  │                       │  • Color-coded status badges         │ │ │
│  │  ┌─────────────────┐  │  • Real-time updates (WebSocket)     │ │ │
│  │  │  Summary Detail │  └──────────────────────────────────────┘ │ │
│  │  │  • Audio player │                                           │ │
│  │  │  • Issue summary│  ┌──────────────────────────────────────┐ │ │
│  │  │  • Key details  │  │  Real-Time Updates                   │ │ │
│  │  │  • Action items │  │  • WebSocket connection              │ │ │
│  │  │  • Transcript   │  │  • Toast notifications               │ │ │
│  │  │  • Export PDF   │  │  • Auto-reconnection                 │ │ │
│  │  └─────────────────┘  │  • Connection status indicator       │ │ │
│  │                       └──────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  Hosted on: AWS Amplify or S3 + CloudFront                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Data Ingestion Layer

#### Google Drive Integration
- **Service**: Google Drive API v3 with Push Notifications
- **Webhook URL**: API Gateway endpoint receives real-time notifications
- **Trigger**: Any file added to designated folder
- **Frequency**: Real-time (< 10 seconds latency)
- **Security**: Service account with viewer-only permissions, token validation

#### Webhook Handler Lambda
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 5 minutes
- **Responsibilities**:
  - Validate Google webhook signature
  - Download audio file from Google Drive
  - Upload to S3 with organized folder structure
  - Create initial DynamoDB record
  - Trigger Step Functions state machine
  - Handle errors with retry logic

### 2. Storage Layer

#### S3 Bucket Architecture
```
customer-care-audio-{environment}/
├── raw-audio/YYYY-MM-DD/{call-id}.{ext}
├── transcripts/YYYY-MM-DD/{call-id}-transcript.json
└── summaries/YYYY-MM-DD/{call-id}-summary.json
```

**Features**:
- **Versioning**: Enabled for data protection
- **Encryption**: AES-256 (S3-managed) or KMS
- **Lifecycle**: Archive to Glacier after 90 days
- **CORS**: Configured for presigned URL access
- **Event Notifications**: Enabled for raw-audio/ prefix

#### DynamoDB Tables

**Table 1: call-summaries**
- **Purpose**: Store all call metadata and summaries
- **Primary Key**: 
  - Partition: `call_id` (string)
  - Sort: `timestamp` (string, ISO 8601)
- **GSIs**:
  - `status-timestamp-index`: Query by processing status
  - `user-timestamp-index`: Query by assigned caseworker
  - `date-index`: Query by call date for reporting
- **Attributes**:
  ```json
  {
    "call_id": "20260131143045-a1b2c3d4",
    "timestamp": "2026-01-31T14:30:45.123Z",
    "status": "COMPLETED | TRANSCRIBING | SUMMARIZING | FAILED",
    "file_name": "customer_call.mp3",
    "call_date": "2026-01-31",
    "issue_sentence": "Customer wants refund for damaged product",
    "key_details": ["Item arrived damaged", "Customer paid $99.99", "Wants full refund"],
    "action_items": ["Process refund", "Send return label"],
    "next_steps": ["Email refund confirmation", "Follow up in 3 days"],
    "sentiment": "Negative | Neutral | Positive",
    "duration_seconds": 287,
    "agent_id": "AGENT-12345",
    "customer_id": "CUST-67890",
    "assigned_user": "caseworker@company.com",
    "s3_audio_url": "s3://bucket/raw-audio/...",
    "s3_transcript_url": "s3://bucket/transcripts/...",
    "s3_summary_url": "s3://bucket/summaries/...",
    "gdrive_file_id": "1a2b3c4d5e6f7g8h9i",
    "processed_timestamp": "2026-01-31T14:35:21.456Z",
    "error_message": null,
    "retry_count": 0
  }
  ```

**Table 2: websocket-connections**
- **Purpose**: Track active WebSocket connections
- **Primary Key**: `connectionId` (string)
- **TTL**: Auto-delete after 24 hours
- **Attributes**: `connectionId`, `user_id`, `email`, `connected_at`, `ttl`

**Table 3: users**
- **Purpose**: User profiles (supplement to Cognito)
- **Primary Key**: `email` (string)
- **Attributes**: `email`, `user_id`, `full_name`, `role`, `department`, `created_at`, `last_login`

### 3. AI Processing Pipeline

#### Step Functions State Machine
**Name**: `call-processing-workflow`  
**Execution Pattern**: Standard (long-running, up to 1 year)

**States**:
1. **UpdateStatusTranscribing** (Task)
   - Update DynamoDB status to "TRANSCRIBING"
   
2. **TranscribeAudio** (Task)
   - Native Transcribe integration with `.sync` suffix (waits for completion)
   - Language auto-detect
   - Speaker identification (2 speakers)
   - PII redaction (optional)
   
3. **ProcessTranscript** (Task)
   - Lambda parses Transcribe output
   - Formats conversation with speaker labels
   - Extracts metadata (duration, word count)
   - Saves formatted transcript to S3
   
4. **UpdateStatusSummarizing** (Task)
   - Update DynamoDB status to "SUMMARIZING"
   
5. **GenerateSummary** (Task)
   - Lambda calls Bedrock with prompt
   - Model: Claude 3.5 Sonnet
   - Returns structured JSON summary
   
6. **SaveToDynamoDB** (Task)
   - Lambda persists complete summary
   - Updates all fields in DynamoDB
   - Status becomes "COMPLETED"
   
7. **NotifyFrontend** (Task)
   - Lambda sends WebSocket message to connected clients
   - Message includes complete summary data
   
8. **MarkAsFailed** (Task - Catch Handler)
   - Updates status to "FAILED"
   - Logs error message
   - Sends to dead-letter queue

**Error Handling**:
- Retry 3 times with exponential backoff (2^attempt seconds)
- All errors caught and routed to failure handler
- CloudWatch alarms on high failure rates

#### Amazon Transcribe Configuration
- **Service**: Amazon Transcribe
- **Job Type**: Batch transcription with .sync integration
- **Language**: Auto-detect (or specify en-US)
- **Media Formats**: mp3, wav, m4a, flac, ogg (auto-detected)
- **Features**:
  - Speaker identification: 2 speakers (agent, customer)
  - Word-level timestamps
  - Confidence scores
  - PII redaction: Credit card, SSN, addresses (optional)
- **Output**: JSON with full transcript and metadata
- **Performance**: ~3 minutes for 5-minute call

#### Amazon Bedrock Integration
- **Model**: Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20241022-v2:0`)
- **Alternative**: Claude 3 Haiku (faster, cheaper, 80% accuracy)
- **Inference Parameters**:
  - `max_tokens`: 2000
  - `temperature`: 0.3 (factual, consistent)
  - `top_p`: 0.9

**Prompt Strategy**:
```python
system_prompt = """You are an expert customer service analyst. 
Analyze the following customer care call transcript and extract key information.
Return ONLY valid JSON with no additional text."""

user_prompt = f"""
Analyze this call transcript:

{formatted_transcript}

Return JSON with these exact fields:
{{
  "call_date": "YYYY-MM-DD",
  "issue_sentence": "Single sentence describing main issue",
  "key_details": ["Detail 1", "Detail 2", "Detail 3"],
  "action_items": ["Action 1", "Action 2"],
  "next_steps": ["Step 1", "Step 2"],
  "sentiment": "Positive|Neutral|Negative",
  "agent_id": "extracted from transcript or null",
  "customer_id": "extracted from transcript or null"
}}
"""
```

**Error Handling**:
- Retry on throttling (exponential backoff)
- Fallback to simpler prompt if JSON parsing fails
- Log all requests/responses for debugging
- Monitor token usage for cost tracking

### 4. Backend API Layer

#### REST API Endpoints

**Authentication**: Cognito JWT tokens (except /webhook/gdrive)

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/webhook/gdrive` | Receive Google webhooks | Custom token |
| GET | `/summaries` | List summaries (paginated) | Cognito JWT |
| GET | `/summaries/{call_id}` | Get single summary detail | Cognito JWT |
| GET | `/summaries/{call_id}/audio` | Get presigned audio URL | Cognito JWT |
| GET | `/summaries/{call_id}/transcript` | Get full transcript | Cognito JWT |
| POST | `/auth/login` | User authentication | None (public) |
| GET | `/auth/user` | Get user profile | Cognito JWT |

**API Features**:
- **CORS**: Enabled for frontend domain
- **Rate Limiting**: 100 requests/minute per user (API Gateway)
- **Throttling**: Burst 500, steady-state 100/sec
- **Validation**: Request/response validation at API Gateway
- **Logging**: Structured JSON logs to CloudWatch
- **Metrics**: Custom metrics for each endpoint

#### Lambda Functions

**Common Configuration**:
- Runtime: Python 3.11 or Node.js 18
- Memory: 256 MB (increase if needed)
- Timeout: 30 seconds
- Environment: `TABLE_NAME`, `BUCKET_NAME`, `COGNITO_USER_POOL_ID`
- IAM: Least-privilege roles
- Logging: Structured JSON

**Key Functions**:
1. `api-summaries-list`: Query DynamoDB with filters, pagination
2. `api-summary-detail`: Get single item from DynamoDB
3. `api-get-audio-url`: Generate presigned URL (1-hour expiration)
4. `api-get-transcript`: Retrieve transcript from S3
5. `auth-login`: Proxy to Cognito authentication
6. `auth-user-profile`: Get user info from Cognito/DynamoDB

### 5. Authentication & Authorization

#### Amazon Cognito User Pool
- **Username Attribute**: Email address
- **Password Policy**: Min 8 chars, uppercase, lowercase, number
- **MFA**: Optional (TOTP or SMS)
- **Token Expiration**: Access 1 hour, Refresh 30 days
- **Email Verification**: Required

**User Groups**:
- **caseworkers**: View summaries, play audio, export
- **supervisors**: View all summaries, analytics dashboard
- **admins**: Full access, user management, system configuration

**Authorization Flow**:
1. User logs in → Cognito returns JWT tokens
2. Frontend stores tokens securely
3. All API calls include JWT in `Authorization` header
4. API Gateway validates JWT signature
5. Lambda checks user role/permissions
6. Response returned or 403 if unauthorized

### 6. Real-Time Notification System

#### WebSocket API
- **URL**: `wss://ws.yourdomain.com`
- **Protocol**: WebSocket (AWS API Gateway v2)
- **Authentication**: JWT token in query string

**Routes**:
- `$connect`: Validate JWT, store connectionId in DynamoDB
- `$disconnect`: Remove connectionId from DynamoDB
- `$default`: Message router (for future features)

**Connection Flow**:
```javascript
// Frontend initiates connection
const ws = new WebSocket(`wss://ws.yourdomain.com?token=${jwtToken}`);

// Backend validates token
// If valid, store { connectionId, user_id, email, connected_at } in DynamoDB

// On new summary completion
// Lambda queries active connections and sends:
{
  "type": "NEW_SUMMARY",
  "data": {
    "call_id": "...",
    "issue_sentence": "...",
    "sentiment": "...",
    "timestamp": "..."
  }
}

// Frontend receives message and updates UI without refresh
```

**Features**:
- Heartbeat/ping every 30 seconds (keep connection alive)
- Automatic reconnection on disconnect (exponential backoff)
- Connection status indicator in UI
- Stale connection cleanup (TTL in DynamoDB)

### 7. Frontend Application

#### Technology Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **State Management**: React Query (server) + Context API (UI)
- **UI Library**: Material-UI (MUI) or Tailwind CSS + Headless UI
- **Authentication**: AWS Amplify Auth
- **HTTP Client**: Axios with interceptors
- **WebSocket**: Native API with reconnection logic
- **Routing**: React Router v6
- **Form Handling**: React Hook Form
- **Date Handling**: date-fns
- **Audio Player**: react-h5-audio-player

#### Key Features

**1. Authentication Pages**
- Login with email/password
- Forgot password flow
- Session management (auto-logout on expiration)
- Protected routes

**2. Dashboard - Summary List**
- Paginated grid/table (20 per page)
- Filters: Status, date range, keyword search
- Sort: Date, sentiment, duration
- Status badges (color-coded)
- Real-time updates via WebSocket
- Quick actions: View, play audio, download

**3. Summary Detail View**
- Header: Date, duration, sentiment, call ID
- Audio player with controls
- Issue summary (prominent display)
- Key details (bullet list)
- Action items (numbered list)
- Next steps (numbered list)
- Full transcript (expandable)
- Metadata display
- Export as PDF

**4. Real-Time Updates**
- WebSocket connection on login
- Toast notifications for new summaries
- Auto-refresh list
- Connection status indicator
- Automatic reconnection

**Folder Structure**:
```
src/
├── components/
│   ├── Auth/ (Login, ProtectedRoute)
│   ├── Dashboard/ (SummaryList, SummaryCard, SummaryDetail)
│   ├── Layout/ (Header, Sidebar, Footer)
│   └── Common/ (AudioPlayer, StatusBadge, LoadingSpinner, ErrorBoundary)
├── services/ (API clients, auth utilities)
├── hooks/ (Custom React hooks, useWebSocket)
├── contexts/ (React Context providers)
├── types/ (TypeScript interfaces)
├── utils/ (Helper functions)
├── routes/ (Route definitions)
├── App.tsx
└── main.tsx
```

### 8. Monitoring & Observability

#### CloudWatch Dashboards

**Dashboard 1: Processing Pipeline**
- Calls uploaded per hour (metric: custom)
- Processing time P50/P95/P99 (Step Functions)
- Success/failure rates (custom metrics)
- Time-series by stage (Transcribe, Bedrock, total)
- Error distribution by type

**Dashboard 2: API Performance**
- API latency by endpoint (API Gateway)
- Request count per endpoint
- Error rates (4xx, 5xx)
- Throttling events

**Dashboard 3: Cost Tracking**
- Transcribe minutes used
- Bedrock token consumption
- Lambda invocations
- S3 storage size
- Monthly cost projections

#### CloudWatch Alarms

**Critical (immediate notification)**:
- Step Function failure rate > 10%
- API Gateway 5xx errors > 5/min
- Lambda errors > 10/min
- DynamoDB throttling events

**Warning (business hours)**:
- Average processing time > 10 minutes
- S3 storage > 80% budget
- Bedrock throttling events

**Notification**:
- SNS topic → Email + Slack
- PagerDuty integration (optional)
- Escalation policy

#### Logging Strategy
- **Format**: JSON with standard fields (`timestamp`, `level`, `call_id`, `user_id`, `action`, `duration`, `error`)
- **Retention**: 30 days (application), 1 year (audit)
- **Insights**: Pre-built queries for common investigations
- **X-Ray**: Distributed tracing across services

---

## Data Flow

### End-to-End Processing Flow

**Phase 1: Upload (0-30 seconds)**
1. Caseworker uploads audio file to Google Drive folder
2. Google Drive sends webhook notification to API Gateway (< 10 sec)
3. Webhook Handler Lambda validates request
4. Lambda downloads file from Google Drive via API
5. Lambda uploads file to S3 (`raw-audio/YYYY-MM-DD/{call-id}.ext`)
6. Lambda creates DynamoDB record with status "UPLOADED"
7. Lambda triggers Step Functions state machine
8. Lambda responds 200 OK to Google (complete webhook)

**Phase 2: Transcription (1-4 minutes)**
9. Step Functions updates DynamoDB status to "TRANSCRIBING"
10. Step Functions calls Amazon Transcribe (native integration with `.sync`)
11. Transcribe processes audio file from S3
12. Transcribe generates transcript with speaker labels and timestamps
13. Transcribe saves output to S3
14. Process Transcript Lambda retrieves output
15. Lambda formats transcript into readable conversation
16. Lambda saves formatted transcript to S3 (`transcripts/...`)
17. Lambda returns formatted data to Step Functions

**Phase 3: Summarization (30-60 seconds)**
18. Step Functions updates DynamoDB status to "SUMMARIZING"
19. Generate Summary Lambda receives formatted transcript
20. Lambda constructs prompt for Bedrock
21. Lambda calls Bedrock with Claude 3.5 Sonnet
22. Bedrock analyzes transcript and generates structured JSON summary
23. Lambda validates JSON output
24. Lambda returns summary to Step Functions

**Phase 4: Persistence (5-10 seconds)**
25. Save Summary Lambda receives all data
26. Lambda updates DynamoDB record with complete summary
27. Lambda saves summary JSON to S3 (`summaries/...`)
28. Lambda updates status to "COMPLETED"
29. Lambda records processing timestamp
30. Lambda emits CloudWatch success metrics

**Phase 5: Notification (< 5 seconds)**
31. Notify Frontend Lambda receives summary data
32. Lambda queries DynamoDB for active WebSocket connections
33. Lambda sends message to each connection via API Gateway Management API
34. Frontend receives WebSocket message
35. Frontend displays toast notification
36. Frontend updates summary list without page refresh
37. Step Functions execution completes successfully

**Total Time**: 2-5 minutes (target: < 5 minutes for 5-minute call)

### Status Transitions

```
UPLOADED → TRANSCRIBING → SUMMARIZING → COMPLETED
                                      ↘ FAILED
```

### Error Scenarios

**Scenario 1: Transcribe Failure**
- Transcribe job fails (unsupported format, corrupted file)
- Step Functions catches error
- Retry 3 times with exponential backoff
- If still fails, route to MarkAsFailed state
- DynamoDB updated with status "FAILED" and error message
- Optionally send notification to admin

**Scenario 2: Bedrock Throttling**
- Bedrock returns throttling error
- Lambda retries 3 times with exponential backoff
- If successful, continue processing
- If fails, Step Functions catches error and routes to MarkAsFailed

**Scenario 3: WebSocket Stale Connection**
- Notification Lambda tries to send to connectionId
- API Gateway returns 410 Gone (stale connection)
- Lambda removes connectionId from DynamoDB
- Lambda continues to next connection
- No error logged (expected behavior)

---

## Technology Stack

### Google Cloud Platform
- **Google Drive API**: File storage and webhook notifications
- **Service Account**: Programmatic access to Drive

### AWS Services
| Service | Purpose | Key Features |
|---------|---------|-------------|
| **API Gateway** | REST & WebSocket APIs | JWT auth, rate limiting, CORS |
| **Lambda** | Serverless compute | Python 3.11, event-driven |
| **Step Functions** | Workflow orchestration | Visual workflows, retries, error handling |
| **Transcribe** | Speech-to-text | Speaker ID, timestamps, PII redaction |
| **Bedrock** | AI/ML models | Claude 3.5 Sonnet, structured output |
| **S3** | Object storage | Versioning, encryption, lifecycle policies |
| **DynamoDB** | NoSQL database | GSIs, streams, point-in-time recovery |
| **Cognito** | Authentication | JWT tokens, user pools, MFA |
| **CloudWatch** | Monitoring | Dashboards, alarms, logs, metrics |
| **Secrets Manager** | Credentials storage | Google service account key |
| **SNS** | Notifications | Email, Slack, PagerDuty integration |
| **CloudFront** | CDN | Frontend distribution (optional) |
| **Amplify** | Frontend hosting | CI/CD, SSL, custom domain |

### Frontend Technologies
- React 18, TypeScript, Vite
- Material-UI or Tailwind CSS
- React Query, React Router
- AWS Amplify Auth
- Axios, WebSocket API

### Development Tools
- **IaC**: AWS CDK (TypeScript)
- **Version Control**: Git, GitHub
- **CI/CD**: GitHub Actions
- **Testing**: Jest (unit), Playwright (E2E), Locust (load)
- **Code Quality**: ESLint, Prettier, Black

---

## Deployment Architecture

### Environments
1. **Development**: Lower limits, verbose logging, frequent deploys
2. **Staging**: Production-like, used for testing and validation
3. **Production**: High availability, optimized costs, minimal logging

### Multi-Stack CDK Architecture
```
lib/
├── stacks/
│   ├── storage-stack.ts (S3, DynamoDB)
│   ├── auth-stack.ts (Cognito)
│   ├── processing-stack.ts (Step Functions, Transcribe, Bedrock)
│   ├── api-stack.ts (API Gateway, Lambda functions)
│   ├── websocket-stack.ts (WebSocket API, connections)
│   ├── monitoring-stack.ts (CloudWatch dashboards, alarms)
│   └── frontend-stack.ts (Amplify or S3 + CloudFront)
├── constructs/ (Reusable CDK constructs)
├── config/ (Environment-specific config)
└── main.ts (Stack orchestration)
```

### Deployment Strategy
- **Blue-Green**: Lambda functions (zero downtime)
- **Canary**: Route 10% traffic to new version, monitor, then 100%
- **Rollback**: Automated on alarm threshold breach

### CI/CD Pipeline (GitHub Actions)
```
Trigger: Push to develop/main branch

Stages:
1. Lint & Test → ESLint, TypeScript, unit tests
2. Build → Compile CDK, build React frontend
3. Security Scan → Snyk, AWS Security Hub
4. Deploy to Dev → Auto-deploy (develop branch)
5. Integration Tests → E2E tests against dev
6. Deploy to Staging → Manual approval
7. Smoke Tests → Validate critical paths
8. Deploy to Production → Manual approval + change request
9. Post-Deployment Validation → Health checks, metrics
```

---

## Key Success Metrics

### Technical KPIs
- **Processing Time**: P95 < 5 minutes (upload to summary)
- **Accuracy**: Transcription > 90%, Summary relevance > 4/5
- **Availability**: 99.9% uptime (43 min downtime/month max)
- **Error Rate**: < 1% of calls fail processing
- **API Latency**: P95 < 500ms
- **Cost Efficiency**: < $1.00 per call

### Business KPIs
- **User Adoption**: 90% of caseworkers using within 30 days
- **Time Savings**: 80% reduction in manual review time
- **User Satisfaction**: > 4/5 rating
- **Processing Volume**: 200+ calls/day in first month

### Budget (200 calls/day)
| Service | Monthly Cost |
|---------|--------------|
| Transcribe | $24 |
| Bedrock (Claude 3.5) | $60 |
| S3 | $2 |
| DynamoDB | $3 |
| Lambda | $5 |
| API Gateway | $2 |
| CloudWatch | $10 |
| Step Functions | $1 |
| Amplify | $12 |
| **Total** | **~$124/month** |

Scaling: 500 calls/day = $280/mo | 1000 calls/day = $520/mo

---

## Security & Compliance

### Encryption
- **At Rest**: S3 (AES-256/KMS), DynamoDB (KMS), Secrets Manager (KMS)
- **In Transit**: TLS 1.2+ for all API calls, WSS for WebSocket

### IAM Strategy
- Least privilege for all roles
- Service roles for Lambda, Step Functions
- Resource-based policies for S3, DynamoDB
- Permission boundaries to prevent escalation

### Network Security
- AWS WAF for DDoS protection
- API Gateway rate limiting
- VPC configuration (optional for enhanced isolation)

### Audit & Compliance
- CloudTrail for all API calls
- AWS Config for configuration tracking
- S3 access logging
- DynamoDB Streams for audit trail

### PII Handling
- Transcribe PII redaction (optional)
- Data retention policies (GDPR compliant)
- Right to deletion mechanism

---

## Next Steps

1. **Deploy**: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Complete deployment walkthrough
2. **Quick Start**: [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Quick implementation checklist
3. **Read**: [02_build_process_steps.md](02_build_process_steps.md) - Detailed build process
4. **Review**: [01_features_and_stories.md](01_features_and_stories.md) - User stories and requirements
5. **Follow**: [03_stage_completion_checklist.md](03_stage_completion_checklist.md) - Validation checklists
6. **Navigate**: [04_navigation_guide.md](04_navigation_guide.md) - Documentation roadmap

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Step-by-step deployment instructions |
| [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) | Quick-start implementation checklist |
| [case_study_file.md](case_study_file.md) | Original project requirements |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [README.md](README.md) | Project overview |

---

**Document Version**: 2.0  
**Last Updated**: 2025-01-31  
**Author**: System Architect  
**Repository**: [github.com/olajio/customer-care-call-processor](https://github.com/olajio/customer-care-call-processor)
