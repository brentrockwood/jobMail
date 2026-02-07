"""Test that Ollama correctly returns JSON with response_format parameter.

This test validates the fix for smaller models that were returning incorrect JSON
(extracting job details instead of classifying emails).
"""

import logging

from src.classifier import create_classifier
from src.config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def test_ollama_json_mode():
    """Test Ollama with small model returns valid JSON."""
    config = Config.from_env()

    # Only run if using Ollama
    if config.ai_provider.lower() != "ollama":
        print(f"Skipping test - not using Ollama (provider: {config.ai_provider})")
        return

    classifier = create_classifier(config)

    # Test with a simple job board notification
    subject = "New jobs matching your search"
    body = """
    Hi there,

    We found 5 new Senior Software Engineer positions that match your search criteria:

    1. Senior Full Stack Engineer at TechCorp
    2. Senior Backend Developer at StartupXYZ
    3. Lead Software Engineer at BigCompany

    Click here to view these opportunities!

    Best regards,
    The Job Board Team
    """

    print(f"\nTesting Ollama model: {config.ollama_model}")
    print(f"Base URL: {config.ollama_base_url}")
    print("\nClassifying email...")
    print(f"Subject: {subject}")

    result = classifier.classify(subject, body)

    print("\n✓ Classification successful!")
    print(f"Category: {result.category.value}")
    print(f"Confidence: {result.confidence}")
    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Reasoning: {result.reasoning}")

    # Verify we got valid structured data
    assert result.category is not None
    assert 0.0 <= result.confidence <= 1.0
    assert result.provider == "ollama"
    assert result.model == config.ollama_model

    print("\n✓ All assertions passed!")


if __name__ == "__main__":
    test_ollama_json_mode()
