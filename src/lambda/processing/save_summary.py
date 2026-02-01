"""
AWS Lambda function to save the final summary to DynamoDB.
Updates the call record with all processed data and marks as COMPLETED.

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
S3_BUCKET = os.environ.get('S3_BUCKET', 'customer-care-audio-dev')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')

# AWS clients
dynamodb = boto3.resource('dynamodb')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for saving the final summary to DynamoDB.
    
    Expected input from Step Functions:
    {
        "call_id": "...",
        "s3_bucket": "...",
        "summary_key": "...",
        "summary": {
            "issue_sentence": "...",
            "key_details": [...],
            "action_items": [...],
            "next_steps": [...],
            "sentiment": "...",
            ...
        }
    }
    """
    logger.info(f"Received event: {json.dumps(event)[:1000]}...")
    
    call_id = event['call_id']
    s3_bucket = event.get('s3_bucket', S3_BUCKET)
    summary_key = event['summary_key']
    summary = event['summary']
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    try:
        # Build update expression dynamically
        update_parts = [
            'status = :status',
            's3_summary_url = :summary_url',
            'issue_sentence = :issue',
            'key_details = :details',
            'action_items = :actions',
            'next_steps = :steps',
            'sentiment = :sentiment',
            'processed_timestamp = :processed',
            'updated_at = :updated'
        ]
        
        expression_values = {
            ':status': 'COMPLETED',
            ':summary_url': f"s3://{s3_bucket}/{summary_key}",
            ':issue': summary.get('issue_sentence', ''),
            ':details': summary.get('key_details', []),
            ':actions': summary.get('action_items', []),
            ':steps': summary.get('next_steps', []),
            ':sentiment': summary.get('sentiment', 'Neutral'),
            ':processed': timestamp,
            ':updated': timestamp
        }
        
        # Add optional fields if present
        if summary.get('call_date'):
            update_parts.append('call_date = :call_date')
            expression_values[':call_date'] = summary['call_date']
        
        if summary.get('agent_id'):
            update_parts.append('agent_id = :agent_id')
            expression_values[':agent_id'] = summary['agent_id']
        
        if summary.get('customer_id'):
            update_parts.append('customer_id = :customer_id')
            expression_values[':customer_id'] = summary['customer_id']
        
        if summary.get('duration_seconds'):
            update_parts.append('duration_seconds = :duration')
            expression_values[':duration'] = summary['duration_seconds']
        
        update_expression = 'SET ' + ', '.join(update_parts)
        
        # Update DynamoDB
        response = table.update_item(
            Key={'call_id': call_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_item = response.get('Attributes', {})
        logger.info(f"Updated DynamoDB record for {call_id} with status COMPLETED")
        
        # Return the complete record for the notification step
        return {
            'call_id': call_id,
            'status': 'COMPLETED',
            'summary': {
                'call_id': call_id,
                'issue_sentence': summary.get('issue_sentence', ''),
                'sentiment': summary.get('sentiment', 'Neutral'),
                'call_date': summary.get('call_date', ''),
                'duration_seconds': summary.get('duration_seconds', 0),
                'processed_timestamp': timestamp
            }
        }
        
    except ClientError as e:
        logger.error(f"Failed to update DynamoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving summary: {e}", exc_info=True)
        raise
