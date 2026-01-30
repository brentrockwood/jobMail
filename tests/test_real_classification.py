"""Test classification with real models and real email data."""

import sys

from src.classifier import create_classifier
from src.config import Config, setup_logging
from src.gmail_client import GmailClient


def extract_email_text(message: dict) -> tuple[str, str]:
    """
    Extract subject and body from Gmail message.

    Args:
        message: Gmail message dict

    Returns:
        Tuple of (subject, body_preview)
    """
    headers = message.get("payload", {}).get("headers", [])
    subject = "No Subject"

    for header in headers:
        if header["name"].lower() == "subject":
            subject = header["value"]
            break

    # Get snippet as body preview (first ~200 chars)
    body = message.get("snippet", "")

    return subject, body


def main() -> int:
    """Test classification with real data and models."""
    setup_logging("INFO")
    print("=" * 80)
    print("REAL EMAIL CLASSIFICATION TEST")
    print("=" * 80)
    print()

    # Load config
    config = Config.from_env()
    config.validate()

    # Update Ollama config for your server
    config.ollama_base_url = "http://ai1.lab:11434/v1"
    config.ollama_model = "qwen2.5:72b-instruct-q4_K_M"
    config.anthropic_model = "claude-sonnet-4-5-20250929"

    print("Configuration:")
    print(f"  OpenAI Model: {config.openai_model}")
    print(f"  Anthropic Model: {config.anthropic_model}")
    print(f"  Ollama URL: {config.ollama_base_url}")
    print(f"  Ollama Model: {config.ollama_model}")
    print()

    # Connect to Gmail
    print("Connecting to Gmail...")
    gmail_client = GmailClient(config.gmail_credentials_file, config.gmail_token_file)

    try:
        gmail_client.authenticate()
    except Exception as e:
        print(f"✗ Gmail authentication failed: {e}")
        return 1

    print("✓ Gmail connected")
    print()

    # Fetch recent emails from inbox
    print("Fetching sample emails from inbox...")
    try:
        messages = gmail_client.list_messages(query="in:inbox", max_results=10)

        if not messages:
            print("✗ No messages found in inbox")
            return 1

        print(f"✓ Found {len(messages)} messages")
        print()

        # Get full details for first 5 messages
        sample_size = min(5, len(messages))
        emails = []

        print(f"Loading details for {sample_size} sample emails...")
        for i, msg_ref in enumerate(messages[:sample_size], 1):
            msg_id = msg_ref["id"]
            message = gmail_client.get_message(msg_id)
            subject, body = extract_email_text(message)
            emails.append((msg_id, subject, body))
            print(f"  {i}. {subject[:60]}...")

        print()

    except Exception as e:
        print(f"✗ Failed to fetch emails: {e}")
        return 1

    # Test with each provider
    providers = ["openai", "anthropic", "ollama"]

    for provider in providers:
        print("=" * 80)
        print(f"TESTING WITH {provider.upper()}")
        print("=" * 80)
        print()

        # Update config for this provider
        config.ai_provider = provider  # type: ignore

        try:
            classifier = create_classifier(config)
            print(f"✓ {provider.capitalize()} classifier created")
            print()

            # Classify each email
            for i, (_msg_id, subject, body) in enumerate(emails, 1):
                print(f"Email {i}:")
                print(f"  Subject: {subject}")
                print(f"  Body Preview: {body[:100]}...")
                print()

                try:
                    result = classifier.classify(subject, body)

                    print("  Classification:")
                    print(f"    Category: {result.category.value}")
                    print(f"    Confidence: {result.confidence:.2f}")
                    print(f"    Provider: {result.provider}")
                    print(f"    Model: {result.model}")
                    if result.reasoning:
                        print(f"    Reasoning: {result.reasoning}")
                    print()

                except Exception as e:
                    print(f"  ✗ Classification failed: {e}")
                    print()
                    continue

        except Exception as e:
            print(f"✗ Failed to create {provider} classifier: {e}")
            print()
            continue

    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
