"""
Unit tests for channel_renewal Lambda function.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Mock environment variables before importing
import os
os.environ['CHANNELS_TABLE'] = 'test-channels'
os.environ['SNS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'
os.environ['WEBHOOK_ENDPOINT'] = 'https://test.execute-api.us-east-1.amazonaws.com'
os.environ['GDRIVE_FOLDER_ID'] = 'test-folder-id'

from src.lambda import channel_renewal


class TestChannelRenewal:
    """Test channel renewal Lambda function."""
    
    @pytest.fixture
    def mock_event(self):
        """Create a mock CloudWatch Events event."""
        return {
            'source': 'aws.events',
            'detail-type': 'Scheduled Event'
        }
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Lambda context."""
        context = Mock()
        context.function_name = 'test-function'
        context.request_id = 'test-request-id'
        return context
    
    @patch('src.lambda.channel_renewal.get_drive_service')
    @patch('src.lambda.channel_renewal.get_active_channels')
    def test_no_channels_creates_initial_channel(
        self, mock_get_channels, mock_get_service, mock_event, mock_context
    ):
        """Test that initial channel is created when none exist."""
        mock_get_channels.return_value = []
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        
        with patch('src.lambda.channel_renewal.create_channel') as mock_create, \
             patch('src.lambda.channel_renewal.save_channel_info') as mock_save:
            
            mock_create.return_value = {
                'channel_id': 'new-channel-123',
                'resource_id': 'resource-123',
                'folder_id': 'test-folder-id',
                'expiration': (datetime.utcnow() + timedelta(hours=23)).isoformat(),
                'page_token': 'token-123'
            }
            
            response = channel_renewal.lambda_handler(mock_event, mock_context)
            
            assert response['statusCode'] == 200
            mock_create.assert_called_once()
            mock_save.assert_called_once()
    
    @patch('src.lambda.channel_renewal.get_drive_service')
    @patch('src.lambda.channel_renewal.get_active_channels')
    @patch('src.lambda.channel_renewal.should_renew_channel')
    @patch('src.lambda.channel_renewal.renew_channel')
    def test_renews_expiring_channels(
        self, mock_renew, mock_should_renew, mock_get_channels, 
        mock_get_service, mock_event, mock_context
    ):
        """Test that expiring channels are renewed."""
        mock_get_channels.return_value = [{
            'channel_id': 'old-channel-123',
            'resource_id': 'resource-123',
            'folder_id': 'folder-123',
            'expiration': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }]
        mock_should_renew.return_value = True
        mock_renew.return_value = {
            'channel_id': 'new-channel-456',
            'resource_id': 'resource-456',
            'folder_id': 'folder-123',
            'expiration': (datetime.utcnow() + timedelta(hours=23)).isoformat()
        }
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        
        response = channel_renewal.lambda_handler(mock_event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['summary']['renewed'] == 1
        mock_renew.assert_called_once()
    
    @patch('src.lambda.channel_renewal.get_drive_service')
    @patch('src.lambda.channel_renewal.get_active_channels')
    @patch('src.lambda.channel_renewal.should_renew_channel')
    def test_skips_valid_channels(
        self, mock_should_renew, mock_get_channels, 
        mock_get_service, mock_event, mock_context
    ):
        """Test that valid channels are not renewed."""
        mock_get_channels.return_value = [{
            'channel_id': 'channel-123',
            'resource_id': 'resource-123',
            'folder_id': 'folder-123',
            'expiration': (datetime.utcnow() + timedelta(hours=10)).isoformat()
        }]
        mock_should_renew.return_value = False
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        
        response = channel_renewal.lambda_handler(mock_event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['summary']['skipped'] == 1
        assert body['summary']['renewed'] == 0


class TestShouldRenewChannel:
    """Test channel renewal logic."""
    
    def test_renew_when_expiring_soon(self):
        """Test renewal when channel expires in less than 2 hours."""
        channel_info = {
            'channel_id': 'test-123',
            'expiration': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        
        assert channel_renewal.should_renew_channel(channel_info) is True
    
    def test_skip_when_still_valid(self):
        """Test skipping renewal when channel is still valid."""
        channel_info = {
            'channel_id': 'test-123',
            'expiration': (datetime.utcnow() + timedelta(hours=10)).isoformat()
        }
        
        assert channel_renewal.should_renew_channel(channel_info) is False
    
    def test_renew_when_no_expiration(self):
        """Test renewal when expiration is missing."""
        channel_info = {
            'channel_id': 'test-123'
        }
        
        assert channel_renewal.should_renew_channel(channel_info) is True


class TestCreateChannel:
    """Test channel creation."""
    
    @patch('src.lambda.channel_renewal.get_secret')
    @patch('src.lambda.channel_renewal.metrics')
    def test_create_channel_success(self, mock_metrics, mock_get_secret):
        """Test successful channel creation."""
        mock_get_secret.return_value = {'webhook_token': 'test-token'}
        
        mock_service = Mock()
        mock_response = {
            'id': 'channel-123',
            'resourceId': 'resource-123',
            'expiration': str(int((datetime.utcnow() + timedelta(hours=23)).timestamp() * 1000))
        }
        mock_service.files().watch().execute.return_value = mock_response
        mock_service.changes().getStartPageToken().execute.return_value = {
            'startPageToken': 'token-123'
        }
        
        channel_info = channel_renewal.create_channel(mock_service, 'folder-123')
        
        assert channel_info['channel_id'] == 'channel-123'
        assert channel_info['resource_id'] == 'resource-123'
        assert channel_info['folder_id'] == 'folder-123'
        assert 'page_token' in channel_info


class TestStopChannel:
    """Test channel stopping."""
    
    def test_stop_channel_success(self):
        """Test successful channel stop."""
        mock_service = Mock()
        mock_service.channels().stop().execute.return_value = {}
        
        result = channel_renewal.stop_channel(mock_service, 'channel-123', 'resource-123')
        
        assert result is True
        mock_service.channels().stop.assert_called_once()
    
    def test_stop_channel_not_found(self):
        """Test stopping non-existent channel."""
        from googleapiclient.errors import HttpError
        
        mock_service = Mock()
        mock_resp = Mock()
        mock_resp.status = 404
        error = HttpError(mock_resp, b'Not found')
        mock_service.channels().stop().execute.side_effect = error
        
        result = channel_renewal.stop_channel(mock_service, 'channel-123', 'resource-123')
        
        # Should return True (channel already gone)
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
