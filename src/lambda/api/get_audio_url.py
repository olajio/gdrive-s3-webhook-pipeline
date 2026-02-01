"""
AWS Lambda function for GET /summaries/{call_id}/audio endpoint.
Returns presigned URL for audio file access.

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
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')
S3_BUCKET = os.environ.get('S3_BUCKET', 'customer-care-call-processor')
URL_EXPIRATION = int(os.environ.get('URL_EXPIRATION', '3600'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for getting audio presigned URL.
    
    Path Parameters:
    - call_id: The unique call identifier
    
    Query Parameters:
    - expiration: URL expiration in seconds (default 3600, max 86400)
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Get path parameter
    path_params = event.get('pathParameters') or {}
    call_id = path_params.get('call_id')
    
    if not call_id:
        return build_response(400, {'error': 'call_id is required'})
    
    # Get query parameters
    query_params = event.get('queryStringParameters') or {}
    expiration = min(int(query_params.get('expiration', URL_EXPIRATION)), 86400)
    
    # Get requesting user from JWT claims
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    requesting_user = claims.get('sub')
    user_groups = claims.get('cognito:groups', '').split(',')
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        # Get call record from DynamoDB
        response = table.get_item(
            Key={'call_id': call_id},
            ProjectionExpression='call_id, s3_key, assigned_user_id'
        )
        
        if 'Item' not in response:
            return build_response(404, {'error': 'Call not found'})
        
        item = response['Item']
        
        # Check permissions
        if 'admin' not in user_groups and 'supervisors' not in user_groups:
            if item.get('assigned_user_id') != requesting_user:
                return build_response(403, {'error': 'Access denied'})
        
        # Check if audio file exists
        if not item.get('s3_key'):
            return build_response(404, {'error': 'Audio file not found'})
        
        # Generate presigned URL
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': item['s3_key']
            },
            ExpiresIn=expiration
        )
        
        return build_response(200, {
            'call_id': call_id,
            'audio_url': url,
            'expires_in': expiration
        })
        
    except ClientError as e:
        logger.error(f"Error: {e}")
        return build_response(500, {'error': 'Internal server error'})


def build_response(status_code: int, body: Dict) -> Dict:
    """Build API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        },
        'body': json.dumps(body)
    }
