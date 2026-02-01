"""
AWS Lambda function to update processing status in DynamoDB.
Called by Step Functions to update status at each stage.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')

# AWS clients
dynamodb = boto3.resource('dynamodb')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for updating processing status.
    
    Expected input from Step Functions:
    {
        "call_id": "...",
        "status": "TRANSCRIBING|SUMMARIZING|FAILED",
        "error_message": "..." (optional, for FAILED status)
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    call_id = event['call_id']
    status = event['status']
    error_message = event.get('error_message')
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    try:
        update_expression = 'SET #status = :status, updated_at = :updated'
        expression_names = {'#status': 'status'}
        expression_values = {
            ':status': status,
            ':updated': timestamp
        }
        
        # Add error message if present
        if error_message:
            update_expression += ', error_message = :error'
            expression_values[':error'] = error_message
        
        # Increment retry count if failed
        if status == 'FAILED':
            update_expression += ', retry_count = if_not_exists(retry_count, :zero) + :inc'
            expression_values[':zero'] = 0
            expression_values[':inc'] = 1
        
        table.update_item(
            Key={'call_id': call_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values
        )
        
        logger.info(f"Updated status for {call_id} to {status}")
        
        # Pass through all input data for the next step
        return event
        
    except ClientError as e:
        logger.error(f"Failed to update status: {e}")
        raise
