"""Main email processing logic."""

import base64
import logging
from typing import Any

from .classifier import ClassificationCategory, create_classifier
from .config import Config
from .gmail_client import GmailClient
from .storage import EmailStorage

logger = logging.getLogger(__name__)


def extract_email_parts(message: dict[str, Any]) -> tuple[str, str, str]:
    """
    Extract subject, from, and body from Gmail message.

    Args:
        message: Gmail message dict from API

    Returns:
        Tuple of (subject, from_email, body_text)
    """
    headers = message.get("payload", {}).get("headers", [])

    # Extract subject and from
    subject = ""
    from_email = ""
    for header in headers:
        if header["name"].lower() == "subject":
            subject = header["value"]
        elif header["name"].lower() == "from":
            from_email = header["value"]

    # Extract body text
    body_text = ""
    payload = message.get("payload", {})

    # Try to get plain text body
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                body_data = part.get("body", {}).get("data", "")
                if body_data:
                    body_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                    break
    elif payload.get("mimeType") == "text/plain":
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            body_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

    # If no plain text, try HTML
    if not body_text and "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/html":
                body_data = part.get("body", {}).get("data", "")
                if body_data:
                    # Basic HTML to text conversion (strip tags)
                    html_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                    # Simple tag removal - for production might want a proper HTML parser
                    import re

                    body_text = re.sub(r"<[^>]+>", "", html_text)
                    break

    return subject, from_email, body_text


class EmailProcessor:
    """Processes emails through classification and applies Gmail actions."""

    def __init__(self, config: Config):
        """
        Initialize the processor.

        Args:
            config: Application configuration
        """
        self.config = config
        self.gmail_client = GmailClient(config.gmail_credentials_file, config.gmail_token_file)
        self.storage = EmailStorage(config.database_path)
        self.classifier = create_classifier(config)

        # Cache label IDs to avoid repeated API calls
        self._label_cache: dict[str, str] = {}

    def authenticate(self) -> None:
        """Authenticate with Gmail API."""
        self.gmail_client.authenticate()

    def _get_label_id(self, label_name: str) -> str:
        """
        Get label ID from cache or create/fetch from Gmail.

        Args:
            label_name: Name of the label

        Returns:
            Label ID
        """
        if label_name not in self._label_cache:
            self._label_cache[label_name] = self.gmail_client.get_or_create_label(label_name)
        return self._label_cache[label_name]

    def process_message(self, message_id: str) -> bool:
        """
        Process a single message through classification and apply actions.

        Args:
            message_id: Gmail message ID

        Returns:
            True if message was processed, False if skipped (already processed)
        """
        # Check if already processed
        if self.storage.is_processed(message_id):
            logger.debug(f"Message {message_id} already processed, skipping")
            return False

        # Get full message
        logger.info(f"Processing message: {message_id}")
        message = self.gmail_client.get_message(message_id)

        # Extract email parts
        subject, from_email, body_text = extract_email_parts(message)
        logger.debug(f"Subject: {subject}")
        logger.debug(f"From: {from_email}")

        # Classify email
        classification_result = self.classifier.classify(subject, body_text)
        logger.info(
            f"Classification: {classification_result.category.value} "
            f"(confidence: {classification_result.confidence:.2f})"
        )

        # Apply actions based on classification and confidence
        label_applied = None
        archived = False

        if classification_result.confidence >= self.config.confidence_threshold:
            if classification_result.category == ClassificationCategory.ACKNOWLEDGEMENT:
                label_applied = self.config.label_acknowledged
                archived = True
            elif classification_result.category == ClassificationCategory.REJECTION:
                label_applied = self.config.label_rejected
                archived = True
            elif classification_result.category == ClassificationCategory.FOLLOWUP:
                label_applied = self.config.label_followup
                archived = False
            elif classification_result.category == ClassificationCategory.JOBBOARD:
                label_applied = self.config.label_jobboard
                archived = True
            # UNKNOWN category: no action
        else:
            logger.info(
                f"Confidence {classification_result.confidence:.2f} below threshold "
                f"{self.config.confidence_threshold}, no action taken"
            )

        # Apply Gmail actions (unless in dry-run mode)
        if label_applied:
            if self.config.dry_run:
                logger.info(f"[DRY RUN] Would apply label: {label_applied}")
                if archived:
                    logger.info("[DRY RUN] Would archive message")
            else:
                self.gmail_client.apply_label(message_id, label_applied)
                logger.info(f"Applied label: {label_applied}")

                if archived:
                    self.gmail_client.archive_message(message_id)
                    logger.info("Archived message")

        # Record in database
        self.storage.record_processed(
            message_id=message_id,
            subject=subject,
            from_email=from_email,
            classification=classification_result.category,
            confidence=classification_result.confidence,
            provider=classification_result.provider,
            model=classification_result.model,
            reasoning=classification_result.reasoning,
            label_applied=label_applied,
            archived=archived,
        )

        return True

    def process_inbox(
        self, query: str = "in:inbox", max_messages: int | None = None
    ) -> dict[str, int]:
        """
        Process messages in the inbox.

        Args:
            query: Gmail search query (default: "in:inbox")
            max_messages: Maximum number of messages to process (uses batch_size if None)

        Returns:
            Dictionary with processing statistics
        """
        if max_messages is None:
            max_messages = self.config.batch_size

        logger.info(f"Fetching up to {max_messages} messages with query: {query}")
        messages = self.gmail_client.list_messages(query=query, max_results=max_messages)

        if not messages:
            logger.info("No messages found")
            return {"found": 0, "processed": 0, "skipped": 0}

        logger.info(f"Found {len(messages)} messages")

        stats = {
            "found": len(messages),
            "processed": 0,
            "skipped": 0,
        }

        for msg in messages:
            message_id = msg["id"]
            try:
                if self.process_message(message_id):
                    stats["processed"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Error processing message {message_id}: {e}", exc_info=True)
                # Continue processing other messages

        logger.info(
            f"Processing complete: {stats['processed']} processed, "
            f"{stats['skipped']} skipped, {len(messages)} total"
        )

        return stats

    def get_stats(self) -> dict[str, int]:
        """
        Get processing statistics from database.

        Returns:
            Dictionary with counts by classification category
        """
        return self.storage.get_stats()
