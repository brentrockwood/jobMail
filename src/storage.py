"""SQLite storage for tracking processed emails."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .classifier import ClassificationCategory

logger = logging.getLogger(__name__)


class EmailStorage:
    """Manages SQLite database for tracking processed emails."""

    def __init__(self, db_path: Path):
        """
        Initialize the storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Create the database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_emails (
                    message_id TEXT PRIMARY KEY,
                    processed_at TEXT NOT NULL,
                    subject TEXT,
                    from_email TEXT,
                    classification TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    reasoning TEXT,
                    label_applied TEXT,
                    archived INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON processed_emails(processed_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_classification 
                ON processed_emails(classification)
                """
            )
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def is_processed(self, message_id: str) -> bool:
        """
        Check if an email has already been processed.

        Args:
            message_id: Gmail message ID

        Returns:
            True if the email has been processed, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_emails WHERE message_id = ?",
                (message_id,),
            )
            return cursor.fetchone() is not None

    def record_processed(
        self,
        message_id: str,
        subject: str,
        from_email: str,
        classification: ClassificationCategory,
        confidence: float,
        provider: str,
        model: str,
        reasoning: Optional[str] = None,
        label_applied: Optional[str] = None,
        archived: bool = False,
    ) -> None:
        """
        Record that an email has been processed.

        Args:
            message_id: Gmail message ID
            subject: Email subject line
            from_email: Sender email address
            classification: Classification category
            confidence: Confidence score (0.0-1.0)
            provider: AI provider used (openai/anthropic/ollama)
            model: Model name used for classification
            reasoning: Optional reasoning for the classification
            label_applied: Optional label that was applied
            archived: Whether the email was archived
        """
        processed_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO processed_emails 
                (message_id, processed_at, subject, from_email, classification, 
                 confidence, provider, model, reasoning, label_applied, archived)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    processed_at,
                    subject,
                    from_email,
                    classification.value,
                    confidence,
                    provider,
                    model,
                    reasoning,
                    label_applied,
                    1 if archived else 0,
                ),
            )
            conn.commit()
        logger.debug(f"Recorded processed email: {message_id}")

    def get_stats(self) -> dict[str, int]:
        """
        Get processing statistics.

        Returns:
            Dictionary with counts by classification category
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT classification, COUNT(*) as count
                FROM processed_emails
                GROUP BY classification
                """
            )
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Add total count
            cursor = conn.execute("SELECT COUNT(*) FROM processed_emails")
            stats["total"] = cursor.fetchone()[0]
            
            return stats

    def get_recent_processed(self, limit: int = 10) -> list[dict]:
        """
        Get recently processed emails.

        Args:
            limit: Maximum number of emails to return

        Returns:
            List of dictionaries containing email processing information
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT message_id, processed_at, subject, from_email, 
                       classification, confidence, provider, model, 
                       label_applied, archived
                FROM processed_emails
                ORDER BY processed_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_by_classification(
        self, classification: ClassificationCategory, limit: Optional[int] = None
    ) -> list[dict]:
        """
        Get emails by classification category.

        Args:
            classification: Classification category to filter by
            limit: Optional maximum number of emails to return

        Returns:
            List of dictionaries containing email processing information
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT message_id, processed_at, subject, from_email, 
                       classification, confidence, provider, model, 
                       label_applied, archived
                FROM processed_emails
                WHERE classification = ?
                ORDER BY processed_at DESC
            """
            params: tuple = (classification.value,)
            
            if limit is not None:
                query += " LIMIT ?"
                params = (classification.value, limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def clear_all(self) -> int:
        """
        Clear all processed emails from the database.
        
        WARNING: This is destructive and should only be used for testing
        or when explicitly requested.

        Returns:
            Number of records deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM processed_emails")
            deleted = cursor.rowcount
            conn.commit()
        logger.warning(f"Cleared {deleted} records from database")
        return deleted
