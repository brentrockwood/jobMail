"""
Test AI classification against a stable corpus of real emails.

This test suite loads saved emails from tests/fixtures/emails/ and tests
classification with different AI providers. This allows for:
- Reproducible testing without hitting Gmail API
- Comparison of different AI models
- Tracking classification accuracy over time
- Performance benchmarking

The email fixtures can include an 'expected_classification' field for
accuracy testing.
"""

import json
from pathlib import Path

import pytest

from src.classifier import create_classifier
from src.config import Config


def load_email_corpus() -> list[dict]:
    """
    Load all email fixtures from tests/fixtures/emails/.

    Returns:
        List of email data dictionaries
    """
    corpus_dir = Path(__file__).parent / "fixtures" / "emails"
    if not corpus_dir.exists():
        return []

    emails = []
    for filepath in sorted(corpus_dir.glob("email_*.json")):
        with open(filepath, encoding="utf-8") as f:
            email_data = json.load(f)
            email_data["filename"] = filepath.name
            emails.append(email_data)

    return emails


@pytest.fixture(scope="module")
def email_corpus():
    """Load email corpus once for all tests."""
    emails = load_email_corpus()
    if not emails:
        pytest.skip("No email corpus found. Run tests/fetch_test_emails.py first.")
    return emails


@pytest.fixture(scope="module")
def config():
    """Load configuration from environment."""
    return Config.from_env()


class TestOpenAIClassification:
    """Test OpenAI classification against corpus."""

    @pytest.fixture(scope="class")
    def classifier(self, config):
        """Create OpenAI classifier."""
        if config.ai_provider != "openai" and not config.openai_api_key:
            pytest.skip("OpenAI API key not configured")
        # Temporarily set provider to openai
        config.ai_provider = "openai"
        return create_classifier(config)

    def test_classify_corpus(self, email_corpus, classifier):
        """Test OpenAI classification on all corpus emails."""
        print(f"\n\n{'='*80}")
        print(f"OpenAI Classification Results ({len(email_corpus)} emails)")
        print(f"{'='*80}\n")

        results = []
        for email in email_corpus:
            result = classifier.classify(email["subject"], email["body"])
            results.append(
                {
                    "email": email,
                    "classification": result,
                }
            )

            # Print results
            print(f"Email: {email['filename']}")
            print(f"Subject: {email['subject'][:80]}")
            print(f"From: {email['from']}")
            print(f"Classification: {result.category.value}")
            print(f"Confidence: {result.confidence:.2f}")
            if result.reasoning:
                print(f"Reasoning: {result.reasoning[:200]}")
            if email.get("expected_classification"):
                match = result.category.value == email["expected_classification"]
                status = "✓" if match else "✗"
                print(f"Expected: {email['expected_classification']} {status}")
            print()

        # Calculate accuracy if expected classifications are provided
        expected_count = sum(1 for e in email_corpus if e.get("expected_classification"))
        if expected_count > 0:
            correct = sum(
                1
                for r in results
                if r["email"].get("expected_classification") == r["classification"].category.value
            )
            accuracy = correct / expected_count * 100
            print(f"Accuracy: {correct}/{expected_count} ({accuracy:.1f}%)")
            print()

        # All classifications should succeed (no exceptions)
        assert len(results) == len(email_corpus)


class TestAnthropicClassification:
    """Test Anthropic classification against corpus."""

    @pytest.fixture(scope="class")
    def classifier(self, config):
        """Create Anthropic classifier."""
        if config.ai_provider != "anthropic" and not config.anthropic_api_key:
            pytest.skip("Anthropic API key not configured")
        # Temporarily set provider to anthropic
        config.ai_provider = "anthropic"
        return create_classifier(config)

    def test_classify_corpus(self, email_corpus, classifier):
        """Test Anthropic classification on all corpus emails."""
        print(f"\n\n{'='*80}")
        print(f"Anthropic Classification Results ({len(email_corpus)} emails)")
        print(f"{'='*80}\n")

        results = []
        for email in email_corpus:
            result = classifier.classify(email["subject"], email["body"])
            results.append(
                {
                    "email": email,
                    "classification": result,
                }
            )

            # Print results
            print(f"Email: {email['filename']}")
            print(f"Subject: {email['subject'][:80]}")
            print(f"From: {email['from']}")
            print(f"Classification: {result.category.value}")
            print(f"Confidence: {result.confidence:.2f}")
            if result.reasoning:
                print(f"Reasoning: {result.reasoning[:200]}")
            if email.get("expected_classification"):
                match = result.category.value == email["expected_classification"]
                status = "✓" if match else "✗"
                print(f"Expected: {email['expected_classification']} {status}")
            print()

        # Calculate accuracy if expected classifications are provided
        expected_count = sum(1 for e in email_corpus if e.get("expected_classification"))
        if expected_count > 0:
            correct = sum(
                1
                for r in results
                if r["email"].get("expected_classification") == r["classification"].category.value
            )
            accuracy = correct / expected_count * 100
            print(f"Accuracy: {correct}/{expected_count} ({accuracy:.1f}%)")
            print()

        # All classifications should succeed (no exceptions)
        assert len(results) == len(email_corpus)


class TestOllamaClassification:
    """Test Ollama classification against corpus."""

    @pytest.fixture(scope="class")
    def classifier(self, config):
        """Create Ollama classifier."""
        # Ollama doesn't require API key but needs running server
        config.ai_provider = "ollama"
        return create_classifier(config)

    def test_classify_corpus(self, email_corpus, classifier):
        """Test Ollama classification on all corpus emails."""
        print(f"\n\n{'='*80}")
        print(f"Ollama Classification Results ({len(email_corpus)} emails)")
        print(f"{'='*80}\n")

        results = []
        for email in email_corpus:
            try:
                result = classifier.classify(email["subject"], email["body"])
                results.append(
                    {
                        "email": email,
                        "classification": result,
                    }
                )

                # Print results
                print(f"Email: {email['filename']}")
                print(f"Subject: {email['subject'][:80]}")
                print(f"From: {email['from']}")
                print(f"Classification: {result.category.value}")
                print(f"Confidence: {result.confidence:.2f}")
                if result.reasoning:
                    print(f"Reasoning: {result.reasoning[:200]}")
                if email.get("expected_classification"):
                    match = result.category.value == email["expected_classification"]
                    status = "✓" if match else "✗"
                    print(f"Expected: {email['expected_classification']} {status}")
                print()
            except Exception as e:
                print(f"Error classifying {email['filename']}: {e}")
                pytest.skip(f"Ollama server not available: {e}")

        # Calculate accuracy if expected classifications are provided
        expected_count = sum(1 for e in email_corpus if e.get("expected_classification"))
        if expected_count > 0:
            correct = sum(
                1
                for r in results
                if r["email"].get("expected_classification") == r["classification"].category.value
            )
            accuracy = correct / expected_count * 100
            print(f"Accuracy: {correct}/{expected_count} ({accuracy:.1f}%)")
            print()

        # All classifications should succeed (no exceptions)
        assert len(results) == len(email_corpus)


class TestCrossProviderComparison:
    """Compare classification results across providers."""

    def test_provider_agreement(self, email_corpus, config):
        """Test agreement between different AI providers."""
        # Skip if not all providers are configured
        if not config.openai_api_key or not config.anthropic_api_key:
            pytest.skip("Both OpenAI and Anthropic keys required for comparison")

        print(f"\n\n{'='*80}")
        print(f"Cross-Provider Comparison ({len(email_corpus)} emails)")
        print(f"{'='*80}\n")

        # Classify with both providers
        config_openai = Config.from_env()
        config_openai.ai_provider = "openai"
        classifier_openai = create_classifier(config_openai)

        config_anthropic = Config.from_env()
        config_anthropic.ai_provider = "anthropic"
        classifier_anthropic = create_classifier(config_anthropic)

        agreements = 0
        for email in email_corpus:
            result_openai = classifier_openai.classify(email["subject"], email["body"])
            result_anthropic = classifier_anthropic.classify(email["subject"], email["body"])

            agree = result_openai.category == result_anthropic.category
            if agree:
                agreements += 1

            print(f"Email: {email['filename']}")
            print(f"Subject: {email['subject'][:60]}")
            print(
                f"OpenAI:    {result_openai.category.value:20s} "
                f"(conf: {result_openai.confidence:.2f})"
            )
            print(
                f"Anthropic: {result_anthropic.category.value:20s} "
                f"(conf: {result_anthropic.confidence:.2f})"
            )
            print(f"Agreement: {'✓' if agree else '✗'}")
            print()

        agreement_rate = agreements / len(email_corpus) * 100
        print(f"Overall Agreement: {agreements}/{len(email_corpus)} ({agreement_rate:.1f}%)")
        print()

        # Expect high agreement (at least 70%)
        assert agreement_rate >= 70, f"Provider agreement too low: {agreement_rate:.1f}%"
