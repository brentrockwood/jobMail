"""Tests for storage module."""

import tempfile
from pathlib import Path

import pytest

from src.classifier import ClassificationCategory
from src.storage import EmailStorage


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
def storage(temp_db):
    """Create an EmailStorage instance with temporary database."""
    return EmailStorage(temp_db)


def test_init_creates_database(temp_db):
    """Test that initialization creates the database and schema."""
    # Initialize storage (temp_db is created by fixture)
    storage = EmailStorage(temp_db)
    
    # Database should exist
    assert temp_db.exists()
    
    # Should be able to query the table
    stats = storage.get_stats()
    assert stats["total"] == 0


def test_is_processed_empty_database(storage):
    """Test is_processed returns False for empty database."""
    assert not storage.is_processed("msg123")


def test_record_and_check_processed(storage):
    """Test recording a processed email and checking it."""
    message_id = "msg123"
    
    # Initially not processed
    assert not storage.is_processed(message_id)
    
    # Record as processed
    storage.record_processed(
        message_id=message_id,
        subject="Test Subject",
        from_email="sender@example.com",
        classification=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.95,
        provider="openai",
        model="gpt-4",
        reasoning="Test reasoning",
        label_applied="Acknowledged",
        archived=True,
    )
    
    # Now should be processed
    assert storage.is_processed(message_id)


def test_record_processed_minimal(storage):
    """Test recording with minimal required fields."""
    message_id = "msg456"
    
    storage.record_processed(
        message_id=message_id,
        subject="Test",
        from_email="test@example.com",
        classification=ClassificationCategory.UNKNOWN,
        confidence=0.5,
        provider="anthropic",
        model="claude-3",
    )
    
    assert storage.is_processed(message_id)


def test_get_stats_empty(storage):
    """Test getting stats from empty database."""
    stats = storage.get_stats()
    assert stats["total"] == 0


def test_get_stats_with_data(storage):
    """Test getting stats with multiple entries."""
    # Add different classifications
    storage.record_processed(
        message_id="msg1",
        subject="Test 1",
        from_email="test@example.com",
        classification=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.9,
        provider="openai",
        model="gpt-4",
    )
    
    storage.record_processed(
        message_id="msg2",
        subject="Test 2",
        from_email="test@example.com",
        classification=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.85,
        provider="openai",
        model="gpt-4",
    )
    
    storage.record_processed(
        message_id="msg3",
        subject="Test 3",
        from_email="test@example.com",
        classification=ClassificationCategory.REJECTION,
        confidence=0.95,
        provider="anthropic",
        model="claude-3",
    )
    
    stats = storage.get_stats()
    assert stats["total"] == 3
    assert stats["acknowledgement"] == 2
    assert stats["rejection"] == 1


def test_get_recent_processed_empty(storage):
    """Test getting recent processed emails from empty database."""
    recent = storage.get_recent_processed()
    assert recent == []


def test_get_recent_processed(storage):
    """Test getting recent processed emails."""
    # Add multiple entries
    for i in range(5):
        storage.record_processed(
            message_id=f"msg{i}",
            subject=f"Test {i}",
            from_email="test@example.com",
            classification=ClassificationCategory.ACKNOWLEDGEMENT,
            confidence=0.9,
            provider="openai",
            model="gpt-4",
        )
    
    # Get recent (default limit 10)
    recent = storage.get_recent_processed()
    assert len(recent) == 5
    
    # Should be in reverse chronological order (most recent first)
    assert recent[0]["message_id"] == "msg4"
    assert recent[-1]["message_id"] == "msg0"


def test_get_recent_processed_with_limit(storage):
    """Test getting recent processed emails with limit."""
    # Add multiple entries
    for i in range(10):
        storage.record_processed(
            message_id=f"msg{i}",
            subject=f"Test {i}",
            from_email="test@example.com",
            classification=ClassificationCategory.ACKNOWLEDGEMENT,
            confidence=0.9,
            provider="openai",
            model="gpt-4",
        )
    
    # Get with limit
    recent = storage.get_recent_processed(limit=3)
    assert len(recent) == 3
    assert recent[0]["message_id"] == "msg9"


def test_get_by_classification(storage):
    """Test filtering emails by classification."""
    # Add different classifications
    storage.record_processed(
        message_id="ack1",
        subject="Acknowledgement 1",
        from_email="test@example.com",
        classification=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.9,
        provider="openai",
        model="gpt-4",
    )
    
    storage.record_processed(
        message_id="rej1",
        subject="Rejection 1",
        from_email="test@example.com",
        classification=ClassificationCategory.REJECTION,
        confidence=0.95,
        provider="openai",
        model="gpt-4",
    )
    
    storage.record_processed(
        message_id="ack2",
        subject="Acknowledgement 2",
        from_email="test@example.com",
        classification=ClassificationCategory.ACKNOWLEDGEMENT,
        confidence=0.85,
        provider="anthropic",
        model="claude-3",
    )
    
    # Get acknowledgements
    acks = storage.get_by_classification(ClassificationCategory.ACKNOWLEDGEMENT)
    assert len(acks) == 2
    assert all(e["classification"] == "acknowledgement" for e in acks)
    
    # Get rejections
    rejs = storage.get_by_classification(ClassificationCategory.REJECTION)
    assert len(rejs) == 1
    assert rejs[0]["message_id"] == "rej1"


def test_get_by_classification_with_limit(storage):
    """Test filtering by classification with limit."""
    # Add multiple acknowledgements
    for i in range(5):
        storage.record_processed(
            message_id=f"ack{i}",
            subject=f"Test {i}",
            from_email="test@example.com",
            classification=ClassificationCategory.ACKNOWLEDGEMENT,
            confidence=0.9,
            provider="openai",
            model="gpt-4",
        )
    
    # Get with limit
    acks = storage.get_by_classification(ClassificationCategory.ACKNOWLEDGEMENT, limit=2)
    assert len(acks) == 2


def test_clear_all(storage):
    """Test clearing all records."""
    # Add some records
    for i in range(3):
        storage.record_processed(
            message_id=f"msg{i}",
            subject=f"Test {i}",
            from_email="test@example.com",
            classification=ClassificationCategory.ACKNOWLEDGEMENT,
            confidence=0.9,
            provider="openai",
            model="gpt-4",
        )
    
    # Verify records exist
    assert storage.get_stats()["total"] == 3
    
    # Clear all
    deleted = storage.clear_all()
    assert deleted == 3
    
    # Verify empty
    assert storage.get_stats()["total"] == 0


def test_clear_all_empty(storage):
    """Test clearing empty database."""
    deleted = storage.clear_all()
    assert deleted == 0


def test_all_classification_categories(storage):
    """Test recording all classification categories."""
    categories = [
        ClassificationCategory.ACKNOWLEDGEMENT,
        ClassificationCategory.REJECTION,
        ClassificationCategory.FOLLOWUP,
        ClassificationCategory.JOBBOARD,
        ClassificationCategory.UNKNOWN,
    ]
    
    for i, category in enumerate(categories):
        storage.record_processed(
            message_id=f"msg{i}",
            subject=f"Test {category.value}",
            from_email="test@example.com",
            classification=category,
            confidence=0.8,
            provider="openai",
            model="gpt-4",
        )
    
    stats = storage.get_stats()
    assert stats["total"] == 5
    assert stats["acknowledgement"] == 1
    assert stats["rejection"] == 1
    assert stats["followup_required"] == 1
    assert stats["jobboard"] == 1
    assert stats["unknown"] == 1
