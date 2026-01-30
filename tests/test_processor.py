"""Tests for processor module."""

import base64
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.classifier import ClassificationCategory, ClassificationResult
from src.config import Config
from src.processor import EmailProcessor, extract_email_parts


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def mock_config(temp_db):
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.gmail_credentials_file = Path("credentials.json")
    config.gmail_token_file = Path("token.json")
    config.database_path = temp_db
    config.confidence_threshold = 0.8
    config.batch_size = 20
    config.label_acknowledged = "Acknowledged"
    config.label_rejected = "Rejected"
    config.label_followup = "FollowUp"
    config.label_jobboard = "JobBoard"
    config.dry_run = False
    config.ai_provider = "openai"
    config.openai_api_key = "test-key"
    config.openai_model = "gpt-4"
    return config


def test_extract_email_parts_plain_text():
    """Test extracting parts from a plain text email."""
    body_text = "This is the email body"
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    
    message = {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
            ],
            "mimeType": "text/plain",
            "body": {
                "data": encoded_body,
            },
        }
    }
    
    subject, from_email, body = extract_email_parts(message)
    assert subject == "Test Subject"
    assert from_email == "sender@example.com"
    assert body == body_text


def test_extract_email_parts_multipart():
    """Test extracting parts from a multipart email."""
    plain_text = "This is plain text"
    html_text = "<html><body>This is HTML</body></html>"
    
    encoded_plain = base64.urlsafe_b64encode(plain_text.encode()).decode()
    encoded_html = base64.urlsafe_b64encode(html_text.encode()).decode()
    
    message = {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Multipart Test"},
                {"name": "From", "value": "test@example.com"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": encoded_plain},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": encoded_html},
                },
            ],
        }
    }
    
    subject, from_email, body = extract_email_parts(message)
    assert subject == "Multipart Test"
    assert from_email == "test@example.com"
    # Should prefer plain text over HTML
    assert body == plain_text


def test_extract_email_parts_html_only():
    """Test extracting parts from HTML-only email."""
    html_text = "<html><body><p>Hello World</p></body></html>"
    encoded_html = base64.urlsafe_b64encode(html_text.encode()).decode()
    
    message = {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "HTML Test"},
                {"name": "From", "value": "html@example.com"},
            ],
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {"data": encoded_html},
                },
            ],
        }
    }
    
    subject, from_email, body = extract_email_parts(message)
    assert subject == "HTML Test"
    # HTML tags should be stripped
    assert "Hello World" in body
    assert "<html>" not in body


def test_extract_email_parts_empty():
    """Test extracting parts from email with minimal data."""
    message = {
        "payload": {
            "headers": [],
        }
    }
    
    subject, from_email, body = extract_email_parts(message)
    assert subject == ""
    assert from_email == ""
    assert body == ""


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_processor_init(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processor initialization."""
    processor = EmailProcessor(mock_config)
    
    assert processor.config == mock_config
    assert processor.gmail_client is not None
    assert processor.storage is not None
    assert processor.classifier is not None


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_processor_authenticate(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processor authentication."""
    processor = EmailProcessor(mock_config)
    mock_gmail_instance = mock_gmail_client.return_value
    
    processor.authenticate()
    
    mock_gmail_instance.authenticate.assert_called_once()


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_message_already_processed(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing a message that's already been processed."""
    processor = EmailProcessor(mock_config)
    
    # Mark message as already processed
    processor.storage.record_processed(
        message_id="msg123",
        subject="Test",
        from_email="test@example.com",
        classification=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.9,
        provider="openai",
        model="gpt-4",
    )
    
    # Try to process again
    result = processor.process_message("msg123")
    
    # Should return False (skipped)
    assert result is False
    # Should not call Gmail API
    mock_gmail_client.return_value.get_message.assert_not_called()


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_message_acknowledgement(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing an acknowledgement email."""
    # Setup mocks
    mock_gmail_instance = mock_gmail_client.return_value
    mock_classifier_instance = mock_create_classifier.return_value
    
    # Mock Gmail response
    body_text = "Thank you for your application"
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    
    mock_gmail_instance.get_message.return_value = {
        "id": "msg123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Application Received"},
                {"name": "From", "value": "hr@company.com"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body},
        },
    }
    
    # Mock classification result
    mock_classifier_instance.classify.return_value = ClassificationResult(
        category=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.95,
        provider="openai",
        model="gpt-4",
        reasoning="Clear acknowledgement",
    )
    
    # Process message
    processor = EmailProcessor(mock_config)
    result = processor.process_message("msg123")
    
    # Verify
    assert result is True
    mock_gmail_instance.get_message.assert_called_once_with("msg123")
    mock_classifier_instance.classify.assert_called_once()
    mock_gmail_instance.apply_label.assert_called_once_with("msg123", "Acknowledged")
    mock_gmail_instance.archive_message.assert_called_once_with("msg123")
    assert processor.storage.is_processed("msg123")


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_message_rejection(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing a rejection email."""
    # Setup mocks
    mock_gmail_instance = mock_gmail_client.return_value
    mock_classifier_instance = mock_create_classifier.return_value
    
    # Mock Gmail response
    body_text = "We regret to inform you"
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    
    mock_gmail_instance.get_message.return_value = {
        "id": "msg456",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Application Status"},
                {"name": "From", "value": "hr@company.com"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body},
        },
    }
    
    # Mock classification result
    mock_classifier_instance.classify.return_value = ClassificationResult(
        category=ClassificationCategory.REJECTION,
        confidence=0.92,
        provider="anthropic",
        model="claude-3",
        reasoning="Clear rejection",
    )
    
    # Process message
    processor = EmailProcessor(mock_config)
    result = processor.process_message("msg456")
    
    # Verify
    assert result is True
    mock_gmail_instance.apply_label.assert_called_once_with("msg456", "Rejected")
    mock_gmail_instance.archive_message.assert_called_once_with("msg456")


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_message_followup(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing a follow-up required email."""
    # Setup mocks
    mock_gmail_instance = mock_gmail_client.return_value
    mock_classifier_instance = mock_create_classifier.return_value
    
    # Mock Gmail response
    body_text = "Please complete your screening"
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    
    mock_gmail_instance.get_message.return_value = {
        "id": "msg789",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Action Required"},
                {"name": "From", "value": "recruiter@company.com"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body},
        },
    }
    
    # Mock classification result
    mock_classifier_instance.classify.return_value = ClassificationResult(
        category=ClassificationCategory.FOLLOWUP,
        confidence=0.98,
        provider="openai",
        model="gpt-4",
        reasoning="Action required",
    )
    
    # Process message
    processor = EmailProcessor(mock_config)
    result = processor.process_message("msg789")
    
    # Verify
    assert result is True
    mock_gmail_instance.apply_label.assert_called_once_with("msg789", "FollowUp")
    # Should NOT archive follow-up emails
    mock_gmail_instance.archive_message.assert_not_called()


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_message_low_confidence(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing with confidence below threshold."""
    # Setup mocks
    mock_gmail_instance = mock_gmail_client.return_value
    mock_classifier_instance = mock_create_classifier.return_value
    
    # Mock Gmail response
    body_text = "Ambiguous content"
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    
    mock_gmail_instance.get_message.return_value = {
        "id": "msg999",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Unclear"},
                {"name": "From", "value": "test@example.com"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body},
        },
    }
    
    # Mock classification result with low confidence
    mock_classifier_instance.classify.return_value = ClassificationResult(
        category=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.5,  # Below threshold of 0.8
        provider="openai",
        model="gpt-4",
        reasoning="Uncertain",
    )
    
    # Process message
    processor = EmailProcessor(mock_config)
    result = processor.process_message("msg999")
    
    # Verify - should record but not apply label/archive
    assert result is True
    mock_gmail_instance.apply_label.assert_not_called()
    mock_gmail_instance.archive_message.assert_not_called()
    assert processor.storage.is_processed("msg999")


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_message_dry_run(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing in dry-run mode."""
    # Enable dry-run
    mock_config.dry_run = True
    
    # Setup mocks
    mock_gmail_instance = mock_gmail_client.return_value
    mock_classifier_instance = mock_create_classifier.return_value
    
    # Mock Gmail response
    body_text = "Test email"
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    
    mock_gmail_instance.get_message.return_value = {
        "id": "msg111",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test"},
                {"name": "From", "value": "test@example.com"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body},
        },
    }
    
    # Mock classification result
    mock_classifier_instance.classify.return_value = ClassificationResult(
        category=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.95,
        provider="openai",
        model="gpt-4",
    )
    
    # Process message
    processor = EmailProcessor(mock_config)
    result = processor.process_message("msg111")
    
    # Verify - should NOT call Gmail modification APIs
    assert result is True
    mock_gmail_instance.apply_label.assert_not_called()
    mock_gmail_instance.archive_message.assert_not_called()
    # But should still record in database
    assert processor.storage.is_processed("msg111")


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_inbox(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing inbox messages."""
    # Setup mocks
    mock_gmail_instance = mock_gmail_client.return_value
    mock_classifier_instance = mock_create_classifier.return_value
    
    # Mock list_messages response
    mock_gmail_instance.list_messages.return_value = [
        {"id": "msg1"},
        {"id": "msg2"},
        {"id": "msg3"},
    ]
    
    # Mock get_message responses
    def get_message_side_effect(msg_id):
        body_text = f"Email {msg_id}"
        encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
        return {
            "id": msg_id,
            "payload": {
                "headers": [
                    {"name": "Subject", "value": f"Subject {msg_id}"},
                    {"name": "From", "value": "test@example.com"},
                ],
                "mimeType": "text/plain",
                "body": {"data": encoded_body},
            },
        }
    
    mock_gmail_instance.get_message.side_effect = get_message_side_effect
    
    # Mock classifier
    mock_classifier_instance.classify.return_value = ClassificationResult(
        category=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.9,
        provider="openai",
        model="gpt-4",
    )
    
    # Process inbox
    processor = EmailProcessor(mock_config)
    stats = processor.process_inbox(query="in:inbox", max_messages=10)
    
    # Verify
    assert stats["found"] == 3
    assert stats["processed"] == 3
    assert stats["skipped"] == 0
    assert mock_gmail_instance.get_message.call_count == 3


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_process_inbox_empty(mock_create_classifier, mock_gmail_client, mock_config):
    """Test processing empty inbox."""
    # Setup mocks
    mock_gmail_instance = mock_gmail_client.return_value
    mock_gmail_instance.list_messages.return_value = []
    
    # Process inbox
    processor = EmailProcessor(mock_config)
    stats = processor.process_inbox()
    
    # Verify
    assert stats["found"] == 0
    assert stats["processed"] == 0
    assert stats["skipped"] == 0


@patch("src.processor.GmailClient")
@patch("src.processor.create_classifier")
def test_get_stats(mock_create_classifier, mock_gmail_client, mock_config):
    """Test getting processing statistics."""
    processor = EmailProcessor(mock_config)
    
    # Add some processed emails
    processor.storage.record_processed(
        message_id="msg1",
        subject="Test 1",
        from_email="test@example.com",
        classification=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.9,
        provider="openai",
        model="gpt-4",
    )
    
    processor.storage.record_processed(
        message_id="msg2",
        subject="Test 2",
        from_email="test@example.com",
        classification=ClassificationCategory.REJECTION,
        confidence=0.95,
        provider="openai",
        model="gpt-4",
    )
    
    # Get stats
    stats = processor.get_stats()
    
    # Verify
    assert stats["total"] == 2
    assert stats["acknowledgement"] == 1
    assert stats["rejection"] == 1
