#!/usr/bin/env python3
"""
Fetch real emails from Gmail and save them as test fixtures.

This script fetches a specified number of emails from Gmail and saves them
to tests/fixtures/emails/ for use in classification testing. This creates
a stable corpus that can be used to test different AI models and compare
their classification results over time.

Usage:
    python tests/fetch_test_emails.py [--count N] [--query "gmail query"]

The saved emails include an optional 'expected_classification' field that
can be manually edited to record the correct classification for accuracy testing.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config, setup_logging
from src.gmail_client import GmailClient
from src.processor import extract_email_parts

logger = logging.getLogger(__name__)


def fetch_and_save_emails(count: int = 10, query: str = "in:inbox") -> None:
    """
    Fetch emails from Gmail and save them as test fixtures.

    Args:
        count: Number of emails to fetch
        query: Gmail search query
    """
    # Load config
    config = Config.from_env()
    setup_logging(config.log_level)

    # Initialize Gmail client
    logger.info("Initializing Gmail client...")
    gmail_client = GmailClient(config.gmail_credentials_file, config.gmail_token_file)
    gmail_client.authenticate()

    # Fetch emails
    logger.info(f"Fetching {count} emails with query: {query}")
    messages = gmail_client.list_messages(query=query, max_results=count)

    if not messages:
        logger.warning("No messages found")
        return

    logger.info(f"Found {len(messages)} messages, fetching details...")

    # Create output directory
    output_dir = Path(__file__).parent / "fixtures" / "emails"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch and save each email
    for i, msg in enumerate(messages, 1):
        message_id = msg["id"]
        logger.info(f"Fetching email {i}/{len(messages)}: {message_id}")

        # Get full message
        message = gmail_client.get_message(message_id)

        # Extract parts
        subject, from_email, body = extract_email_parts(message)

        # Truncate very large bodies to avoid rate limits in testing
        # Keep first 5000 chars which is enough for classification
        max_body_length = 5000
        if len(body) > max_body_length:
            body = body[:max_body_length] + "\n\n[... truncated for testing ...]"

        # Get date header
        headers = message.get("payload", {}).get("headers", [])
        date = ""
        for header in headers:
            if header["name"].lower() == "date":
                date = header["value"]
                break

        # Create email data
        email_data = {
            "message_id": message_id,
            "subject": subject,
            "from": from_email,
            "date": date,
            "body": body,
            "expected_classification": None,  # To be filled in manually
            "notes": "",  # Optional notes about this email
        }

        # Save to file
        filename = f"email_{i:03d}.json"
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(email_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved to {filepath}")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  From: {from_email}")
        logger.info(f"  Body length: {len(body)} chars")

    logger.info(f"\n✓ Successfully saved {len(messages)} emails to {output_dir}")
    logger.info(
        "\nYou can now manually edit the JSON files to add 'expected_classification' values:"
    )
    logger.info("  - acknowledgement")
    logger.info("  - rejection")
    logger.info("  - followup_required")
    logger.info("  - jobboard")
    logger.info("  - unknown")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch emails from Gmail and save as test fixtures"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of emails to fetch (default: 10)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="in:inbox",
        help='Gmail search query (default: "in:inbox")',
    )

    args = parser.parse_args()

    try:
        fetch_and_save_emails(count=args.count, query=args.query)
    except Exception as e:
        logger.error(f"Error fetching emails: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
