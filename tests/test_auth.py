"""Quick test of Gmail authentication."""

import sys
from pathlib import Path

from src.config import Config, setup_logging
from src.gmail_client import GmailClient


def main() -> int:
    """Test Gmail authentication."""
    setup_logging("INFO")
    print("Testing Gmail authentication...\n")

    # Load config
    config = Config.from_env()
    print(f"✓ Config loaded")
    print(f"  Credentials file: {config.gmail_credentials_file}")
    print(f"  Token file: {config.gmail_token_file}")

    # Check credentials file exists
    if not config.gmail_credentials_file.exists():
        print(f"\n✗ Credentials file not found: {config.gmail_credentials_file}")
        return 1

    print(f"✓ Credentials file found\n")

    # Create Gmail client
    client = GmailClient(config.gmail_credentials_file, config.gmail_token_file)

    # Authenticate (will open browser on first run)
    print("Attempting authentication...")
    print("(Browser will open for authorization on first run)\n")
    try:
        client.authenticate()
        print("✓ Authentication successful!\n")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return 1

    # Test basic API call - list labels
    print("Testing API call - listing Gmail labels...")
    try:
        labels = client.list_labels()
        print(f"✓ API call successful!")
        print(f"  Found {len(labels)} labels in your Gmail account\n")

        # Show first few labels
        print("Sample labels:")
        for label in labels[:5]:
            print(f"  - {label['name']} (id: {label['id']})")
        if len(labels) > 5:
            print(f"  ... and {len(labels) - 5} more")

        print("\n✓ All tests passed!")
        print(f"  Token saved to: {config.gmail_token_file}")
        print("  Future runs will use this token (no browser needed)")
        return 0

    except Exception as e:
        print(f"✗ API call failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
