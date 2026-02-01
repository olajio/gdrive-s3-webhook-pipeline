"""
Integration tests for the Call Processing Pipeline.

These tests verify end-to-end functionality of the system.
Requires AWS credentials and resources to be deployed.
"""
import json
import os
import pytest
import boto3
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Skip integration tests if not in integration test mode
pytestmark = pytest.mark.skipif(
    os.environ.get('RUN_INTEGRATION_TESTS') != 'true',
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to run."
)


@pytest.fixture(scope="module")
def aws_region():
    """AWS region for tests."""
    return os.environ.get('AWS_REGION', 'us-east-1')


@pytest.fixture(scope="module")
def s3_bucket():
    """S3 bucket name for tests."""
    return os.environ.get('S3_BUCKET', 'customer-care-call-processor-dev')


@pytest.fixture(scope="module")
def dynamodb_table():
    """DynamoDB table name for tests."""
    return os.environ.get('DYNAMODB_TABLE', 'customer-care-call-summaries-dev')


@pytest.fixture(scope="module")
def api_url():
    """API Gateway URL for tests."""
    return os.environ.get('API_URL')


@pytest.fixture(scope="module")
def s3_client(aws_region):
    """S3 client for tests."""
    return boto3.client('s3', region_name=aws_region)


@pytest.fixture(scope="module")
def dynamodb_resource(aws_region):
    """DynamoDB resource for tests."""
    return boto3.resource('dynamodb', region_name=aws_region)


@pytest.fixture(scope="module")
def step_functions_client(aws_region):
    """Step Functions client for tests."""
    return boto3.client('stepfunctions', region_name=aws_region)


class TestS3Integration:
    """Test S3 bucket configuration and access."""
    
    def test_bucket_exists(self, s3_client, s3_bucket):
        """S3 bucket should exist."""
        response = s3_client.head_bucket(Bucket=s3_bucket)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_bucket_has_folders(self, s3_client, s3_bucket):
        """S3 bucket should have expected folder structure."""
        expected_prefixes = ['raw-audio/', 'transcripts/', 'summaries/']
        
        response = s3_client.list_objects_v2(
            Bucket=s3_bucket,
            Prefix='',
            Delimiter='/'
        )
        
        actual_prefixes = [p['Prefix'] for p in response.get('CommonPrefixes', [])]
        
        for prefix in expected_prefixes:
            assert prefix in actual_prefixes, f"Missing prefix: {prefix}"
    
    def test_can_upload_and_download(self, s3_client, s3_bucket):
        """Should be able to upload and download files."""
        test_key = 'test/integration-test.txt'
        test_content = 'Integration test content'
        
        # Upload
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=test_key,
            Body=test_content.encode()
        )
        
        # Download
        response = s3_client.get_object(Bucket=s3_bucket, Key=test_key)
        downloaded = response['Body'].read().decode()
        
        assert downloaded == test_content
        
        # Cleanup
        s3_client.delete_object(Bucket=s3_bucket, Key=test_key)


class TestDynamoDBIntegration:
    """Test DynamoDB table configuration and access."""
    
    def test_table_exists(self, dynamodb_resource, dynamodb_table):
        """DynamoDB table should exist."""
        table = dynamodb_resource.Table(dynamodb_table)
        assert table.table_status == 'ACTIVE'
    
    def test_table_has_gsi(self, dynamodb_resource, dynamodb_table):
        """Table should have required GSIs."""
        table = dynamodb_resource.Table(dynamodb_table)
        
        expected_gsis = ['status-index', 'user-index']
        actual_gsi_names = [gsi['IndexName'] for gsi in table.global_secondary_indexes or []]
        
        for gsi in expected_gsis:
            assert gsi in actual_gsi_names, f"Missing GSI: {gsi}"
    
    def test_can_put_and_get_item(self, dynamodb_resource, dynamodb_table):
        """Should be able to put and get items."""
        table = dynamodb_resource.Table(dynamodb_table)
        test_call_id = f"test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Put item
        table.put_item(
            Item={
                'call_id': test_call_id,
                'status': 'TESTING',
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'ttl': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            }
        )
        
        # Get item
        response = table.get_item(Key={'call_id': test_call_id})
        item = response.get('Item')
        
        assert item is not None
        assert item['status'] == 'TESTING'
        
        # Cleanup
        table.delete_item(Key={'call_id': test_call_id})


class TestStepFunctionsIntegration:
    """Test Step Functions state machine."""
    
    @pytest.fixture
    def state_machine_arn(self, step_functions_client):
        """Get state machine ARN."""
        response = step_functions_client.list_state_machines()
        for sm in response['stateMachines']:
            if 'call-processing' in sm['name'].lower():
                return sm['stateMachineArn']
        pytest.skip("State machine not found")
    
    def test_state_machine_exists(self, step_functions_client, state_machine_arn):
        """State machine should exist and be active."""
        response = step_functions_client.describe_state_machine(
            stateMachineArn=state_machine_arn
        )
        
        assert response['status'] == 'ACTIVE'
    
    def test_state_machine_definition(self, step_functions_client, state_machine_arn):
        """State machine should have expected states."""
        response = step_functions_client.describe_state_machine(
            stateMachineArn=state_machine_arn
        )
        
        definition = json.loads(response['definition'])
        
        expected_states = [
            'UpdateStatusTranscribing',
            'StartTranscription',
            'WaitForTranscription',
            'ProcessTranscript',
            'GenerateSummary',
            'SaveSummary'
        ]
        
        for state in expected_states:
            assert state in definition['States'], f"Missing state: {state}"


class TestAPIIntegration:
    """Test API Gateway endpoints."""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for API requests."""
        # In real tests, this would authenticate with Cognito
        return os.environ.get('API_AUTH_TOKEN')
    
    @pytest.fixture
    def http_client(self):
        """HTTP client for API requests."""
        import urllib.request
        return urllib.request
    
    @pytest.mark.skipif(
        os.environ.get('API_URL') is None,
        reason="API_URL not configured"
    )
    def test_list_summaries_endpoint(self, api_url, auth_token, http_client):
        """GET /summaries should return list of summaries."""
        request = http_client.Request(
            f"{api_url}/summaries",
            headers={
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            }
        )
        
        response = http_client.urlopen(request)
        data = json.loads(response.read())
        
        assert 'items' in data
        assert 'pagination' in data
    
    @pytest.mark.skipif(
        os.environ.get('API_URL') is None,
        reason="API_URL not configured"
    )
    def test_health_check(self, api_url, http_client):
        """Health check endpoint should be accessible."""
        request = http_client.Request(f"{api_url}/health")
        
        response = http_client.urlopen(request)
        data = json.loads(response.read())
        
        assert data.get('status') == 'healthy'


class TestEndToEndPipeline:
    """Test complete call processing pipeline."""
    
    @pytest.fixture
    def sample_audio_file(self):
        """Create a sample audio file for testing."""
        # In real tests, this would be an actual audio file
        return b'FAKE_AUDIO_DATA_FOR_TESTING'
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get('RUN_E2E_TESTS') != 'true',
        reason="E2E tests disabled. Set RUN_E2E_TESTS=true to run."
    )
    def test_full_pipeline(
        self,
        s3_client,
        s3_bucket,
        dynamodb_resource,
        dynamodb_table,
        step_functions_client,
        sample_audio_file
    ):
        """Test complete pipeline from audio upload to summary."""
        import time
        
        # Generate test call ID
        test_call_id = f"e2e-test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
        s3_key = f"raw-audio/{date_prefix}/{test_call_id}.mp3"
        
        try:
            # Step 1: Upload audio file
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=sample_audio_file,
                ContentType='audio/mpeg'
            )
            
            # Step 2: Create DynamoDB record (simulating webhook handler)
            table = dynamodb_resource.Table(dynamodb_table)
            table.put_item(
                Item={
                    'call_id': test_call_id,
                    'status': 'PENDING',
                    's3_bucket': s3_bucket,
                    's3_key': s3_key,
                    'caller_id': '+15555551234',
                    'assigned_user_id': 'test-user',
                    'created_at': datetime.utcnow().isoformat() + 'Z'
                }
            )
            
            # Step 3: Start Step Functions execution
            state_machines = step_functions_client.list_state_machines()
            state_machine_arn = None
            for sm in state_machines['stateMachines']:
                if 'call-processing' in sm['name'].lower():
                    state_machine_arn = sm['stateMachineArn']
                    break
            
            if state_machine_arn:
                execution = step_functions_client.start_execution(
                    stateMachineArn=state_machine_arn,
                    name=f"e2e-test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    input=json.dumps({
                        'call_id': test_call_id,
                        's3_bucket': s3_bucket,
                        's3_key': s3_key,
                        'caller_id': '+15555551234',
                        'assigned_user_id': 'test-user'
                    })
                )
                
                # Step 4: Wait for execution to complete (with timeout)
                max_wait = 300  # 5 minutes
                waited = 0
                while waited < max_wait:
                    status = step_functions_client.describe_execution(
                        executionArn=execution['executionArn']
                    )
                    
                    if status['status'] in ['SUCCEEDED', 'FAILED', 'ABORTED']:
                        break
                    
                    time.sleep(10)
                    waited += 10
                
                # Step 5: Verify results
                assert status['status'] == 'SUCCEEDED', f"Execution failed: {status.get('error')}"
                
                # Verify DynamoDB record was updated
                response = table.get_item(Key={'call_id': test_call_id})
                item = response.get('Item')
                
                assert item is not None
                assert item['status'] == 'COMPLETED'
                assert 'summary' in item
                assert 'key_points' in item
        
        finally:
            # Cleanup
            try:
                s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
            except:
                pass
            
            try:
                table.delete_item(Key={'call_id': test_call_id})
            except:
                pass


class TestWebSocketIntegration:
    """Test WebSocket API functionality."""
    
    @pytest.fixture
    def websocket_url(self):
        """Get WebSocket API URL."""
        return os.environ.get('WEBSOCKET_URL')
    
    @pytest.mark.skipif(
        os.environ.get('WEBSOCKET_URL') is None,
        reason="WEBSOCKET_URL not configured"
    )
    def test_websocket_connection(self, websocket_url):
        """Should be able to establish WebSocket connection."""
        # This would require websocket-client library
        # pip install websocket-client
        try:
            import websocket
            
            ws = websocket.create_connection(websocket_url)
            assert ws.connected
            ws.close()
        except ImportError:
            pytest.skip("websocket-client not installed")
