"""
Shared utility functions for Google Drive to S3 webhook pipeline.
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients (initialized once, reused across invocations)
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')
sns_client = boto3.client('sns')

# Environment variables
CHANNELS_TABLE = os.environ.get('CHANNELS_TABLE', 'gdrive_channels')
SYNC_LOG_TABLE = os.environ.get('SYNC_LOG_TABLE', 'gdrive_s3_sync_log')
S3_BUCKET = os.environ.get('S3_BUCKET')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
GOOGLE_CREDENTIALS_SECRET = os.environ.get('GOOGLE_CREDENTIALS_SECRET', 'gdrive-webhook-credentials')


def validate_webhook_signature(headers: Dict[str, str], webhook_token: str) -> bool:
    """
    Validate that the webhook request came from Google Drive.
    
    Args:
        headers: HTTP request headers
        webhook_token: Expected webhook token from Secrets Manager
        
    Returns:
        True if valid, False otherwise
    """
    received_token = headers.get('X-Goog-Channel-Token', '')
    
    if not received_token:
        logger.warning("Missing X-Goog-Channel-Token header")
        return False
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(received_token, webhook_token)


def get_secret(secret_name: str) -> Dict[str, Any]:
    """
    Retrieve a secret from AWS Secrets Manager.
    
    Args:
        secret_name: Name of the secret
        
    Returns:
        Secret value as dictionary
        
    Raises:
        ClientError: If secret cannot be retrieved
    """
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise


def get_google_credentials() -> Dict[str, Any]:
    """
    Get Google service account credentials from Secrets Manager.
    
    Returns:
        Service account credentials dictionary
    """
    return get_secret(GOOGLE_CREDENTIALS_SECRET)


def should_sync_file(file_metadata: Dict[str, Any], allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    Determine if a file should be synced based on filters.
    
    Args:
        file_metadata: Google Drive file metadata
        allowed_extensions: List of allowed file extensions (e.g., ['.csv', '.json'])
        
    Returns:
        True if file should be synced, False otherwise
    """
    # Skip folders
    mime_type = file_metadata.get('mimeType', '')
    if mime_type == 'application/vnd.google-apps.folder':
        logger.info(f"Skipping folder: {file_metadata.get('name')}")
        return False
    
    # Skip Google Workspace native files (Docs, Sheets, etc.)
    if mime_type.startswith('application/vnd.google-apps.'):
        logger.info(f"Skipping Google Workspace file: {file_metadata.get('name')}")
        return False
    
    # Check file extension if filter is provided
    if allowed_extensions:
        file_name = file_metadata.get('name', '')
        extension = os.path.splitext(file_name)[1].lower()
        
        if extension not in allowed_extensions:
            logger.info(f"Skipping file with extension {extension}: {file_name}")
            return False
    
    # Check file size (default max: 100 MB)
    max_size_bytes = int(os.environ.get('MAX_FILE_SIZE_MB', '100')) * 1024 * 1024
    file_size = int(file_metadata.get('size', 0))
    
    if file_size > max_size_bytes:
        logger.warning(f"File too large ({file_size} bytes): {file_metadata.get('name')}")
        return False
    
    return True


def is_duplicate_file(file_id: str, md5_checksum: str) -> bool:
    """
    Check if file with same content already exists in S3.
    
    Args:
        file_id: Google Drive file ID
        md5_checksum: MD5 hash of file content
        
    Returns:
        True if duplicate exists, False otherwise
    """
    try:
        # Check S3 object metadata
        s3_key = f"gdrive/{file_id}"
        response = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        
        # Compare MD5 hashes (S3 stores as ETag for simple uploads)
        s3_md5 = response.get('ETag', '').strip('"')
        
        if s3_md5 == md5_checksum:
            logger.info(f"Duplicate file detected (MD5 match): {file_id}")
            return True
            
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # Object doesn't exist, not a duplicate
            return False
        else:
            logger.error(f"Error checking for duplicate: {e}")
            raise
    
    return False


def log_sync_event(
    file_id: str,
    file_name: str,
    status: str,
    s3_key: Optional[str] = None,
    error_message: Optional[str] = None,
    file_size: Optional[int] = None,
    md5_checksum: Optional[str] = None
) -> None:
    """
    Log a sync event to DynamoDB.
    
    Args:
        file_id: Google Drive file ID
        file_name: File name
        status: Sync status ('success', 'failure', 'skipped')
        s3_key: S3 object key (if uploaded)
        error_message: Error details (if failed)
        file_size: File size in bytes
        md5_checksum: MD5 hash of file content
    """
    table = dynamodb.Table(SYNC_LOG_TABLE)
    
    item = {
        'file_id': file_id,
        'timestamp': datetime.utcnow().isoformat(),
        'file_name': file_name,
        'status': status,
        'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
    }
    
    if s3_key:
        item['s3_key'] = s3_key
    if error_message:
        item['error_message'] = error_message
    if file_size is not None:
        item['file_size'] = file_size
    if md5_checksum:
        item['md5_checksum'] = md5_checksum
    
    try:
        table.put_item(Item=item)
        logger.info(f"Logged sync event: {file_id} - {status}")
    except ClientError as e:
        logger.error(f"Failed to log sync event: {e}")
        # Don't raise - logging failure shouldn't stop the pipeline


def send_alert(subject: str, message: str) -> None:
    """
    Send an alert via SNS.
    
    Args:
        subject: Alert subject
        message: Alert message body
    """
    if not SNS_TOPIC_ARN:
        logger.warning("SNS_TOPIC_ARN not configured, skipping alert")
        return
    
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
        logger.info(f"Sent alert: {subject}")
    except ClientError as e:
        logger.error(f"Failed to send SNS alert: {e}")


def get_channel_info(channel_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve channel information from DynamoDB.
    
    Args:
        channel_id: Google Drive webhook channel ID
        
    Returns:
        Channel info dictionary or None if not found
    """
    table = dynamodb.Table(CHANNELS_TABLE)
    
    try:
        response = table.get_item(Key={'channel_id': channel_id})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Failed to retrieve channel info: {e}")
        return None


def save_channel_info(
    channel_id: str,
    resource_id: str,
    folder_id: str,
    expiration: str,
    page_token: Optional[str] = None
) -> None:
    """
    Save channel information to DynamoDB.
    
    Args:
        channel_id: Google Drive webhook channel ID
        resource_id: Google Drive resource ID
        folder_id: Google Drive folder ID being watched
        expiration: ISO format expiration timestamp
        page_token: Change token for incremental sync
    """
    table = dynamodb.Table(CHANNELS_TABLE)
    
    item = {
        'channel_id': channel_id,
        'resource_id': resource_id,
        'folder_id': folder_id,
        'expiration': expiration,
        'created_at': datetime.utcnow().isoformat(),
        'last_renewed': datetime.utcnow().isoformat(),
        'status': 'active'
    }
    
    if page_token:
        item['page_token'] = page_token
    
    try:
        table.put_item(Item=item)
        logger.info(f"Saved channel info: {channel_id}")
    except ClientError as e:
        logger.error(f"Failed to save channel info: {e}")
        raise


def update_page_token(channel_id: str, page_token: str) -> None:
    """
    Update the page token for incremental sync.
    
    Args:
        channel_id: Google Drive webhook channel ID
        page_token: New page token
    """
    table = dynamodb.Table(CHANNELS_TABLE)
    
    try:
        table.update_item(
            Key={'channel_id': channel_id},
            UpdateExpression='SET page_token = :token, last_updated = :ts',
            ExpressionAttributeValues={
                ':token': page_token,
                ':ts': datetime.utcnow().isoformat()
            }
        )
        logger.info(f"Updated page token for channel: {channel_id}")
    except ClientError as e:
        logger.error(f"Failed to update page token: {e}")


def calculate_md5(content: bytes) -> str:
    """
    Calculate MD5 hash of content.
    
    Args:
        content: File content bytes
        
    Returns:
        MD5 hash as hex string
    """
    return hashlib.md5(content).hexdigest()


class MetricsPublisher:
    """Helper class for publishing CloudWatch metrics."""
    
    def __init__(self, namespace: str = 'GoogleDriveWebhook'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
    
    def publish_metric(self, metric_name: str, value: float, unit: str = 'Count'):
        """Publish a single metric to CloudWatch."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            logger.debug(f"Published metric: {metric_name}={value}")
        except ClientError as e:
            logger.error(f"Failed to publish metric {metric_name}: {e}")
