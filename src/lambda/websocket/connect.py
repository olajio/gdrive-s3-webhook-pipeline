"""
AWS Lambda function for WebSocket $connect route.
Handles new WebSocket connections from the React frontend.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from typing import Dict, Any
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE', 'websocket-connections')

# AWS clients
dynamodb = boto3.resource('dynamodb')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for WebSocket $connect route.
    
    Stores connection information in DynamoDB for later message broadcasting.
    Validates JWT token from Cognito authorizer.
    """
    logger.info(f"Connect event: {json.dumps(event)}")
    
    connection_id = event['requestContext']['connectionId']
    
    # Get user info from Cognito authorizer
    authorizer = event.get('requestContext', {}).get('authorizer', {})
    user_id = authorizer.get('principalId') or authorizer.get('sub')
    user_groups = authorizer.get('groups', '').split(',') if authorizer.get('groups') else []
    
    # Get query parameters for subscription preferences
    query_params = event.get('queryStringParameters') or {}
    subscribe_to = query_params.get('subscribe_to', 'all')  # all, own, or specific call_id
    
    table = dynamodb.Table(CONNECTIONS_TABLE)
    
    try:
        # Store connection info
        item = {
            'connection_id': connection_id,
            'user_id': user_id,
            'user_groups': user_groups,
            'subscribe_to': subscribe_to,
            'connected_at': datetime.utcnow().isoformat() + 'Z',
            'ttl': int(datetime.utcnow().timestamp()) + 86400  # 24 hour TTL
        }
        
        table.put_item(Item=item)
        
        logger.info(f"Connection stored: {connection_id} for user {user_id}")
        
        return {
            'statusCode': 200,
            'body': 'Connected'
        }
        
    except ClientError as e:
        logger.error(f"Failed to store connection: {e}")
        return {
            'statusCode': 500,
            'body': 'Failed to connect'
        }
