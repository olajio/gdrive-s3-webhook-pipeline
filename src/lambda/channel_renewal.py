"""
AWS Lambda function to automatically renew Google Drive webhook channels.
Scheduled to run every 12 hours via CloudWatch Events.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils import (
    get_google_credentials,
    get_channel_info,
    save_channel_info,
    send_alert,
    MetricsPublisher
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
WEBHOOK_ENDPOINT = os.environ.get('WEBHOOK_ENDPOINT')  # API Gateway URL
FOLDER_ID = os.environ.get('GDRIVE_FOLDER_ID')
CHANNELS_TABLE = os.environ.get('CHANNELS_TABLE', 'gdrive_channels')

# AWS clients
dynamodb = boto3.resource('dynamodb')

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


def stop_channel(service, channel_id: str, resource_id: str) -> bool:
    """
    Stop an existing webhook channel.
    
    Args:
        service: Google Drive API service
        channel_id: Channel ID to stop
        resource_id: Resource ID associated with channel
        
    Returns:
        True if successful, False otherwise
    """
    try:
        service.channels().stop(
            body={
                'id': channel_id,
                'resourceId': resource_id
            }
        ).execute()
        
        logger.info(f"Successfully stopped channel: {channel_id}")
        return True
        
    except HttpError as e:
        # Channel may already be expired or invalid
        if e.resp.status == 404:
            logger.warning(f"Channel not found (may be expired): {channel_id}")
            return True
        else:
            logger.error(f"Failed to stop channel: {e}")
            return False


def create_channel(service, folder_id: str) -> Dict[str, Any]:
    """
    Create a new webhook channel for a Google Drive folder.
    
    Args:
        service: Google Drive API service
        folder_id: Google Drive folder ID to watch
        
    Returns:
        Channel information dictionary
        
    Raises:
        HttpError: If channel creation fails
    """
    try:
        # Generate unique channel ID
        channel_id = str(uuid.uuid4())
        
        # Get webhook token from Secrets Manager
        from utils import get_secret
        secrets = get_secret('gdrive-webhook-config')
        webhook_token = secrets.get('webhook_token')
        
        # Create channel (expires in 24 hours by default, max is 24 hours for Drive)
        channel_body = {
            'id': channel_id,
            'type': 'web_hook',
            'address': WEBHOOK_ENDPOINT,
            'token': webhook_token,
            'expiration': int((datetime.utcnow() + timedelta(hours=23)).timestamp() * 1000)
        }
        
        # Watch the folder
        response = service.files().watch(
            fileId=folder_id,
            body=channel_body,
            supportsAllDrives=True
        ).execute()
        
        logger.info(f"Created new channel: {channel_id}")
        logger.info(f"Channel response: {json.dumps(response)}")
        
        # Get start page token for change tracking
        page_token_response = service.changes().getStartPageToken().execute()
        page_token = page_token_response.get('startPageToken')
        
        channel_info = {
            'channel_id': response['id'],
            'resource_id': response['resourceId'],
            'folder_id': folder_id,
            'expiration': datetime.fromtimestamp(int(response['expiration']) / 1000).isoformat(),
            'page_token': page_token
        }
        
        metrics.publish_metric('ChannelsCreated', 1)
        return channel_info
        
    except HttpError as e:
        logger.error(f"Failed to create channel: {e}")
        metrics.publish_metric('ChannelCreationErrors', 1)
        raise


def get_active_channels() -> list:
    """
    Get all active channels from DynamoDB.
    
    Returns:
        List of channel info dictionaries
    """
    table = dynamodb.Table(CHANNELS_TABLE)
    
    try:
        response = table.scan(
            FilterExpression='#status = :active',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':active': 'active'}
        )
        
        channels = response.get('Items', [])
        logger.info(f"Found {len(channels)} active channels")
        return channels
        
    except ClientError as e:
        logger.error(f"Failed to get active channels: {e}")
        return []


def should_renew_channel(channel_info: Dict[str, Any]) -> bool:
    """
    Check if a channel should be renewed.
    
    Args:
        channel_info: Channel information from DynamoDB
        
    Returns:
        True if renewal needed, False otherwise
    """
    expiration_str = channel_info.get('expiration')
    if not expiration_str:
        logger.warning(f"No expiration for channel: {channel_info.get('channel_id')}")
        return True
    
    try:
        expiration = datetime.fromisoformat(expiration_str)
        now = datetime.utcnow()
        
        # Renew if expiring in less than 2 hours (safety buffer)
        time_until_expiration = expiration - now
        should_renew = time_until_expiration.total_seconds() < (2 * 3600)
        
        if should_renew:
            logger.info(f"Channel expires in {time_until_expiration.total_seconds() / 3600:.1f} hours, renewing")
        else:
            logger.info(f"Channel still valid for {time_until_expiration.total_seconds() / 3600:.1f} hours")
        
        return should_renew
        
    except ValueError as e:
        logger.error(f"Invalid expiration format: {expiration_str}, {e}")
        return True


def renew_channel(service, old_channel: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Renew a webhook channel (stop old, create new).
    
    Args:
        service: Google Drive API service
        old_channel: Old channel information
        
    Returns:
        New channel information or None if failed
    """
    channel_id = old_channel['channel_id']
    resource_id = old_channel['resource_id']
    folder_id = old_channel['folder_id']
    
    try:
        # Stop old channel
        logger.info(f"Stopping old channel: {channel_id}")
        stop_channel(service, channel_id, resource_id)
        
        # Create new channel
        logger.info(f"Creating new channel for folder: {folder_id}")
        new_channel = create_channel(service, folder_id)
        
        # Save to DynamoDB
        save_channel_info(
            channel_id=new_channel['channel_id'],
            resource_id=new_channel['resource_id'],
            folder_id=new_channel['folder_id'],
            expiration=new_channel['expiration'],
            page_token=new_channel.get('page_token')
        )
        
        # Mark old channel as renewed in DynamoDB
        table = dynamodb.Table(CHANNELS_TABLE)
        table.update_item(
            Key={'channel_id': channel_id},
            UpdateExpression='SET #status = :status, renewed_to = :new_id',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'renewed',
                ':new_id': new_channel['channel_id']
            }
        )
        
        logger.info(f"Successfully renewed channel: {channel_id} -> {new_channel['channel_id']}")
        metrics.publish_metric('ChannelsRenewed', 1)
        
        return new_channel
        
    except Exception as e:
        logger.error(f"Failed to renew channel {channel_id}: {e}")
        metrics.publish_metric('ChannelRenewalErrors', 1)
        
        # Send alert
        send_alert(
            "Webhook Channel Renewal Failed",
            f"Failed to renew channel {channel_id} for folder {folder_id}: {str(e)}"
        )
        
        return None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for automatic channel renewal.
    
    Args:
        event: CloudWatch Events scheduled event
        context: Lambda context
        
    Returns:
        Execution summary
    """
    logger.info(f"Starting channel renewal check: {json.dumps(event)}")
    
    try:
        # Create Google Drive service
        service = get_drive_service()
        
        # Get all active channels
        active_channels = get_active_channels()
        
        if not active_channels:
            logger.info("No active channels found")
            
            # If no channels exist, create initial channel
            if FOLDER_ID:
                logger.info(f"Creating initial channel for folder: {FOLDER_ID}")
                channel = create_channel(service, FOLDER_ID)
                save_channel_info(
                    channel_id=channel['channel_id'],
                    resource_id=channel['resource_id'],
                    folder_id=channel['folder_id'],
                    expiration=channel['expiration'],
                    page_token=channel.get('page_token')
                )
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Created initial channel',
                        'channel_id': channel['channel_id']
                    })
                }
            else:
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'No channels to renew'})
                }
        
        # Check and renew channels as needed
        renewed_count = 0
        skipped_count = 0
        failed_count = 0
        
        for channel in active_channels:
            if should_renew_channel(channel):
                new_channel = renew_channel(service, channel)
                if new_channel:
                    renewed_count += 1
                else:
                    failed_count += 1
            else:
                skipped_count += 1
        
        # Summary
        summary = {
            'total_channels': len(active_channels),
            'renewed': renewed_count,
            'skipped': skipped_count,
            'failed': failed_count
        }
        
        logger.info(f"Channel renewal complete: {json.dumps(summary)}")
        
        # Alert if any renewals failed
        if failed_count > 0:
            send_alert(
                "Channel Renewal Failures",
                f"Failed to renew {failed_count} channel(s). Check logs for details."
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Channel renewal complete',
                'summary': summary
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        metrics.publish_metric('LambdaErrors', 1)
        
        send_alert(
            "Channel Renewal Lambda Error",
            f"Unexpected error during channel renewal: {str(e)}"
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
