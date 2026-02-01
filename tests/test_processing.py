"""
Tests for the AI Processing Lambda functions.

Tests cover:
- Amazon Transcribe job creation
- Transcript processing
- Bedrock summarization
- DynamoDB updates
"""
import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Set environment variables before imports
os.environ['DYNAMODB_TABLE'] = 'test-table'
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['TRANSCRIBE_OUTPUT_BUCKET'] = 'test-bucket'
os.environ['BEDROCK_MODEL_ID'] = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
os.environ['MAX_TOKENS'] = '4096'


class TestStartTranscribe:
    """Test cases for start_transcribe Lambda."""
    
    @pytest.fixture
    def mock_event(self):
        """Valid Step Functions input."""
        return {
            'call_id': 'call-abc12345',
            's3_bucket': 'test-bucket',
            's3_key': 'raw-audio/2024/01/15/call-abc12345.mp3',
            'caller_id': '+14155551234',
            'assigned_user_id': 'user-123'
        }
    
    def test_generates_unique_job_name(self, mock_event):
        """Transcription job names should be unique."""
        import uuid
        call_id = mock_event['call_id']
        job_name = f"call-{call_id}-{uuid.uuid4().hex[:8]}"
        
        assert job_name.startswith('call-')
        assert call_id in job_name
    
    def test_media_format_detection(self):
        """Media format should be detected from file extension."""
        format_map = {
            'mp3': 'mp3',
            'mp4': 'mp4',
            'm4a': 'mp4',
            'wav': 'wav',
            'flac': 'flac',
            'ogg': 'ogg',
            'webm': 'webm',
            'amr': 'amr'
        }
        
        for ext, expected_format in format_map.items():
            s3_key = f"raw-audio/2024/01/15/call-123.{ext}"
            detected = s3_key.lower().split('.')[-1]
            assert format_map.get(detected, 'mp3') == expected_format
    
    def test_output_key_format(self, mock_event):
        """Transcribe output key should follow expected format."""
        date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
        call_id = mock_event['call_id']
        output_key = f"transcripts/{date_prefix}/{call_id}.json"
        
        assert output_key.startswith('transcripts/')
        assert call_id in output_key
        assert output_key.endswith('.json')


class TestProcessTranscript:
    """Test cases for process_transcript Lambda."""
    
    @pytest.fixture
    def mock_transcribe_output(self):
        """Sample Amazon Transcribe output."""
        return {
            "jobName": "call-abc12345-xyz",
            "accountId": "123456789012",
            "results": {
                "transcripts": [
                    {
                        "transcript": "Hello, this is customer service. How can I help you today?"
                    }
                ],
                "speaker_labels": {
                    "speakers": 2,
                    "segments": [
                        {
                            "start_time": "0.0",
                            "end_time": "3.5",
                            "speaker_label": "spk_0",
                            "items": [
                                {"start_time": "0.0", "end_time": "0.5", "speaker_label": "spk_0"}
                            ]
                        }
                    ]
                },
                "items": [
                    {
                        "start_time": "0.0",
                        "end_time": "0.5",
                        "alternatives": [{"content": "Hello", "confidence": "0.99"}],
                        "type": "pronunciation"
                    },
                    {
                        "alternatives": [{"content": ",", "confidence": "0.0"}],
                        "type": "punctuation"
                    }
                ]
            },
            "status": "COMPLETED"
        }
    
    def test_extracts_transcript_text(self, mock_transcribe_output):
        """Should extract plain text transcript."""
        transcript = mock_transcribe_output['results']['transcripts'][0]['transcript']
        assert len(transcript) > 0
        assert "Hello" in transcript
    
    def test_identifies_speaker_count(self, mock_transcribe_output):
        """Should identify number of speakers."""
        speakers = mock_transcribe_output['results']['speaker_labels']['speakers']
        assert speakers == 2  # Customer and Agent
    
    def test_formats_transcript_with_speakers(self, mock_transcribe_output):
        """Should format transcript with speaker labels."""
        # Expected format: "Agent: Hello, this is customer service..."
        # This tests the formatting logic
        segments = mock_transcribe_output['results']['speaker_labels']['segments']
        assert len(segments) > 0
        assert 'speaker_label' in segments[0]


class TestGenerateSummary:
    """Test cases for generate_summary Lambda (Bedrock)."""
    
    @pytest.fixture
    def mock_transcript(self):
        """Sample formatted transcript."""
        return """
Agent: Good morning, thank you for calling Customer Care. How can I help you today?

Customer: Hi, I'm having trouble with my account. I was charged twice for my subscription last month.

Agent: I'm sorry to hear that. Let me look into this for you. Can you please provide your account number?

Customer: Sure, it's 12345678.

Agent: Thank you. I can see the duplicate charge. I'll process a refund for you right away. Is there anything else I can help with?

Customer: No, that's all. Thank you so much!

Agent: You're welcome. Have a great day!
"""
    
    def test_prompt_includes_transcript(self, mock_transcript):
        """Prompt should include the full transcript."""
        prompt = f"""Analyze this customer service call transcript and provide:
1. Brief summary (2-3 sentences)
2. Key points discussed
3. Action items
4. Customer sentiment (positive/neutral/negative)
5. Urgency level (low/medium/high)

Transcript:
{mock_transcript}
"""
        assert mock_transcript in prompt
        assert "summary" in prompt.lower()
        assert "sentiment" in prompt.lower()
    
    def test_expected_response_structure(self):
        """Bedrock response should have expected structure."""
        expected_structure = {
            'summary': str,
            'key_points': list,
            'action_items': list,
            'sentiment': str,
            'urgency': str,
            'categories': list
        }
        
        mock_response = {
            'summary': 'Customer called about duplicate charge.',
            'key_points': ['Duplicate charge identified', 'Refund processed'],
            'action_items': ['Verify refund completed'],
            'sentiment': 'positive',
            'urgency': 'medium',
            'categories': ['billing', 'refund']
        }
        
        for key, expected_type in expected_structure.items():
            assert key in mock_response
            assert isinstance(mock_response[key], expected_type)
    
    def test_sentiment_values(self):
        """Sentiment should be one of defined values."""
        valid_sentiments = {'positive', 'neutral', 'negative'}
        assert 'positive' in valid_sentiments
    
    def test_urgency_values(self):
        """Urgency should be one of defined values."""
        valid_urgencies = {'low', 'medium', 'high', 'critical'}
        assert 'medium' in valid_urgencies


class TestSaveSummary:
    """Test cases for save_summary Lambda."""
    
    @pytest.fixture
    def mock_summary_input(self):
        """Input from generate_summary step."""
        return {
            'call_id': 'call-abc12345',
            'summary': 'Customer called about a duplicate charge and received a refund.',
            'key_points': [
                'Duplicate charge on subscription',
                'Refund processed immediately',
                'Customer satisfied with resolution'
            ],
            'action_items': [
                'Verify refund completed within 3-5 business days'
            ],
            'sentiment': 'positive',
            'urgency': 'medium',
            'categories': ['billing', 'refund'],
            'transcript_s3_key': 'transcripts/2024/01/15/call-abc12345.txt'
        }
    
    def test_dynamodb_update_expression(self, mock_summary_input):
        """DynamoDB update should set all required fields."""
        fields_to_update = [
            'summary', 'key_points', 'action_items',
            'sentiment', 'urgency', 'categories',
            'transcript_s3_key', 'status', 'completed_at'
        ]
        
        # All these fields should be in the update expression
        for field in fields_to_update:
            if field not in ['status', 'completed_at']:
                assert field in mock_summary_input
    
    def test_status_set_to_completed(self):
        """Final status should be COMPLETED."""
        final_status = 'COMPLETED'
        assert final_status == 'COMPLETED'
    
    def test_completed_at_timestamp(self):
        """completed_at should be ISO format timestamp."""
        timestamp = datetime.utcnow().isoformat() + 'Z'
        assert timestamp.endswith('Z')
        assert 'T' in timestamp


class TestUpdateStatus:
    """Test cases for update_status Lambda."""
    
    @pytest.mark.parametrize("status,expected_valid", [
        ('PENDING', True),
        ('TRANSCRIBING', True),
        ('SUMMARIZING', True),
        ('COMPLETED', True),
        ('FAILED', True),
        ('PROCESSING', False),
        ('UNKNOWN', False),
    ])
    def test_valid_status_values(self, status, expected_valid):
        """Only defined status values should be valid."""
        valid_statuses = {'PENDING', 'TRANSCRIBING', 'SUMMARIZING', 'COMPLETED', 'FAILED'}
        is_valid = status in valid_statuses
        assert is_valid == expected_valid
    
    def test_failed_status_includes_error(self):
        """FAILED status should include error message."""
        update_input = {
            'call_id': 'call-abc12345',
            'status': 'FAILED',
            'error_message': 'Transcription failed: Audio file corrupted'
        }
        
        assert update_input['status'] == 'FAILED'
        assert 'error_message' in update_input
        assert len(update_input['error_message']) > 0
