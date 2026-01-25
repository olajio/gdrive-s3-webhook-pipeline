"""
End-to-end integration tests for the webhook pipeline.
"""
import json
import time
import boto3
import pytest
from datetime import datetime

# These tests require actual AWS resources to be deployed
# Run with: pytest tests/integration/test_e2e.py -v

pytestmark = pytest.mark.integration


class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.fixture(scope='class')
    def aws_clients(self):
        """Create AWS clients."""
        return {
            's3': boto3.client('s3'),
            'lambda': boto3.client('lambda'),
            'dynamodb': boto3.resource('dynamodb')
        }
    
    @pytest.fixture(scope='class')
    def config(self):
        """Load configuration from environment."""
        import os
        return {
            'webhook_handler_function': os.environ.get('WEBHOOK_HANDLER_FUNCTION', 'gdrive-webhook-webhook-handler-dev'),
            'channel_renewal_function': os.environ.get('CHANNEL_RENEWAL_FUNCTION', 'gdrive-webhook-channel-renewal-dev'),
            's3_bucket': os.environ.get('S3_BUCKET', 'gdrive-sync-dev'),
            'channels_table': os.environ.get('CHANNELS_TABLE', 'gdrive-webhook-channels-dev'),
            'sync_log_table': os.environ.get('SYNC_LOG_TABLE', 'gdrive-webhook-sync-log-dev')
        }
    
    def test_channel_renewal_lambda_invocation(self, aws_clients, config):
        """Test that channel renewal Lambda can be invoked."""
        response = aws_clients['lambda'].invoke(
            FunctionName=config['channel_renewal_function'],
            InvocationType='RequestResponse',
            Payload=json.dumps({})
        )
        
        assert response['StatusCode'] == 200
        
        payload = json.loads(response['Payload'].read())
        assert 'body' in payload
        
        body = json.loads(payload['body'])
        assert 'message' in body or 'summary' in body
    
    def test_webhook_handler_sync_notification(self, aws_clients, config):
        """Test webhook handler with sync notification."""
        event = {
            'headers': {
                'X-Goog-Channel-Id': 'test-channel-integration',
                'X-Goog-Channel-Token': 'test-token',
                'X-Goog-Resource-State': 'sync'
            }
        }
        
        response = aws_clients['lambda'].invoke(
            FunctionName=config['webhook_handler_function'],
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        assert response['StatusCode'] == 200
        
        payload = json.loads(response['Payload'].read())
        # Note: Will fail signature validation without actual webhook token
        # This is expected in testing
        assert payload['statusCode'] in [200, 401]
    
    def test_s3_bucket_exists(self, aws_clients, config):
        """Test that S3 bucket exists and is accessible."""
        response = aws_clients['s3'].head_bucket(Bucket=config['s3_bucket'])
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_dynamodb_tables_exist(self, aws_clients, config):
        """Test that DynamoDB tables exist."""
        channels_table = aws_clients['dynamodb'].Table(config['channels_table'])
        sync_log_table = aws_clients['dynamodb'].Table(config['sync_log_table'])
        
        # Describe tables (will raise exception if they don't exist)
        assert channels_table.table_status in ['ACTIVE', 'UPDATING']
        assert sync_log_table.table_status in ['ACTIVE', 'UPDATING']
    
    def test_write_to_sync_log(self, aws_clients, config):
        """Test writing to sync log table."""
        sync_log_table = aws_clients['dynamodb'].Table(config['sync_log_table'])
        
        test_item = {
            'file_id': f'test-file-{int(time.time())}',
            'timestamp': datetime.utcnow().isoformat(),
            'file_name': 'test.txt',
            'status': 'success',
            's3_key': 'gdrive/test/test.txt'
        }
        
        sync_log_table.put_item(Item=test_item)
        
        # Verify item was written
        response = sync_log_table.get_item(
            Key={
                'file_id': test_item['file_id'],
                'timestamp': test_item['timestamp']
            }
        )
        
        assert 'Item' in response
        assert response['Item']['file_name'] == 'test.txt'
        
        # Clean up
        sync_log_table.delete_item(
            Key={
                'file_id': test_item['file_id'],
                'timestamp': test_item['timestamp']
            }
        )
    
    def test_query_sync_log_by_status(self, aws_clients, config):
        """Test querying sync log by status using GSI."""
        sync_log_table = aws_clients['dynamodb'].Table(config['sync_log_table'])
        
        # Query using GSI
        response = sync_log_table.query(
            IndexName='status-timestamp-index',
            KeyConditionExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'success'},
            Limit=10
        )
        
        # Should not error (even if empty)
        assert 'Items' in response


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
