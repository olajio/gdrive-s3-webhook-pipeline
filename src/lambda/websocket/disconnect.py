"""
AWS Lambda function for WebSocket $disconnect route.
Handles WebSocket disconnections from the React frontend.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from typing import Dict, Any

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
    Lambda handler for WebSocket $disconnect route.
    
    Removes connection information from DynamoDB when client disconnects.
    """
    logger.info(f"Disconnect event: {json.dumps(event)}")
    
    connection_id = event['requestContext']['connectionId']
    
    table = dynamodb.Table(CONNECTIONS_TABLE)
    
    try:
        # Delete connection record
        table.delete_item(
            Key={'connection_id': connection_id}
        )
        
        logger.info(f"Connection removed: {connection_id}")
        
        return {
            'statusCode': 200,
            'body': 'Disconnected'
        }
        
    except ClientError as e:
        logger.error(f"Failed to remove connection: {e}")
        # Return success anyway - connection cleanup will happen via TTL
        return {
            'statusCode': 200,
            'body': 'Disconnected'
        }
