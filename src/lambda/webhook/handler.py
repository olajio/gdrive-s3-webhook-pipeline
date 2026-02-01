"""
AWS Lambda function to handle Google Drive webhook notifications.
Downloads audio files and triggers the Step Functions processing pipeline.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
import io
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET', 'customer-care-audio-dev')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')
STEP_FUNCTION_ARN = os.environ.get('STEP_FUNCTION_ARN')
WEBHOOK_TOKEN = os.environ.get('WEBHOOK_TOKEN')
GOOGLE_CREDENTIALS_SECRET = os.environ.get('GOOGLE_CREDENTIALS_SECRET', 'google-drive-service-account')

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')
secrets_client = boto3.client('secretsmanager')

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = {
    'audio/mpeg': '.mp3',
    'audio/mp3': '.mp3',
    'audio/wav': '.wav',
    'audio/x-wav': '.wav',
    'audio/mp4': '.m4a',
    'audio/x-m4a': '.m4a',
    'audio/flac': '.flac',
    'audio/ogg': '.ogg',
    'audio/webm': '.webm'
}

# Maximum file size (500MB)
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


def get_google_credentials() -> Dict[str, Any]:
    """Retrieve Google service account credentials from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=GOOGLE_CREDENTIALS_SECRET)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Failed to get Google credentials: {e}")
        raise


def get_drive_service():
    """Create and return a Google Drive API service instance."""
    try:
        creds_dict = get_google_credentials()
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        logger.info("Successfully created Google Drive service")
        return service
    except Exception as e:
        logger.error(f"Failed to create Google Drive service: {e}")
        raise


def is_audio_file(file_metadata: Dict[str, Any]) -> bool:
    """Check if the file is a supported audio format."""
    mime_type = file_metadata.get('mimeType', '')
    file_name = file_metadata.get('name', '').lower()
    
    # Check MIME type
    if mime_type in SUPPORTED_AUDIO_FORMATS:
        return True
    
    # Check file extension as fallback
    audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm']
    return any(file_name.endswith(ext) for ext in audio_extensions)


def generate_call_id() -> str:
    """Generate a unique call ID with timestamp and UUID."""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    short_uuid = str(uuid.uuid4())[:8]
    return f"{timestamp}-{short_uuid}"


def download_file_from_drive(service, file_id: str) -> tuple:
    """
    Download a file from Google Drive.
    
    Returns:
        Tuple of (file_content bytes, file_metadata dict)
    """
    try:
        # Get file metadata
        file_metadata = service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,size,md5Checksum,createdTime,modifiedTime'
        ).execute()
        
        file_size = int(file_metadata.get('size', 0))
        file_name = file_metadata.get('name', 'unknown')
        
        logger.info(f"Downloading file: {file_name} ({file_id}), size: {file_size} bytes")
        
        # Check file size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE_BYTES})")
        
        # Download file content
        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.info(f"Download progress: {int(status.progress() * 100)}%")
        
        file_content = file_buffer.getvalue()
        logger.info(f"Successfully downloaded {len(file_content)} bytes")
        
        return file_content, file_metadata
        
    except HttpError as e:
        logger.error(f"Failed to download file {file_id}: {e}")
        raise


def upload_to_s3(file_content: bytes, call_id: str, file_metadata: Dict[str, Any]) -> str:
    """
    Upload audio file to S3 with organized path.
    
    Returns:
        S3 key of the uploaded file
    """
    date_prefix = datetime.utcnow().strftime('%Y-%m-%d')
    file_name = file_metadata.get('name', 'audio')
    
    # Get file extension
    mime_type = file_metadata.get('mimeType', '')
    extension = SUPPORTED_AUDIO_FORMATS.get(mime_type, '')
    if not extension:
        # Extract from filename
        if '.' in file_name:
            extension = '.' + file_name.rsplit('.', 1)[-1].lower()
        else:
            extension = '.mp3'  # Default
    
    s3_key = f"raw-audio/{date_prefix}/{call_id}{extension}"
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=mime_type or 'audio/mpeg',
            Metadata={
                'call-id': call_id,
                'original-filename': file_name,
                'gdrive-file-id': file_metadata.get('id', ''),
                'upload-timestamp': datetime.utcnow().isoformat()
            },
            ServerSideEncryption='AES256'
        )
        logger.info(f"Uploaded to S3: s3://{S3_BUCKET}/{s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise


def create_dynamodb_record(call_id: str, file_metadata: Dict[str, Any], s3_key: str) -> None:
    """Create initial DynamoDB record for the call."""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    item = {
        'call_id': call_id,
        'timestamp': timestamp,
        'status': 'UPLOADED',
        'file_name': file_metadata.get('name', 'unknown'),
        'gdrive_file_id': file_metadata.get('id', ''),
        's3_audio_url': f"s3://{S3_BUCKET}/{s3_key}",
        's3_bucket': S3_BUCKET,
        's3_key': s3_key,
        'created_at': timestamp,
        'updated_at': timestamp,
        'retry_count': 0
    }
    
    try:
        table.put_item(Item=item)
        logger.info(f"Created DynamoDB record for call_id: {call_id}")
    except ClientError as e:
        logger.error(f"Failed to create DynamoDB record: {e}")
        raise


def trigger_step_function(call_id: str, s3_bucket: str, s3_key: str, file_name: str) -> str:
    """Trigger Step Functions state machine for processing."""
    input_payload = {
        'call_id': call_id,
        's3_bucket': s3_bucket,
        's3_key': s3_key,
        'file_name': file_name
    }
    
    try:
        response = sfn_client.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=f"call-{call_id}",
            input=json.dumps(input_payload)
        )
        execution_arn = response['executionArn']
        logger.info(f"Started Step Function execution: {execution_arn}")
        return execution_arn
    except ClientError as e:
        logger.error(f"Failed to start Step Function: {e}")
        raise


def validate_webhook_token(headers: Dict[str, str]) -> bool:
    """Validate the webhook token from Google."""
    token = headers.get('X-Goog-Channel-Token') or headers.get('x-goog-channel-token')
    if not WEBHOOK_TOKEN:
        logger.warning("WEBHOOK_TOKEN not configured, skipping validation")
        return True
    return token == WEBHOOK_TOKEN


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Google Drive webhooks.
    
    Processes webhook notifications, downloads audio files, uploads to S3,
    creates DynamoDB records, and triggers Step Functions processing.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract headers
    headers = event.get('headers', {})
    
    # Handle sync message (initial webhook setup verification)
    resource_state = headers.get('X-Goog-Resource-State') or headers.get('x-goog-resource-state')
    if resource_state == 'sync':
        logger.info("Received sync message - webhook verified")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Webhook verified'})
        }
    
    # Validate webhook token
    if not validate_webhook_token(headers):
        logger.warning("Invalid webhook token")
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Invalid token'})
        }
    
    # Get file ID from the notification
    # Google sends file ID in the resource URI or in the body
    body = event.get('body', '{}')
    if isinstance(body, str):
        try:
            body = json.loads(body) if body else {}
        except json.JSONDecodeError:
            body = {}
    
    file_id = body.get('file_id') or headers.get('X-Goog-Resource-Id') or headers.get('x-goog-resource-id')
    
    if not file_id:
        logger.warning("No file ID in notification")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No file ID provided'})
        }
    
    try:
        # Initialize Google Drive service
        drive_service = get_drive_service()
        
        # Get file metadata first to check if it's an audio file
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,size,md5Checksum,createdTime,modifiedTime'
        ).execute()
        
        # Check if it's a supported audio file
        if not is_audio_file(file_metadata):
            logger.info(f"Skipping non-audio file: {file_metadata.get('name')} ({file_metadata.get('mimeType')})")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Skipped non-audio file'})
            }
        
        # Generate unique call ID
        call_id = generate_call_id()
        logger.info(f"Processing call: {call_id}")
        
        # Download file from Google Drive
        file_content, file_metadata = download_file_from_drive(drive_service, file_id)
        
        # Upload to S3
        s3_key = upload_to_s3(file_content, call_id, file_metadata)
        
        # Create DynamoDB record
        create_dynamodb_record(call_id, file_metadata, s3_key)
        
        # Trigger Step Functions processing pipeline
        execution_arn = trigger_step_function(
            call_id=call_id,
            s3_bucket=S3_BUCKET,
            s3_key=s3_key,
            file_name=file_metadata.get('name', 'unknown')
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing started',
                'call_id': call_id,
                'execution_arn': execution_arn
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
