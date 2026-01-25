"""
Unit tests for webhook_handler Lambda function.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock environment variables before importing
import os
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['CHANNELS_TABLE'] = 'test-channels'
os.environ['SYNC_LOG_TABLE'] = 'test-sync-log'
os.environ['SNS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'

from src.lambda import webhook_handler


class TestWebhookHandler:
    """Test webhook handler Lambda function."""
    
    @pytest.fixture
    def mock_event(self):
        """Create a mock API Gateway event."""
        return {
            'headers': {
                'X-Goog-Channel-Id': 'test-channel-123',
                'X-Goog-Channel-Token': 'test-webhook-token',
                'X-Goog-Resource-State': 'update'
            },
            'body': None
        }
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Lambda context."""
        context = Mock()
        context.function_name = 'test-function'
        context.request_id = 'test-request-id'
        return context
    
    @patch('src.lambda.webhook_handler.get_secret')
    @patch('src.lambda.webhook_handler.validate_webhook_signature')
    def test_invalid_signature_returns_401(self, mock_validate, mock_get_secret, mock_event, mock_context):
        """Test that invalid webhook signature returns 401."""
        mock_get_secret.return_value = {'webhook_token': 'test-token'}
        mock_validate.return_value = False
        
        response = webhook_handler.lambda_handler(mock_event, mock_context)
        
        assert response['statusCode'] == 401
        assert 'Unauthorized' in response['body']
    
    @patch('src.lambda.webhook_handler.get_secret')
    @patch('src.lambda.webhook_handler.validate_webhook_signature')
    @patch('src.lambda.webhook_handler.get_drive_service')
    @patch('src.lambda.webhook_handler.get_changed_files')
    def test_sync_notification_returns_200(
        self, mock_get_files, mock_get_service, mock_validate, mock_get_secret, 
        mock_event, mock_context
    ):
        """Test that sync notification returns 200."""
        mock_get_secret.return_value = {'webhook_token': 'test-token'}
        mock_validate.return_value = True
        mock_event['headers']['X-Goog-Resource-State'] = 'sync'
        
        response = webhook_handler.lambda_handler(mock_event, mock_context)
        
        assert response['statusCode'] == 200
        assert 'Webhook verified' in response['body']
    
    @patch('src.lambda.webhook_handler.get_secret')
    @patch('src.lambda.webhook_handler.validate_webhook_signature')
    @patch('src.lambda.webhook_handler.get_drive_service')
    @patch('src.lambda.webhook_handler.get_changed_files')
    @patch('src.lambda.webhook_handler.process_file_change')
    def test_successful_file_processing(
        self, mock_process, mock_get_files, mock_get_service, 
        mock_validate, mock_get_secret, mock_event, mock_context
    ):
        """Test successful file processing."""
        mock_get_secret.return_value = {'webhook_token': 'test-token'}
        mock_validate.return_value = True
        mock_get_files.return_value = ['file-123']
        mock_process.return_value = {
            'file_id': 'file-123',
            'status': 'success',
            'message': 'File synced',
            's3_key': 'gdrive/file-123/test.csv'
        }
        
        response = webhook_handler.lambda_handler(mock_event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] == 1
        assert body['total'] == 1


class TestFileProcessing:
    """Test file processing logic."""
    
    @patch('src.lambda.webhook_handler.download_file_from_drive')
    @patch('src.lambda.webhook_handler.should_sync_file')
    @patch('src.lambda.webhook_handler.is_duplicate_file')
    @patch('src.lambda.webhook_handler.upload_to_s3')
    @patch('src.lambda.webhook_handler.log_sync_event')
    def test_process_file_change_success(
        self, mock_log, mock_upload, mock_is_dup, mock_should_sync, mock_download
    ):
        """Test successful file processing."""
        mock_service = Mock()
        
        # Mock file download
        file_content = b'test,data\n1,2'
        file_metadata = {
            'id': 'file-123',
            'name': 'test.csv',
            'mimeType': 'text/csv',
            'size': '100',
            'md5Checksum': 'abc123'
        }
        mock_download.return_value = (file_content, file_metadata)
        mock_should_sync.return_value = True
        mock_is_dup.return_value = False
        mock_upload.return_value = 'gdrive/file-123/test.csv'
        
        result = webhook_handler.process_file_change(mock_service, 'file-123')
        
        assert result['status'] == 'success'
        assert result['file_id'] == 'file-123'
        mock_upload.assert_called_once()
        mock_log.assert_called_once()
    
    @patch('src.lambda.webhook_handler.download_file_from_drive')
    @patch('src.lambda.webhook_handler.should_sync_file')
    @patch('src.lambda.webhook_handler.log_sync_event')
    def test_process_file_change_skipped(
        self, mock_log, mock_should_sync, mock_download
    ):
        """Test file processing when file should be skipped."""
        mock_service = Mock()
        
        file_content = b'folder'
        file_metadata = {
            'id': 'folder-123',
            'name': 'My Folder',
            'mimeType': 'application/vnd.google-apps.folder',
            'size': '0'
        }
        mock_download.return_value = (file_content, file_metadata)
        mock_should_sync.return_value = False
        
        result = webhook_handler.process_file_change(mock_service, 'folder-123')
        
        assert result['status'] == 'skipped'
        mock_log.assert_called_once()
    
    @patch('src.lambda.webhook_handler.download_file_from_drive')
    @patch('src.lambda.webhook_handler.should_sync_file')
    @patch('src.lambda.webhook_handler.is_duplicate_file')
    @patch('src.lambda.webhook_handler.log_sync_event')
    def test_process_file_change_duplicate(
        self, mock_log, mock_is_dup, mock_should_sync, mock_download
    ):
        """Test file processing when file is a duplicate."""
        mock_service = Mock()
        
        file_content = b'test,data'
        file_metadata = {
            'id': 'file-123',
            'name': 'test.csv',
            'mimeType': 'text/csv',
            'size': '100',
            'md5Checksum': 'abc123'
        }
        mock_download.return_value = (file_content, file_metadata)
        mock_should_sync.return_value = True
        mock_is_dup.return_value = True
        
        result = webhook_handler.process_file_change(mock_service, 'file-123')
        
        assert result['status'] == 'skipped'
        assert 'Duplicate' in result['message']


class TestS3Upload:
    """Test S3 upload functionality."""
    
    @patch('src.lambda.webhook_handler.s3_client')
    @patch('src.lambda.webhook_handler.metrics')
    def test_upload_to_s3_success(self, mock_metrics, mock_s3):
        """Test successful S3 upload."""
        file_content = b'test data'
        file_metadata = {
            'id': 'file-123',
            'name': 'test.txt',
            'mimeType': 'text/plain',
            'createdTime': '2026-01-25T12:00:00Z',
            'modifiedTime': '2026-01-25T12:00:00Z',
            'md5Checksum': 'abc123'
        }
        
        s3_key = webhook_handler.upload_to_s3(file_content, file_metadata)
        
        assert s3_key == 'gdrive/file-123/test.txt'
        mock_s3.put_object.assert_called_once()
        
        # Verify metadata is included
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs['Metadata']['gdrive-file-id'] == 'file-123'
        assert call_kwargs['ServerSideEncryption'] == 'AES256'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
