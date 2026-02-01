"""
AWS Lambda function for GET /summaries/{call_id}/transcript endpoint.
Returns the formatted transcript for a call.

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

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for getting call transcript.
    
    Path Parameters:
    - call_id: The unique call identifier
    
    Query Parameters:
    - format: Output format (text, json) - default text
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Get path parameter
    path_params = event.get('pathParameters') or {}
    call_id = path_params.get('call_id')
    
    if not call_id:
        return build_response(400, {'error': 'call_id is required'})
    
    # Get query parameters
    query_params = event.get('queryStringParameters') or {}
    output_format = query_params.get('format', 'text').lower()
    
    if output_format not in ('text', 'json'):
        return build_response(400, {'error': 'format must be text or json'})
    
    # Get requesting user from JWT claims
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    requesting_user = claims.get('sub')
    user_groups = claims.get('cognito:groups', '').split(',')
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        # Get call record from DynamoDB
        response = table.get_item(
            Key={'call_id': call_id},
            ProjectionExpression='call_id, transcript_s3_key, assigned_user_id, #status',
            ExpressionAttributeNames={'#status': 'status'}
        )
        
        if 'Item' not in response:
            return build_response(404, {'error': 'Call not found'})
        
        item = response['Item']
        
        # Check permissions
        if 'admin' not in user_groups and 'supervisors' not in user_groups:
            if item.get('assigned_user_id') != requesting_user:
                return build_response(403, {'error': 'Access denied'})
        
        # Check if transcript exists
        if not item.get('transcript_s3_key'):
            if item.get('status') in ('PENDING', 'TRANSCRIBING'):
                return build_response(202, {
                    'message': 'Transcript is being generated',
                    'status': item.get('status')
                })
            return build_response(404, {'error': 'Transcript not found'})
        
        # Get transcript from S3
        s3_response = s3.get_object(
            Bucket=S3_BUCKET,
            Key=item['transcript_s3_key']
        )
        transcript_content = s3_response['Body'].read().decode('utf-8')
        
        if output_format == 'json':
            # Parse and return as structured JSON
            try:
                transcript_data = json.loads(transcript_content)
                return build_response(200, {
                    'call_id': call_id,
                    'transcript': transcript_data
                })
            except json.JSONDecodeError:
                # Return as text if not valid JSON
                return build_response(200, {
                    'call_id': call_id,
                    'transcript': transcript_content
                })
        else:
            # Return as plain text
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/plain',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True
                },
                'body': transcript_content
            }
        
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
