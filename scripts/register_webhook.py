#!/usr/bin/env python3
"""
Register Google Drive webhook for Customer Care Call Processing System.

This script creates a push notification channel to watch for new files
in a Google Drive folder and send notifications to the webhook endpoint.

Usage:
    python register_webhook.py \
        --folder-id YOUR_FOLDER_ID \
        --webhook-url https://your-api.execute-api.region.amazonaws.com/dev/webhook \
        [--token-file credentials/webhook-token.txt]
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Required packages not installed.")
    print("Run: pip install google-api-python-client google-auth")
    sys.exit(1)


# Scopes required for Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def get_credentials(credentials_file: str = None) -> service_account.Credentials:
    """Get Google service account credentials."""
    if credentials_file and os.path.exists(credentials_file):
        return service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES
        )
    
    # Try common locations
    common_paths = [
        'credentials/service-account-key.json',
        '../credentials/service-account-key.json',
        'service-account-key.json',
        os.path.expanduser('~/.config/google-drive-credentials.json')
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            print(f"Using credentials from: {path}")
            return service_account.Credentials.from_service_account_file(
                path, scopes=SCOPES
            )
    
    # Try environment variable
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        creds_dict = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    
    raise FileNotFoundError(
        "Could not find Google service account credentials. "
        "Specify with --credentials-file or place in credentials/service-account-key.json"
    )


def get_webhook_token(token_file: str = None) -> str:
    """Get webhook verification token."""
    if token_file and os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return f.read().strip()
    
    # Try environment variable
    token = os.environ.get('WEBHOOK_TOKEN')
    if token:
        return token
    
    # Generate new token
    token = uuid.uuid4().hex
    print(f"Generated new webhook token: {token}")
    print("Save this token in AWS Secrets Manager!")
    return token


def verify_folder_access(drive_service, folder_id: str) -> dict:
    """Verify access to the Google Drive folder."""
    try:
        folder = drive_service.files().get(
            fileId=folder_id,
            fields='id, name, mimeType'
        ).execute()
        
        if folder['mimeType'] != 'application/vnd.google-apps.folder':
            raise ValueError(f"ID {folder_id} is not a folder")
        
        return folder
    except HttpError as e:
        if e.resp.status == 404:
            raise ValueError(f"Folder not found: {folder_id}")
        elif e.resp.status == 403:
            raise ValueError(f"Access denied to folder: {folder_id}")
        raise


def create_watch_channel(
    drive_service,
    folder_id: str,
    webhook_url: str,
    token: str
) -> dict:
    """Create a push notification channel for the folder."""
    channel_id = f"channel-{uuid.uuid4().hex[:12]}"
    
    # Channel expires in 7 days (maximum allowed by Google)
    expiration = datetime.utcnow() + timedelta(days=7)
    expiration_ms = int(expiration.timestamp() * 1000)
    
    request_body = {
        'id': channel_id,
        'type': 'web_hook',
        'address': webhook_url,
        'token': token,
        'expiration': str(expiration_ms)
    }
    
    try:
        response = drive_service.files().watch(
            fileId=folder_id,
            body=request_body
        ).execute()
        
        return {
            'channel_id': response['id'],
            'resource_id': response['resourceId'],
            'expiration': datetime.fromtimestamp(int(response['expiration']) / 1000).isoformat(),
            'resource_uri': response.get('resourceUri', '')
        }
    except HttpError as e:
        if e.resp.status == 400:
            raise ValueError(f"Invalid webhook URL or configuration: {e}")
        raise


def save_channel_info(channel_info: dict, output_file: str = None):
    """Save channel information for later use."""
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(channel_info, f, indent=2)
        print(f"Channel info saved to: {output_file}")
    
    # Also print to stdout
    print("\n" + "="*60)
    print("WEBHOOK CHANNEL CREATED SUCCESSFULLY")
    print("="*60)
    print(f"  Channel ID:   {channel_info['channel_id']}")
    print(f"  Resource ID:  {channel_info['resource_id']}")
    print(f"  Expiration:   {channel_info['expiration']}")
    print("="*60)
    print("\nIMPORTANT: Save the Channel ID and Resource ID!")
    print("You'll need them to stop the channel or troubleshoot issues.")
    print("\nThe channel will expire in 7 days. Set up auto-renewal using")
    print("the EventBridge rule created by Terraform.")


def main():
    parser = argparse.ArgumentParser(
        description='Register Google Drive webhook for call processing'
    )
    parser.add_argument(
        '--folder-id', '-f',
        required=True,
        help='Google Drive folder ID to watch'
    )
    parser.add_argument(
        '--webhook-url', '-w',
        required=True,
        help='Webhook endpoint URL'
    )
    parser.add_argument(
        '--credentials-file', '-c',
        default=None,
        help='Path to Google service account JSON file'
    )
    parser.add_argument(
        '--token-file', '-t',
        default=None,
        help='Path to file containing webhook verification token'
    )
    parser.add_argument(
        '--output', '-o',
        default='channel-info.json',
        help='Output file for channel information'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("Google Drive Webhook Registration")
    print("="*60)
    print(f"Folder ID:   {args.folder_id}")
    print(f"Webhook URL: {args.webhook_url}")
    print("")
    
    try:
        # Get credentials
        print("Loading credentials...")
        credentials = get_credentials(args.credentials_file)
        print("✓ Credentials loaded")
        
        # Get webhook token
        print("Loading webhook token...")
        token = get_webhook_token(args.token_file)
        print("✓ Token loaded")
        
        # Build Drive service
        print("Connecting to Google Drive API...")
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✓ Connected")
        
        # Verify folder access
        print(f"Verifying access to folder {args.folder_id}...")
        folder = verify_folder_access(drive_service, args.folder_id)
        print(f"✓ Folder accessible: {folder['name']}")
        
        # Create watch channel
        print("Creating webhook channel...")
        channel_info = create_watch_channel(
            drive_service,
            args.folder_id,
            args.webhook_url,
            token
        )
        
        # Save and display results
        save_channel_info(channel_info, args.output)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        return 1
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return 1
    except HttpError as e:
        print(f"\n❌ Google API Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
