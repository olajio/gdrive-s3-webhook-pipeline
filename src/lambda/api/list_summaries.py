"""
AWS Lambda function for GET /summaries endpoint.
Returns paginated list of call summaries with filtering.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from typing import Dict, Any, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# AWS clients
dynamodb = boto3.resource('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for listing call summaries.
    
    Query Parameters:
    - status: Filter by status (PENDING, TRANSCRIBING, SUMMARIZING, COMPLETED, FAILED)
    - assigned_user_id: Filter by assigned caseworker
    - date_from: Filter by date range start (YYYY-MM-DD)
    - date_to: Filter by date range end (YYYY-MM-DD)
    - limit: Number of items per page (default 20, max 100)
    - next_token: Pagination token for next page
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Get query parameters
    params = event.get('queryStringParameters') or {}
    
    status = params.get('status')
    assigned_user_id = params.get('assigned_user_id')
    date_from = params.get('date_from')
    date_to = params.get('date_to')
    limit = min(int(params.get('limit', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
    next_token = params.get('next_token')
    
    # Get requesting user from JWT claims
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    requesting_user = claims.get('sub')
    user_groups = claims.get('cognito:groups', '').split(',')
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        # Build query or scan based on filters
        if status:
            # Use GSI for status queries
            response = query_by_status(table, status, limit, next_token)
        elif assigned_user_id:
            # Use GSI for user queries
            response = query_by_user(table, assigned_user_id, limit, next_token)
        else:
            # Scan for all items (with optional date filtering)
            response = scan_all(table, date_from, date_to, limit, next_token)
        
        # Filter results based on user permissions
        items = response.get('Items', [])
        if 'admin' not in user_groups and 'supervisors' not in user_groups:
            # Caseworkers can only see their assigned calls
            items = [item for item in items if item.get('assigned_user_id') == requesting_user]
        
        # Build pagination token
        pagination_token = None
        if 'LastEvaluatedKey' in response:
            pagination_token = json.dumps(response['LastEvaluatedKey'])
        
        return build_response(200, {
            'items': items,
            'count': len(items),
            'next_token': pagination_token
        })
        
    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        return build_response(500, {'error': 'Internal server error'})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return build_response(500, {'error': 'Internal server error'})


def query_by_status(table, status: str, limit: int, next_token: Optional[str]) -> Dict:
    """Query using status-index GSI."""
    kwargs = {
        'IndexName': 'status-index',
        'KeyConditionExpression': Key('status').eq(status),
        'Limit': limit,
        'ScanIndexForward': False  # Most recent first
    }
    
    if next_token:
        kwargs['ExclusiveStartKey'] = json.loads(next_token)
    
    return table.query(**kwargs)


def query_by_user(table, user_id: str, limit: int, next_token: Optional[str]) -> Dict:
    """Query using user-index GSI."""
    kwargs = {
        'IndexName': 'user-index',
        'KeyConditionExpression': Key('assigned_user_id').eq(user_id),
        'Limit': limit,
        'ScanIndexForward': False
    }
    
    if next_token:
        kwargs['ExclusiveStartKey'] = json.loads(next_token)
    
    return table.query(**kwargs)


def scan_all(table, date_from: Optional[str], date_to: Optional[str], 
             limit: int, next_token: Optional[str]) -> Dict:
    """Scan table with optional date filtering."""
    kwargs = {
        'Limit': limit
    }
    
    if next_token:
        kwargs['ExclusiveStartKey'] = json.loads(next_token)
    
    # Build filter expression for date range
    filter_parts = []
    expression_values = {}
    
    if date_from:
        filter_parts.append('created_at >= :date_from')
        expression_values[':date_from'] = date_from
    
    if date_to:
        filter_parts.append('created_at <= :date_to')
        expression_values[':date_to'] = date_to + 'T23:59:59Z'
    
    if filter_parts:
        kwargs['FilterExpression'] = ' AND '.join(filter_parts)
        kwargs['ExpressionAttributeValues'] = expression_values
    
    return table.scan(**kwargs)


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
