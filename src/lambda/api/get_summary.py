"""
AWS Lambda function for GET /summaries/{call_id} endpoint.
Returns detailed call summary with transcript and metadata.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from typing import Dict, Any
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')
S3_BUCKET = os.environ.get('S3_BUCKET', 'customer-care-call-processor')

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for getting call summary details.
    
    Path Parameters:
    - call_id: The unique call identifier
    
    Query Parameters:
    - include_transcript: Include full transcript (default false)
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Get path parameter
    path_params = event.get('pathParameters') or {}
    call_id = path_params.get('call_id')
    
    if not call_id:
        return build_response(400, {'error': 'call_id is required'})
    
    # Get query parameters
    query_params = event.get('queryStringParameters') or {}
    include_transcript = query_params.get('include_transcript', 'false').lower() == 'true'
    
    # Get requesting user from JWT claims
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    requesting_user = claims.get('sub')
    user_groups = claims.get('cognito:groups', '').split(',')
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        # Get call record from DynamoDB
        response = table.get_item(Key={'call_id': call_id})
        
        if 'Item' not in response:
            return build_response(404, {'error': 'Call not found'})
        
        item = response['Item']
        
        # Check permissions
        if 'admin' not in user_groups and 'supervisors' not in user_groups:
            if item.get('assigned_user_id') != requesting_user:
                return build_response(403, {'error': 'Access denied'})
        
        # Build response object
        result = {
            'call_id': item['call_id'],
            'caller_id': item.get('caller_id'),
            'assigned_user_id': item.get('assigned_user_id'),
            'status': item.get('status'),
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at'),
            'duration_seconds': item.get('duration_seconds'),
            'summary': item.get('summary'),
            'key_points': item.get('key_points', []),
            'action_items': item.get('action_items', []),
            'sentiment': item.get('sentiment'),
            'urgency': item.get('urgency'),
            'categories': item.get('categories', [])
        }
        
        # Optionally include transcript
        if include_transcript and item.get('transcript_s3_key'):
            transcript = get_transcript_from_s3(item['transcript_s3_key'])
            if transcript:
                result['transcript'] = transcript
        
        # Add presigned URLs for audio access
        if item.get('s3_key'):
            result['audio_url'] = generate_presigned_url(item['s3_key'])
        
        return build_response(200, result)
        
    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        return build_response(500, {'error': 'Internal server error'})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return build_response(500, {'error': 'Internal server error'})


def get_transcript_from_s3(s3_key: str) -> str:
    """Retrieve formatted transcript from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        return response['Body'].read().decode('utf-8')
    except ClientError as e:
        logger.error(f"Failed to get transcript from S3: {e}")
        return None


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Generate presigned URL for audio file access."""
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None


def build_response(status_code: int, body: Dict) -> Dict:
    """Build API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }
