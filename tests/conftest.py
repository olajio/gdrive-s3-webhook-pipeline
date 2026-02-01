"""
Shared pytest fixtures for all test modules.
"""
import json
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

# Set up test environment variables
os.environ['DYNAMODB_TABLE'] = 'test-call-summaries'
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['WEBSOCKET_CONNECTIONS_TABLE'] = 'test-websocket-connections'
os.environ['WEBHOOK_CHANNELS_TABLE'] = 'test-webhook-channels'
os.environ['STEP_FUNCTIONS_ARN'] = 'arn:aws:states:us-east-1:123456789012:stateMachine:test'
os.environ['PRESIGNED_URL_EXPIRATION'] = '3600'
os.environ['BEDROCK_MODEL_ID'] = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
os.environ['MAX_TOKENS'] = '4096'
os.environ['DEFAULT_PAGE_SIZE'] = '20'
os.environ['MAX_PAGE_SIZE'] = '100'
os.environ['AWS_REGION'] = 'us-east-1'


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table resource."""
    table = MagicMock()
    table.put_item = MagicMock(return_value={})
    table.get_item = MagicMock(return_value={'Item': {}})
    table.update_item = MagicMock(return_value={})
    table.delete_item = MagicMock(return_value={})
    table.query = MagicMock(return_value={'Items': [], 'Count': 0})
    table.scan = MagicMock(return_value={'Items': [], 'Count': 0})
    return table


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    client = MagicMock()
    client.put_object = MagicMock(return_value={})
    client.get_object = MagicMock(return_value={
        'Body': MagicMock(read=MagicMock(return_value=b'test content'))
    })
    client.generate_presigned_url = MagicMock(return_value='https://example.com/presigned')
    client.head_object = MagicMock(return_value={
        'ContentLength': 1024,
        'ContentType': 'audio/mpeg'
    })
    return client


@pytest.fixture
def mock_step_functions_client():
    """Mock Step Functions client."""
    client = MagicMock()
    client.start_execution = MagicMock(return_value={
        'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:test:test-exec',
        'startDate': datetime.utcnow()
    })
    client.describe_execution = MagicMock(return_value={
        'status': 'RUNNING'
    })
    return client


@pytest.fixture
def mock_transcribe_client():
    """Mock Amazon Transcribe client."""
    client = MagicMock()
    client.start_transcription_job = MagicMock(return_value={
        'TranscriptionJob': {
            'TranscriptionJobName': 'test-job',
            'TranscriptionJobStatus': 'IN_PROGRESS'
        }
    })
    client.get_transcription_job = MagicMock(return_value={
        'TranscriptionJob': {
            'TranscriptionJobName': 'test-job',
            'TranscriptionJobStatus': 'COMPLETED',
            'Transcript': {
                'TranscriptFileUri': 'https://s3.amazonaws.com/bucket/transcript.json'
            }
        }
    })
    return client


@pytest.fixture
def mock_bedrock_client():
    """Mock Amazon Bedrock runtime client."""
    client = MagicMock()
    client.invoke_model = MagicMock(return_value={
        'body': MagicMock(read=MagicMock(return_value=json.dumps({
            'content': [{
                'text': json.dumps({
                    'summary': 'Test summary',
                    'key_points': ['Point 1', 'Point 2'],
                    'action_items': ['Action 1'],
                    'sentiment': 'positive',
                    'urgency': 'low',
                    'categories': ['general']
                })
            }]
        }).encode()))
    })
    return client


@pytest.fixture
def mock_api_gateway_client():
    """Mock API Gateway Management client for WebSocket."""
    client = MagicMock()
    client.post_to_connection = MagicMock(return_value={})
    client.delete_connection = MagicMock(return_value={})
    return client


@pytest.fixture
def sample_call_record():
    """Sample call record for testing."""
    return {
        'call_id': 'call-abc12345',
        'status': 'PENDING',
        'caller_id': '+14155551234',
        'assigned_user_id': 'user-001',
        's3_bucket': 'test-bucket',
        's3_key': 'raw-audio/2024/01/15/call-abc12345.mp3',
        'created_at': '2024-01-15T10:30:00Z',
        'gdrive_file_id': 'gdrive-file-123',
        'original_filename': 'call_recording.mp3'
    }


@pytest.fixture
def sample_completed_call():
    """Sample completed call with summary."""
    return {
        'call_id': 'call-abc12345',
        'status': 'COMPLETED',
        'caller_id': '+14155551234',
        'assigned_user_id': 'user-001',
        's3_bucket': 'test-bucket',
        's3_key': 'raw-audio/2024/01/15/call-abc12345.mp3',
        'transcript_s3_key': 'transcripts/2024/01/15/call-abc12345.txt',
        'summary': 'Customer called about billing issue. Refund processed.',
        'key_points': ['Duplicate charge', 'Refund requested', 'Customer satisfied'],
        'action_items': ['Verify refund in 3-5 days'],
        'sentiment': 'positive',
        'urgency': 'medium',
        'categories': ['billing', 'refund'],
        'created_at': '2024-01-15T10:30:00Z',
        'completed_at': '2024-01-15T10:35:00Z'
    }


@pytest.fixture
def sample_transcript():
    """Sample formatted transcript."""
    return """
Agent: Good morning, thank you for calling Customer Care. How can I help you today?

Customer: Hi, I'm having trouble with my account. I was charged twice for my subscription last month.

Agent: I'm sorry to hear that. Let me look into this for you. Can you please provide your account number?

Customer: Sure, it's 12345678.

Agent: Thank you. I can see the duplicate charge. I'll process a refund for you right away. Is there anything else I can help with?

Customer: No, that's all. Thank you so much!

Agent: You're welcome. Have a great day!
"""


@pytest.fixture
def sample_webhook_event():
    """Sample Google Drive webhook event."""
    return {
        'headers': {
            'X-Goog-Channel-ID': 'channel-123',
            'X-Goog-Resource-ID': 'resource-456',
            'X-Goog-Resource-State': 'change',
            'X-Goog-Channel-Token': 'valid-token'
        },
        'body': '{}'
    }


@pytest.fixture
def sample_api_event():
    """Sample API Gateway event with Cognito auth."""
    return {
        'httpMethod': 'GET',
        'path': '/summaries',
        'pathParameters': None,
        'queryStringParameters': {
            'status': 'COMPLETED',
            'limit': '20'
        },
        'headers': {
            'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
        },
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'user-001',
                    'cognito:username': 'testuser@example.com',
                    'cognito:groups': 'caseworkers',
                    'email': 'testuser@example.com'
                }
            }
        }
    }


@pytest.fixture
def sample_websocket_connect_event():
    """Sample WebSocket $connect event."""
    return {
        'requestContext': {
            'connectionId': 'conn-abc123',
            'routeKey': '$connect',
            'eventType': 'CONNECT',
            'domainName': 'abc123.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod',
            'authorizer': {
                'claims': {
                    'sub': 'user-001',
                    'cognito:username': 'testuser@example.com'
                }
            }
        }
    }


@pytest.fixture
def sample_step_functions_input():
    """Sample Step Functions state machine input."""
    return {
        'call_id': 'call-abc12345',
        's3_bucket': 'test-bucket',
        's3_key': 'raw-audio/2024/01/15/call-abc12345.mp3',
        'caller_id': '+14155551234',
        'assigned_user_id': 'user-001'
    }


@pytest.fixture
def sample_transcribe_output():
    """Sample Amazon Transcribe job output."""
    return {
        "jobName": "call-abc12345-xyz",
        "accountId": "123456789012",
        "results": {
            "transcripts": [
                {
                    "transcript": "Hello, this is customer service. How can I help you today?"
                }
            ],
            "speaker_labels": {
                "speakers": 2,
                "segments": [
                    {
                        "start_time": "0.0",
                        "end_time": "3.5",
                        "speaker_label": "spk_0",
                        "items": []
                    }
                ]
            },
            "items": [
                {
                    "start_time": "0.0",
                    "end_time": "0.5",
                    "alternatives": [{"content": "Hello", "confidence": "0.99"}],
                    "type": "pronunciation"
                }
            ]
        },
        "status": "COMPLETED"
    }
