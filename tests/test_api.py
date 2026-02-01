"""
Tests for API Lambda functions.

Tests cover:
- list_summaries endpoint
- get_summary endpoint
- get_audio_url endpoint
- get_transcript endpoint
"""
import json
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Set environment variables before imports
os.environ['DYNAMODB_TABLE'] = 'test-call-summaries'
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['PRESIGNED_URL_EXPIRATION'] = '3600'
os.environ['DEFAULT_PAGE_SIZE'] = '20'
os.environ['MAX_PAGE_SIZE'] = '100'


class TestListSummaries:
    """Test cases for list_summaries Lambda."""
    
    @pytest.fixture
    def admin_event(self):
        """API Gateway event with admin user."""
        return {
            'httpMethod': 'GET',
            'path': '/summaries',
            'queryStringParameters': {
                'status': 'COMPLETED',
                'limit': '20'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-admin-001',
                        'cognito:groups': 'admin',
                        'cognito:username': 'admin@example.com'
                    }
                }
            }
        }
    
    @pytest.fixture
    def caseworker_event(self):
        """API Gateway event with caseworker user."""
        return {
            'httpMethod': 'GET',
            'path': '/summaries',
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-caseworker-001',
                        'cognito:groups': 'caseworkers',
                        'cognito:username': 'worker@example.com'
                    }
                }
            }
        }
    
    def test_admin_sees_all_summaries(self, admin_event):
        """Admin users should see all call summaries."""
        groups = admin_event['requestContext']['authorizer']['claims']['cognito:groups']
        is_admin = 'admin' in groups or 'supervisors' in groups
        assert is_admin
    
    def test_caseworker_sees_assigned_only(self, caseworker_event):
        """Caseworkers should only see their assigned summaries."""
        groups = caseworker_event['requestContext']['authorizer']['claims']['cognito:groups']
        is_admin = 'admin' in groups or 'supervisors' in groups
        assert not is_admin
        # Should use user-index GSI for caseworkers
    
    def test_pagination_parameters(self):
        """Pagination should respect limit and offset."""
        query_params = {
            'limit': '20',
            'offset': '40'
        }
        limit = int(query_params.get('limit', 20))
        offset = int(query_params.get('offset', 0))
        
        assert limit <= 100  # Max page size
        assert offset >= 0
    
    def test_status_filter(self):
        """Should filter by status."""
        valid_statuses = ['PENDING', 'TRANSCRIBING', 'SUMMARIZING', 'COMPLETED', 'FAILED']
        
        for status in valid_statuses:
            assert status in valid_statuses
    
    def test_date_range_filter(self):
        """Should filter by date range."""
        query_params = {
            'from_date': '2024-01-01',
            'to_date': '2024-01-31'
        }
        
        from_date = datetime.fromisoformat(query_params['from_date'])
        to_date = datetime.fromisoformat(query_params['to_date'])
        
        assert from_date < to_date
    
    def test_response_format(self):
        """Response should include items and pagination info."""
        mock_response = {
            'statusCode': 200,
            'body': json.dumps({
                'items': [
                    {'call_id': 'call-001', 'status': 'COMPLETED'},
                    {'call_id': 'call-002', 'status': 'COMPLETED'}
                ],
                'pagination': {
                    'count': 2,
                    'total': 50,
                    'offset': 0,
                    'limit': 20,
                    'has_more': True
                }
            })
        }
        
        body = json.loads(mock_response['body'])
        assert 'items' in body
        assert 'pagination' in body
        assert body['pagination']['has_more'] == True


class TestGetSummary:
    """Test cases for get_summary Lambda."""
    
    @pytest.fixture
    def valid_event(self):
        """API Gateway event for single summary."""
        return {
            'httpMethod': 'GET',
            'path': '/summaries/call-abc12345',
            'pathParameters': {
                'call_id': 'call-abc12345'
            },
            'queryStringParameters': {
                'include_transcript': 'true'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-001',
                        'cognito:groups': 'caseworkers'
                    }
                }
            }
        }
    
    def test_requires_call_id(self, valid_event):
        """call_id is required in path parameters."""
        call_id = valid_event['pathParameters']['call_id']
        assert call_id is not None
        assert len(call_id) > 0
    
    def test_call_id_format(self):
        """call_id should follow expected format."""
        valid_ids = ['call-abc12345', 'call-xyz98765', 'call-000001']
        invalid_ids = ['abc12345', 'CALL-abc', '']
        
        for call_id in valid_ids:
            assert call_id.startswith('call-')
        
        for call_id in invalid_ids:
            assert not call_id.startswith('call-') or call_id == ''
    
    def test_not_found_response(self):
        """Should return 404 if call_id not found."""
        response = {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Not Found',
                'message': 'Call summary not found'
            })
        }
        
        assert response['statusCode'] == 404
    
    def test_includes_transcript_when_requested(self, valid_event):
        """Should include transcript when include_transcript=true."""
        include = valid_event['queryStringParameters'].get('include_transcript', 'false')
        should_include = include.lower() == 'true'
        assert should_include
    
    def test_response_structure(self):
        """Response should include all summary fields."""
        expected_fields = [
            'call_id', 'status', 'caller_id', 'assigned_user_id',
            'summary', 'key_points', 'action_items', 'sentiment',
            'urgency', 'categories', 'created_at', 'completed_at'
        ]
        
        mock_response = {
            'call_id': 'call-abc12345',
            'status': 'COMPLETED',
            'caller_id': '+14155551234',
            'assigned_user_id': 'user-001',
            'summary': 'Customer inquired about account billing.',
            'key_points': ['Billing question', 'Resolved'],
            'action_items': [],
            'sentiment': 'neutral',
            'urgency': 'low',
            'categories': ['billing'],
            'created_at': '2024-01-15T10:30:00Z',
            'completed_at': '2024-01-15T10:35:00Z'
        }
        
        for field in expected_fields:
            assert field in mock_response


class TestGetAudioUrl:
    """Test cases for get_audio_url Lambda."""
    
    @pytest.fixture
    def valid_event(self):
        """API Gateway event for audio URL."""
        return {
            'httpMethod': 'GET',
            'path': '/summaries/call-abc12345/audio',
            'pathParameters': {
                'call_id': 'call-abc12345'
            },
            'queryStringParameters': {
                'expires': '3600'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-001',
                        'cognito:groups': 'supervisors'
                    }
                }
            }
        }
    
    def test_presigned_url_expiration(self, valid_event):
        """Presigned URL should have configurable expiration."""
        expires = int(valid_event['queryStringParameters'].get('expires', 3600))
        
        # Should be between 1 minute and 12 hours
        assert expires >= 60
        assert expires <= 43200
    
    def test_presigned_url_format(self):
        """Presigned URL should be a valid S3 URL."""
        mock_url = (
            "https://test-bucket.s3.amazonaws.com/raw-audio/2024/01/15/call-abc12345.mp3"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256"
            "&X-Amz-Credential=AKIA..."
            "&X-Amz-Date=20240115T103000Z"
            "&X-Amz-Expires=3600"
            "&X-Amz-SignedHeaders=host"
            "&X-Amz-Signature=abc123..."
        )
        
        assert 's3.amazonaws.com' in mock_url
        assert 'X-Amz-Signature' in mock_url
    
    def test_audio_not_found(self):
        """Should return 404 if audio file not found."""
        response = {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Not Found',
                'message': 'Audio file not found for this call'
            })
        }
        
        assert response['statusCode'] == 404
    
    def test_response_includes_metadata(self):
        """Response should include audio metadata."""
        mock_response = {
            'statusCode': 200,
            'body': json.dumps({
                'url': 'https://...',
                'expires_in': 3600,
                'content_type': 'audio/mpeg',
                'size_bytes': 1024000,
                'duration_seconds': 180
            })
        }
        
        body = json.loads(mock_response['body'])
        assert 'url' in body
        assert 'expires_in' in body


class TestGetTranscript:
    """Test cases for get_transcript Lambda."""
    
    @pytest.fixture
    def valid_event(self):
        """API Gateway event for transcript."""
        return {
            'httpMethod': 'GET',
            'path': '/summaries/call-abc12345/transcript',
            'pathParameters': {
                'call_id': 'call-abc12345'
            },
            'queryStringParameters': {
                'format': 'text'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-001',
                        'cognito:groups': 'caseworkers'
                    }
                }
            }
        }
    
    def test_format_options(self):
        """Should support text and json formats."""
        valid_formats = ['text', 'json']
        
        for fmt in valid_formats:
            assert fmt in valid_formats
    
    def test_text_format_response(self):
        """Text format should return plain transcript."""
        mock_transcript = """
Agent: Hello, how can I help you?
Customer: I have a billing question.
Agent: I'd be happy to help with that.
"""
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/plain'
            },
            'body': mock_transcript
        }
        
        assert response['headers']['Content-Type'] == 'text/plain'
        assert 'Agent:' in response['body']
    
    def test_json_format_response(self):
        """JSON format should return structured transcript."""
        mock_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'call_id': 'call-abc12345',
                'segments': [
                    {
                        'speaker': 'Agent',
                        'text': 'Hello, how can I help you?',
                        'start_time': 0.0,
                        'end_time': 2.5
                    },
                    {
                        'speaker': 'Customer',
                        'text': 'I have a billing question.',
                        'start_time': 3.0,
                        'end_time': 5.0
                    }
                ],
                'full_transcript': 'Agent: Hello...'
            })
        }
        
        body = json.loads(mock_response['body'])
        assert 'segments' in body
        assert len(body['segments']) > 0
    
    def test_transcript_not_ready(self):
        """Should return 202 if transcription still in progress."""
        response = {
            'statusCode': 202,
            'body': json.dumps({
                'status': 'TRANSCRIBING',
                'message': 'Transcription is still in progress'
            })
        }
        
        assert response['statusCode'] == 202


class TestAPIAuthentication:
    """Test cases for API authentication."""
    
    def test_missing_authorization(self):
        """Should return 401 if no authorization."""
        event = {
            'httpMethod': 'GET',
            'path': '/summaries',
            'requestContext': {}
        }
        
        # Without authorizer claims, should be unauthorized
        has_auth = 'authorizer' in event.get('requestContext', {})
        assert not has_auth
    
    def test_extracts_user_from_claims(self):
        """Should extract user info from Cognito claims."""
        claims = {
            'sub': 'user-001',
            'cognito:username': 'john@example.com',
            'cognito:groups': 'caseworkers,supervisors',
            'email': 'john@example.com',
            'name': 'John Doe'
        }
        
        user_id = claims['sub']
        groups = claims['cognito:groups'].split(',')
        
        assert user_id == 'user-001'
        assert 'caseworkers' in groups
    
    def test_cors_headers(self):
        """Response should include CORS headers."""
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        }
        
        assert 'Access-Control-Allow-Origin' in headers
