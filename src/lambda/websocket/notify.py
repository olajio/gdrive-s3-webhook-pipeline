"""
AWS Lambda function for broadcasting WebSocket notifications.
Called by Step Functions when processing status changes.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from typing import Dict, Any, List

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')
WEBSOCKET_ENDPOINT = os.environ.get('WEBSOCKET_ENDPOINT')

# AWS clients
dynamodb = boto3.resource('dynamodb')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for broadcasting notifications via WebSocket.
    
    Expected input:
    {
        "call_id": "...",
        "status": "TRANSCRIBING|SUMMARIZING|COMPLETED|FAILED",
        "assigned_user_id": "...",
        "message_type": "status_update|new_call|processing_complete",
        "data": { ... optional additional data ... }
    }
    """
    logger.info(f"Notify event: {json.dumps(event)}")
    
    call_id = event['call_id']
    status = event.get('status')
    assigned_user_id = event.get('assigned_user_id')
    message_type = event.get('message_type', 'status_update')
    additional_data = event.get('data', {})
    
    # Build notification message
    message = {
        'type': message_type,
        'call_id': call_id,
        'status': status,
        'timestamp': event.get('timestamp'),
        **additional_data
    }
    
    # Get all active connections
    connections = get_connections()
    
    # Filter connections based on subscription preferences and permissions
    target_connections = filter_connections(
        connections, 
        call_id, 
        assigned_user_id
    )
    
    # Send notifications
    failed_connections = send_notifications(target_connections, message)
    
    # Clean up stale connections
    if failed_connections:
        cleanup_connections(failed_connections)
    
    logger.info(f"Sent {len(target_connections) - len(failed_connections)} notifications")
    
    # Pass through event data for Step Functions
    return event


def get_connections() -> List[Dict]:
    """Get all active WebSocket connections."""
    table = dynamodb.Table(CONNECTIONS_TABLE)
    
    try:
        response = table.scan()
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Failed to get connections: {e}")
        return []


def filter_connections(connections: List[Dict], call_id: str, 
                       assigned_user_id: str) -> List[Dict]:
    """Filter connections based on subscription and permissions."""
    filtered = []
    
    for conn in connections:
        subscribe_to = conn.get('subscribe_to', 'all')
        user_id = conn.get('user_id')
        user_groups = conn.get('user_groups', [])
        
        # Admins and supervisors see all notifications
        if 'admin' in user_groups or 'supervisors' in user_groups:
            filtered.append(conn)
            continue
        
        # Check subscription preference
        if subscribe_to == 'all':
            # Caseworkers only see their own calls
            if user_id == assigned_user_id:
                filtered.append(conn)
        elif subscribe_to == 'own':
            if user_id == assigned_user_id:
                filtered.append(conn)
        elif subscribe_to == call_id:
            # Subscribed to specific call
            filtered.append(conn)
    
    return filtered


def send_notifications(connections: List[Dict], message: Dict) -> List[str]:
    """Send notification to all target connections. Returns failed connection IDs."""
    if not WEBSOCKET_ENDPOINT:
        logger.warning("WEBSOCKET_ENDPOINT not configured")
        return []
    
    # Create API Gateway Management API client
    apigw = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=WEBSOCKET_ENDPOINT
    )
    
    failed = []
    message_bytes = json.dumps(message).encode('utf-8')
    
    for conn in connections:
        connection_id = conn['connection_id']
        
        try:
            apigw.post_to_connection(
                ConnectionId=connection_id,
                Data=message_bytes
            )
        except apigw.exceptions.GoneException:
            logger.info(f"Connection gone: {connection_id}")
            failed.append(connection_id)
        except ClientError as e:
            logger.error(f"Failed to send to {connection_id}: {e}")
            if e.response['Error']['Code'] == 'GoneException':
                failed.append(connection_id)
    
    return failed


def cleanup_connections(connection_ids: List[str]) -> None:
    """Remove stale connections from DynamoDB."""
    table = dynamodb.Table(CONNECTIONS_TABLE)
    
    for connection_id in connection_ids:
        try:
            table.delete_item(Key={'connection_id': connection_id})
            logger.info(f"Cleaned up connection: {connection_id}")
        except ClientError as e:
            logger.error(f"Failed to cleanup {connection_id}: {e}")
