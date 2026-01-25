"""
AWS Lambda function to handle Google Drive webhook notifications.
Triggered when files are added/modified in the watched folder.
"""
import json
import logging
import os
import io
from typing import Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import boto3
from botocore.exceptions import ClientError

from utils import (
    validate_webhook_signature,
    get_google_credentials,
    should_sync_file,
    is_duplicate_file,
    log_sync_event,
    send_alert,
    get_channel_info,
    update_page_token,
    calculate_md5,
    MetricsPublisher
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET')
S3_PREFIX = os.environ.get('S3_PREFIX', 'gdrive/')
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', '').split(',') if os.environ.get('ALLOWED_EXTENSIONS') else None

# AWS clients
s3_client = boto3.client('s3')

# CloudWatch metrics
metrics = MetricsPublisher()


def get_drive_service():
    """
    Create and return a Google Drive API service instance.
    
    Returns:
        Google Drive API service object
    """
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


def download_file_from_drive(service, file_id: str) -> tuple[bytes, Dict[str, Any]]:
    """
    Download a file from Google Drive.
    
    Args:
        service: Google Drive API service
        file_id: Google Drive file ID
        
    Returns:
        Tuple of (file_content, file_metadata)
        
    Raises:
        HttpError: If download fails
    """
    try:
        # Get file metadata
        file_metadata = service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,size,md5Checksum,createdTime,modifiedTime,parents'
        ).execute()
        
        logger.info(f"Downloading file: {file_metadata.get('name')} ({file_id})")
        
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


def upload_to_s3(file_content: bytes, file_metadata: Dict[str, Any]) -> str:
    """
    Upload file to S3.
    
    Args:
        file_content: File content bytes
        file_metadata: Google Drive file metadata
        
    Returns:
        S3 object key
        
    Raises:
        ClientError: If upload fails
    """
    file_id = file_metadata['id']
    file_name = file_metadata['name']
    s3_key = f"{S3_PREFIX}{file_id}/{file_name}"
    
    try:
        # Prepare metadata
        s3_metadata = {
            'gdrive-file-id': file_id,
            'gdrive-file-name': file_name,
            'gdrive-mime-type': file_metadata.get('mimeType', ''),
            'gdrive-created-time': file_metadata.get('createdTime', ''),
            'gdrive-modified-time': file_metadata.get('modifiedTime', '')
        }
        
        # Add MD5 checksum if available
        if 'md5Checksum' in file_metadata:
            s3_metadata['gdrive-md5-checksum'] = file_metadata['md5Checksum']
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            Metadata=s3_metadata,
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Successfully uploaded to S3: {s3_key}")
        metrics.publish_metric('FilesUploaded', 1)
        metrics.publish_metric('BytesUploaded', len(file_content), 'Bytes')
        
        return s3_key
        
    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e}")
        metrics.publish_metric('S3UploadErrors', 1)
        raise


def process_file_change(service, file_id: str) -> Dict[str, Any]:
    """
    Process a single file change notification.
    
    Args:
        service: Google Drive API service
        file_id: Google Drive file ID
        
    Returns:
        Processing result dictionary
    """
    result = {
        'file_id': file_id,
        'status': 'unknown',
        'message': ''
    }
    
    try:
        # Download file and get metadata
        file_content, file_metadata = download_file_from_drive(service, file_id)
        file_name = file_metadata['name']
        
        # Check if file should be synced
        if not should_sync_file(file_metadata, ALLOWED_EXTENSIONS):
            result['status'] = 'skipped'
            result['message'] = f"File filtered out: {file_name}"
            log_sync_event(file_id, file_name, 'skipped')
            metrics.publish_metric('FilesSkipped', 1)
            return result
        
        # Check for duplicates
        md5_checksum = file_metadata.get('md5Checksum')
        if md5_checksum and is_duplicate_file(file_id, md5_checksum):
            result['status'] = 'skipped'
            result['message'] = f"Duplicate file (same content): {file_name}"
            log_sync_event(file_id, file_name, 'skipped', md5_checksum=md5_checksum)
            metrics.publish_metric('DuplicateFilesSkipped', 1)
            return result
        
        # Upload to S3
        s3_key = upload_to_s3(file_content, file_metadata)
        
        # Log success
        result['status'] = 'success'
        result['message'] = f"Successfully synced: {file_name}"
        result['s3_key'] = s3_key
        
        log_sync_event(
            file_id=file_id,
            file_name=file_name,
            status='success',
            s3_key=s3_key,
            file_size=len(file_content),
            md5_checksum=md5_checksum
        )
        
        logger.info(f"Successfully processed file: {file_name}")
        return result
        
    except HttpError as e:
        error_msg = f"Google Drive API error: {str(e)}"
        logger.error(error_msg)
        result['status'] = 'failure'
        result['message'] = error_msg
        
        log_sync_event(file_id, 'unknown', 'failure', error_message=error_msg)
        metrics.publish_metric('GoogleDriveErrors', 1)
        
        # Send alert for quota errors
        if e.resp.status == 403:
            send_alert(
                "Google Drive API Quota Exceeded",
                f"File {file_id} failed due to quota limits"
            )
        
        return result
        
    except ClientError as e:
        error_msg = f"AWS error: {str(e)}"
        logger.error(error_msg)
        result['status'] = 'failure'
        result['message'] = error_msg
        
        log_sync_event(file_id, 'unknown', 'failure', error_message=error_msg)
        metrics.publish_metric('AWSErrors', 1)
        
        return result
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        result['status'] = 'failure'
        result['message'] = error_msg
        
        log_sync_event(file_id, 'unknown', 'failure', error_message=error_msg)
        metrics.publish_metric('UnexpectedErrors', 1)
        
        return result


def get_changed_files(service, channel_id: str) -> list:
    """
    Get list of changed files since last sync.
    
    Args:
        service: Google Drive API service
        channel_id: Webhook channel ID
        
    Returns:
        List of changed file IDs
    """
    channel_info = get_channel_info(channel_id)
    if not channel_info:
        logger.warning(f"Channel info not found: {channel_id}")
        return []
    
    folder_id = channel_info.get('folder_id')
    page_token = channel_info.get('page_token')
    
    try:
        # Get changes since last page token
        if page_token:
            results = service.changes().list(
                pageToken=page_token,
                spaces='drive',
                fields='newStartPageToken,changes(fileId,file(id,name,mimeType,trashed,parents))'
            ).execute()
        else:
            # First time - get all files in folder
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id,name,mimeType)'
            ).execute()
            
            files = results.get('files', [])
            file_ids = [f['id'] for f in files]
            
            # Get start page token for future changes
            response = service.changes().getStartPageToken().execute()
            new_page_token = response.get('startPageToken')
            update_page_token(channel_id, new_page_token)
            
            return file_ids
        
        # Process changes
        changes = results.get('changes', [])
        file_ids = []
        
        for change in changes:
            file_info = change.get('file', {})
            
            # Skip if trashed or not in watched folder
            if file_info.get('trashed'):
                continue
            
            parents = file_info.get('parents', [])
            if folder_id not in parents:
                continue
            
            file_ids.append(change['fileId'])
        
        # Update page token
        new_page_token = results.get('newStartPageToken')
        if new_page_token:
            update_page_token(channel_id, new_page_token)
        
        logger.info(f"Found {len(file_ids)} changed files")
        return file_ids
        
    except HttpError as e:
        logger.error(f"Failed to get changed files: {e}")
        return []


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Google Drive webhook notifications.
    
    Args:
        event: API Gateway proxy event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract headers
        headers = event.get('headers', {})
        
        # Get webhook token from Secrets Manager
        from utils import get_secret
        secrets = get_secret('gdrive-webhook-config')
        webhook_token = secrets.get('webhook_token')
        
        # Validate webhook signature
        if not validate_webhook_signature(headers, webhook_token):
            logger.error("Invalid webhook signature")
            metrics.publish_metric('InvalidWebhooks', 1)
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Extract channel info from headers
        channel_id = headers.get('X-Goog-Channel-Id')
        resource_state = headers.get('X-Goog-Resource-State')
        
        logger.info(f"Channel: {channel_id}, State: {resource_state}")
        
        # Handle sync message (initial verification)
        if resource_state == 'sync':
            logger.info("Received sync notification (webhook verification)")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Webhook verified'})
            }
        
        # Handle change notifications
        if resource_state in ['add', 'update', 'change']:
            metrics.publish_metric('WebhooksReceived', 1)
            
            # Create Google Drive service
            service = get_drive_service()
            
            # Get changed files
            file_ids = get_changed_files(service, channel_id)
            
            if not file_ids:
                logger.info("No files to process")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'No changes to process'})
                }
            
            # Process each file
            results = []
            for file_id in file_ids:
                result = process_file_change(service, file_id)
                results.append(result)
            
            # Summary
            success_count = sum(1 for r in results if r['status'] == 'success')
            failure_count = sum(1 for r in results if r['status'] == 'failure')
            skipped_count = sum(1 for r in results if r['status'] == 'skipped')
            
            logger.info(f"Processing complete: {success_count} success, {failure_count} failures, {skipped_count} skipped")
            
            # Send alert if high failure rate
            if failure_count > 0 and (failure_count / len(results)) > 0.2:
                send_alert(
                    "High Webhook Processing Failure Rate",
                    f"Failed to process {failure_count}/{len(results)} files"
                )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Processing complete',
                    'total': len(results),
                    'success': success_count,
                    'failures': failure_count,
                    'skipped': skipped_count,
                    'results': results
                })
            }
        
        # Unknown resource state
        logger.warning(f"Unknown resource state: {resource_state}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Unknown resource state'})
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        metrics.publish_metric('LambdaErrors', 1)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
