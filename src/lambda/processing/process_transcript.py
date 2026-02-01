"""
AWS Lambda function to process transcripts from Amazon Transcribe.
Parses the raw output and formats it for Bedrock summarization.

Part of the Customer Care Call Processing System.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET', 'customer-care-audio-dev')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'call-summaries')

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')


def get_transcribe_output(s3_bucket: str, transcribe_output_key: str) -> Dict[str, Any]:
    """Retrieve and parse Transcribe output from S3."""
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=transcribe_output_key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except ClientError as e:
        logger.error(f"Failed to get Transcribe output: {e}")
        raise


def format_transcript(transcribe_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the Transcribe output into a readable conversation format.
    
    Returns:
        Dict containing formatted transcript and metadata
    """
    results = transcribe_output.get('results', {})
    
    # Get the full transcript
    transcripts = results.get('transcripts', [])
    full_transcript = transcripts[0].get('transcript', '') if transcripts else ''
    
    # Process speaker-labeled segments if available
    speaker_labels = results.get('speaker_labels', {})
    segments = speaker_labels.get('segments', [])
    items = results.get('items', [])
    
    # Map speakers (typically spk_0 = Agent, spk_1 = Customer)
    speaker_map = {
        'spk_0': 'Agent',
        'spk_1': 'Customer'
    }
    
    formatted_segments = []
    current_speaker = None
    current_text = []
    current_start = None
    
    if segments:
        # Process with speaker labels
        for segment in segments:
            speaker = segment.get('speaker_label', 'Unknown')
            speaker_name = speaker_map.get(speaker, speaker)
            start_time = float(segment.get('start_time', 0))
            end_time = float(segment.get('end_time', 0))
            
            # Get items for this segment
            segment_items = segment.get('items', [])
            segment_text = []
            
            for item in segment_items:
                # Find matching item in the main items list
                start = item.get('start_time')
                end = item.get('end_time')
                
                for main_item in items:
                    if main_item.get('start_time') == start and main_item.get('end_time') == end:
                        alternatives = main_item.get('alternatives', [])
                        if alternatives:
                            content = alternatives[0].get('content', '')
                            # Handle punctuation
                            if main_item.get('type') == 'punctuation':
                                if segment_text:
                                    segment_text[-1] += content
                            else:
                                segment_text.append(content)
                        break
            
            if segment_text:
                formatted_segments.append({
                    'speaker': speaker_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': ' '.join(segment_text)
                })
    else:
        # No speaker labels - use full transcript
        formatted_segments.append({
            'speaker': 'Unknown',
            'start_time': 0,
            'end_time': 0,
            'text': full_transcript
        })
    
    # Calculate metadata
    total_duration = 0
    agent_talk_time = 0
    customer_talk_time = 0
    word_count = len(full_transcript.split())
    
    for segment in formatted_segments:
        duration = segment['end_time'] - segment['start_time']
        total_duration = max(total_duration, segment['end_time'])
        
        if segment['speaker'] == 'Agent':
            agent_talk_time += duration
        elif segment['speaker'] == 'Customer':
            customer_talk_time += duration
    
    # Create readable conversation format
    conversation_lines = []
    for segment in formatted_segments:
        timestamp = f"[{int(segment['start_time'] // 60)}:{int(segment['start_time'] % 60):02d}]"
        conversation_lines.append(f"{timestamp} {segment['speaker']}: {segment['text']}")
    
    formatted_conversation = '\n\n'.join(conversation_lines)
    
    return {
        'formatted_transcript': formatted_conversation,
        'segments': formatted_segments,
        'metadata': {
            'total_duration_seconds': int(total_duration),
            'word_count': word_count,
            'agent_talk_time_seconds': int(agent_talk_time),
            'customer_talk_time_seconds': int(customer_talk_time),
            'segment_count': len(formatted_segments)
        }
    }


def save_formatted_transcript(
    call_id: str,
    formatted_data: Dict[str, Any]
) -> str:
    """Save formatted transcript to S3."""
    date_prefix = datetime.utcnow().strftime('%Y-%m-%d')
    s3_key = f"transcripts/{date_prefix}/{call_id}-transcript.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(formatted_data, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Saved formatted transcript to s3://{S3_BUCKET}/{s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"Failed to save transcript: {e}")
        raise


def update_dynamodb_status(call_id: str, transcript_key: str, duration: int) -> None:
    """Update DynamoDB record with transcript information."""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        table.update_item(
            Key={'call_id': call_id},
            UpdateExpression='SET s3_transcript_url = :url, duration_seconds = :dur, updated_at = :ts',
            ExpressionAttributeValues={
                ':url': f"s3://{S3_BUCKET}/{transcript_key}",
                ':dur': duration,
                ':ts': datetime.utcnow().isoformat() + 'Z'
            }
        )
        logger.info(f"Updated DynamoDB record for {call_id}")
    except ClientError as e:
        logger.error(f"Failed to update DynamoDB: {e}")
        raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing Transcribe output.
    
    Expected input from Step Functions:
    {
        "call_id": "...",
        "s3_bucket": "...",
        "transcribe_output_key": "..."
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    call_id = event['call_id']
    s3_bucket = event.get('s3_bucket', S3_BUCKET)
    transcribe_output_key = event['transcribe_output_key']
    
    try:
        # Get Transcribe output
        transcribe_output = get_transcribe_output(s3_bucket, transcribe_output_key)
        
        # Format transcript
        formatted_data = format_transcript(transcribe_output)
        
        # Save formatted transcript to S3
        transcript_key = save_formatted_transcript(call_id, formatted_data)
        
        # Update DynamoDB
        duration = formatted_data['metadata']['total_duration_seconds']
        update_dynamodb_status(call_id, transcript_key, duration)
        
        # Return data for next step (Bedrock summarization)
        return {
            'call_id': call_id,
            's3_bucket': s3_bucket,
            'transcript_key': transcript_key,
            'formatted_transcript': formatted_data['formatted_transcript'],
            'metadata': formatted_data['metadata']
        }
        
    except Exception as e:
        logger.error(f"Error processing transcript: {e}", exc_info=True)
        raise
