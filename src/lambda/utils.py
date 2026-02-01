"""
Shared utility functions for Customer Care Call Processing System.

This module provides common functionality used across all Lambda functions
in the call processing pipeline.
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients (initialized once, reused across invocations)
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')
S3_BUCKET = os.environ.get('S3_BUCKET', 'customer-care-call-processor')
GOOGLE_CREDENTIALS_SECRET = os.environ.get('GOOGLE_CREDENTIALS_SECRET', 'google-drive-credentials')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


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


def is_audio_file(filename: str) -> bool:
    """
    Check if a file is an audio file based on extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if audio file, False otherwise
    """
    audio_extensions = {
        '.mp3', '.wav', '.flac', '.ogg', '.m4a', 
        '.wma', '.aac', '.webm', '.amr', '.mp4'
    }
    ext = os.path.splitext(filename.lower())[1]
    return ext in audio_extensions


def get_audio_format(filename: str) -> str:
    """
    Get audio format for Amazon Transcribe from filename.
    
    Args:
        filename: Name of the audio file
        
    Returns:
        Media format string for Transcribe API
    """
    ext = os.path.splitext(filename.lower())[1].lstrip('.')
    format_map = {
        'mp3': 'mp3',
        'mp4': 'mp4',
        'm4a': 'mp4',
        'wav': 'wav',
        'flac': 'flac',
        'ogg': 'ogg',
        'webm': 'webm',
        'amr': 'amr',
        'wma': 'mp3',
        'aac': 'mp4'
    }
    return format_map.get(ext, 'mp3')


def generate_call_id(file_id: str, timestamp: Optional[str] = None) -> str:
    """
    Generate a unique call ID from file ID and timestamp.
    
    Args:
        file_id: Google Drive file ID
        timestamp: Optional timestamp string
        
    Returns:
        Unique call ID
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    
    combined = f"{file_id}-{timestamp}"
    hash_suffix = hashlib.sha256(combined.encode()).hexdigest()[:8]
    return f"call-{hash_suffix}"


def generate_s3_key(call_id: str, prefix: str, extension: str) -> str:
    """
    Generate S3 key with date-based prefix.
    
    Args:
        call_id: Unique call identifier
        prefix: Folder prefix (e.g., 'raw-audio', 'transcripts', 'summaries')
        extension: File extension
        
    Returns:
        Full S3 key path
    """
    date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
    return f"{prefix}/{date_prefix}/{call_id}.{extension}"


def get_presigned_url(s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate presigned URL for S3 object access.
    
    Args:
        s3_key: S3 object key
        expiration: URL expiration in seconds
        
    Returns:
        Presigned URL or None if error
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None


def update_call_status(call_id: str, status: str, 
                       additional_fields: Optional[Dict[str, Any]] = None) -> bool:
    """
    Update call status in DynamoDB.
    
    Args:
        call_id: Unique call identifier
        status: New status value
        additional_fields: Optional additional fields to update
        
    Returns:
        True if successful, False otherwise
    """
    table = dynamodb.Table(DYNAMODB_TABLE)
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    update_expr = 'SET #status = :status, updated_at = :updated'
    expr_names = {'#status': 'status'}
    expr_values = {
        ':status': status,
        ':updated': timestamp
    }
    
    if additional_fields:
        for key, value in additional_fields.items():
            update_expr += f', {key} = :{key}'
            expr_values[f':{key}'] = value
    
    try:
        table.update_item(
            Key={'call_id': call_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
        return True
    except ClientError as e:
        logger.error(f"Failed to update status for {call_id}: {e}")
        return False


def build_api_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build standardized API Gateway response.
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        
    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


def parse_caller_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract caller ID from audio filename if present.
    Expected formats: 
    - caller_+1234567890_2024-01-15.mp3
    - call_customer123_timestamp.wav
    
    Args:
        filename: Audio filename
        
    Returns:
        Caller ID if found, None otherwise
    """
    import re
    
    # Pattern for phone number
    phone_pattern = r'caller_(\+?\d{10,15})_'
    phone_match = re.search(phone_pattern, filename)
    if phone_match:
        return phone_match.group(1)
    
    # Pattern for customer ID
    customer_pattern = r'call_([a-zA-Z0-9]+)_'
    customer_match = re.search(customer_pattern, filename)
    if customer_match:
        return customer_match.group(1)
    
    return None


def sanitize_text_for_dynamodb(text: str, max_length: int = 400000) -> str:
    """
    Sanitize text for DynamoDB storage.
    DynamoDB has a 400KB item limit, so we need to truncate if necessary.
    
    Args:
        text: Text to sanitize
        max_length: Maximum character length
        
    Returns:
        Sanitized text
    """
    if len(text) > max_length:
        logger.warning(f"Text truncated from {len(text)} to {max_length} characters")
        return text[:max_length] + "... [truncated]"
    return text
