"""
AWS Lambda function to start Amazon Transcribe job.
Called by Step Functions after audio upload to S3.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
import uuid

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
TRANSCRIBE_OUTPUT_BUCKET = os.environ.get('TRANSCRIBE_OUTPUT_BUCKET', 'customer-care-call-processor')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')

# AWS clients
transcribe = boto3.client('transcribe')
dynamodb = boto3.resource('dynamodb')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for starting Transcribe jobs.
    
    Expected input from Step Functions:
    {
        "call_id": "...",
        "s3_bucket": "...",
        "s3_key": "raw-audio/2024/01/15/call_123.mp3",
        "caller_id": "...",
        "assigned_user_id": "..."
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    call_id = event['call_id']
    s3_bucket = event['s3_bucket']
    s3_key = event['s3_key']
    
    # Generate unique transcription job name
    job_name = f"call-{call_id}-{uuid.uuid4().hex[:8]}"
    media_uri = f"s3://{s3_bucket}/{s3_key}"
    
    # Determine output key
    date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
    output_key = f"transcripts/{date_prefix}/{call_id}.json"
    
    try:
        # Start transcription job with speaker identification
        response = transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat=get_media_format(s3_key),
            LanguageCode='en-US',
            OutputBucketName=TRANSCRIBE_OUTPUT_BUCKET,
            OutputKey=output_key,
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 2,  # Customer + Agent
                'ShowAlternatives': False
            },
            ContentRedaction={
                'RedactionType': 'PII',
                'RedactionOutput': 'redacted'
            }
        )
        
        logger.info(f"Started transcription job: {job_name}")
        
        # Update DynamoDB with transcription job details
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.update_item(
            Key={'call_id': call_id},
            UpdateExpression='SET transcribe_job_name = :job, transcribe_output_key = :output, #status = :status, updated_at = :updated',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':job': job_name,
                ':output': output_key,
                ':status': 'TRANSCRIBING',
                ':updated': datetime.utcnow().isoformat() + 'Z'
            }
        )
        
        # Return data for next step
        return {
            **event,
            'transcribe_job_name': job_name,
            'transcribe_output_key': output_key,
            'transcribe_output_bucket': TRANSCRIBE_OUTPUT_BUCKET
        }
        
    except ClientError as e:
        logger.error(f"Failed to start transcription job: {e}")
        raise


def get_media_format(s3_key: str) -> str:
    """Determine media format from file extension."""
    extension = s3_key.lower().split('.')[-1]
    format_map = {
        'mp3': 'mp3',
        'mp4': 'mp4',
        'wav': 'wav',
        'flac': 'flac',
        'ogg': 'ogg',
        'webm': 'webm',
        'm4a': 'mp4',
        'amr': 'amr'
    }
    return format_map.get(extension, 'mp3')
