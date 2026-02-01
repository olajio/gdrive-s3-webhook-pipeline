"""
AWS Lambda function to generate AI summaries using Amazon Bedrock.
Uses Claude 3.5 Sonnet to analyze call transcripts and extract insights.

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
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
BEDROCK_REGION = os.environ.get('BEDROCK_REGION', 'us-east-1')

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)


def create_summary_prompt(transcript: str, metadata: Dict[str, Any]) -> str:
    """Create the prompt for Bedrock to generate a structured summary."""
    
    system_prompt = """You are an expert customer service analyst. Your task is to analyze customer care call transcripts and extract key information in a structured format.

You must return ONLY valid JSON with no additional text, markdown formatting, or code blocks. The JSON must be parseable.

Focus on:
1. Identifying the main issue or reason for the call
2. Extracting key details discussed
3. Identifying any action items or commitments made
4. Determining next steps
5. Assessing the overall sentiment of the interaction
6. Extracting any mentioned IDs (agent ID, customer ID, case numbers)

Be factual and accurate. Do not infer or hallucinate information not present in the transcript."""

    user_prompt = f"""Analyze the following customer care call transcript and provide a structured summary.

Call Duration: {metadata.get('total_duration_seconds', 0)} seconds
Word Count: {metadata.get('word_count', 0)}

TRANSCRIPT:
{transcript}

Return a JSON object with exactly these fields:
{{
  "call_date": "YYYY-MM-DD format, extract from transcript or use today",
  "issue_sentence": "Single sentence (max 100 chars) describing the main issue or reason for the call",
  "key_details": ["Array of 3-5 key details or facts discussed in the call"],
  "action_items": ["Array of action items or commitments made during the call"],
  "next_steps": ["Array of follow-up steps mentioned or implied"],
  "sentiment": "One of: Positive, Neutral, or Negative based on overall tone",
  "agent_id": "Agent ID if mentioned, otherwise null",
  "customer_id": "Customer ID or account number if mentioned, otherwise null"
}}

IMPORTANT: Return ONLY the JSON object, no other text."""

    return system_prompt, user_prompt


def call_bedrock(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Call Amazon Bedrock with the prompt and return the response."""
    
    # Prepare the request for Claude 3.5 Sonnet
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "temperature": 0.3,
        "top_p": 0.9,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract the text content from Claude's response
        content = response_body.get('content', [])
        if content and len(content) > 0:
            text = content[0].get('text', '')
            logger.info(f"Bedrock response: {text[:500]}...")
            return text
        else:
            raise ValueError("Empty response from Bedrock")
            
    except ClientError as e:
        logger.error(f"Bedrock API error: {e}")
        raise


def parse_summary_response(response_text: str) -> Dict[str, Any]:
    """Parse the JSON response from Bedrock."""
    
    # Clean up the response - remove any markdown code blocks if present
    text = response_text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    
    try:
        summary = json.loads(text)
        
        # Validate required fields
        required_fields = ['issue_sentence', 'key_details', 'action_items', 'next_steps', 'sentiment']
        for field in required_fields:
            if field not in summary:
                logger.warning(f"Missing field in summary: {field}")
                summary[field] = [] if field.endswith('s') and field != 'sentiment' else ''
        
        # Validate sentiment
        valid_sentiments = ['Positive', 'Neutral', 'Negative']
        if summary.get('sentiment') not in valid_sentiments:
            summary['sentiment'] = 'Neutral'
        
        # Ensure arrays are arrays
        for field in ['key_details', 'action_items', 'next_steps']:
            if not isinstance(summary.get(field), list):
                summary[field] = [summary[field]] if summary.get(field) else []
        
        return summary
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response as JSON: {e}")
        logger.error(f"Response text: {text}")
        
        # Return a fallback summary
        return {
            'call_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'issue_sentence': 'Unable to parse call summary automatically',
            'key_details': ['Transcript available for manual review'],
            'action_items': [],
            'next_steps': ['Manual review required'],
            'sentiment': 'Neutral',
            'agent_id': None,
            'customer_id': None,
            'parse_error': str(e)
        }


def save_summary_to_s3(call_id: str, summary: Dict[str, Any]) -> str:
    """Save the summary to S3."""
    date_prefix = datetime.utcnow().strftime('%Y-%m-%d')
    s3_key = f"summaries/{date_prefix}/{call_id}-summary.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(summary, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Saved summary to s3://{S3_BUCKET}/{s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"Failed to save summary: {e}")
        raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for generating AI summaries.
    
    Expected input from Step Functions:
    {
        "call_id": "...",
        "s3_bucket": "...",
        "transcript_key": "...",
        "formatted_transcript": "...",
        "metadata": {...}
    }
    """
    logger.info(f"Received event: {json.dumps(event)[:1000]}...")
    
    call_id = event['call_id']
    s3_bucket = event.get('s3_bucket', S3_BUCKET)
    formatted_transcript = event['formatted_transcript']
    metadata = event.get('metadata', {})
    
    try:
        # Create prompt for Bedrock
        system_prompt, user_prompt = create_summary_prompt(formatted_transcript, metadata)
        
        # Call Bedrock for summarization
        logger.info(f"Calling Bedrock model: {BEDROCK_MODEL_ID}")
        response_text = call_bedrock(system_prompt, user_prompt)
        
        # Parse the response
        summary = parse_summary_response(response_text)
        
        # Add metadata to summary
        summary['call_id'] = call_id
        summary['processed_at'] = datetime.utcnow().isoformat() + 'Z'
        summary['duration_seconds'] = metadata.get('total_duration_seconds', 0)
        summary['word_count'] = metadata.get('word_count', 0)
        
        # Save summary to S3
        summary_key = save_summary_to_s3(call_id, summary)
        
        # Return data for next step
        return {
            'call_id': call_id,
            's3_bucket': s3_bucket,
            'summary_key': summary_key,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise
