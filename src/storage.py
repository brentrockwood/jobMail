"""SQLite storage for tracking processed emails."""

import logging
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path

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
        self._conn = None
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get or create a database connection with proper settings.

        Returns:
            SQLite connection with optimized settings for concurrency
        """
        if self._conn is None:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create connection with increased timeout (30 seconds)
            self._conn = sqlite3.connect(str(self.db_path), timeout=30.0)

            # Enable WAL mode for better concurrency
            self._conn.execute("PRAGMA journal_mode=WAL")

            # Enable foreign keys
            self._conn.execute("PRAGMA foreign_keys=ON")

        return self._conn

    def _execute_with_retry(
        self, query: str, params: tuple = (), max_retries: int = 3
    ) -> sqlite3.Cursor:
        """
        Execute a query with retry logic for database lock issues.

        Args:
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum number of retry attempts

        Returns:
            Cursor with query results

        Raises:
            sqlite3.OperationalError: If all retries fail
        """
        conn = self._get_connection()
        last_error = None

        for attempt in range(max_retries):
            try:
                return conn.execute(query, params)
            except sqlite3.OperationalError as e:
                last_error = e
                if (
                    "database is locked" in str(e) or "unable to open" in str(e)
                ) and attempt < max_retries - 1:
                    wait_time = 0.1 * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time:.1f}s: {e}"
                    )
                    time.sleep(wait_time)
                    # Try to reconnect on "unable to open" errors
                    if "unable to open" in str(e):
                        self._conn = None
                    continue
                raise

        raise last_error  # type: ignore

    def _init_database(self) -> None:
        """Create the database schema if it doesn't exist."""
        conn = self._get_connection()
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
        cursor = self._execute_with_retry(
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
        reasoning: str | None = None,
        label_applied: str | None = None,
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
        processed_at = datetime.now(UTC).isoformat()
        conn = self._get_connection()
        self._execute_with_retry(
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
        cursor = self._execute_with_retry(
            """
            SELECT classification, COUNT(*) as count
            FROM processed_emails
            GROUP BY classification
            """
        )
        stats = {row[0]: row[1] for row in cursor.fetchall()}

        # Add total count
        cursor = self._execute_with_retry("SELECT COUNT(*) FROM processed_emails")
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
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = self._execute_with_retry(
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
        self, classification: ClassificationCategory, limit: int | None = None
    ) -> list[dict]:
        """
        Get emails by classification category.

        Args:
            classification: Classification category to filter by
            limit: Optional maximum number of emails to return

        Returns:
            List of dictionaries containing email processing information
        """
        conn = self._get_connection()
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

        cursor = self._execute_with_retry(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def clear_all(self) -> int:
        """
        Clear all processed emails from the database.

        WARNING: This is destructive and should only be used for testing
        or when explicitly requested.

        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        cursor = self._execute_with_retry("DELETE FROM processed_emails")
        deleted = cursor.rowcount
        conn.commit()
        logger.warning(f"Cleared {deleted} records from database")
        return deleted

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
