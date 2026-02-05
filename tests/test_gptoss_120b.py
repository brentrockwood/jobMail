"""
Test gpt-oss:120b model on Ollama with detailed diagnostics.

This script tests the gpt-oss:120b model and provides:
- Detailed response inspection (including empty responses)
- Retry behavior observation
- Performance metrics (latency)
- Comparison with other tested models
"""

import json
import time
from pathlib import Path

from src.classifier import ClassificationCategory, OllamaClassifier
from src.config import Config


def load_email_corpus() -> list[dict]:
    """Load all email fixtures from tests/fixtures/emails/."""
    corpus_dir = Path(__file__).parent / "fixtures" / "emails"
    if not corpus_dir.exists():
        print(f"❌ No email corpus found at {corpus_dir}")
        return []

    emails = []
    for filepath in sorted(corpus_dir.glob("email_*.json")):
        with open(filepath, encoding="utf-8") as f:
            email_data = json.load(f)
            email_data["filename"] = filepath.name
            emails.append(email_data)

    return emails


def test_gptoss_120b():
    """Test gpt-oss:120b with comprehensive diagnostics."""

    # Configuration
    config = Config(
        ai_provider="ollama",
        ollama_base_url="http://ai1.lab:11434/v1",
        ollama_model="gpt-oss:120b",
        # Other required config fields (not used for Ollama)
        openai_api_key=None,
        openai_model="gpt-4",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-5-20250929",
        gemini_api_key=None,
        gemini_model="gemini-2.0-flash",
        gmail_credentials_file=Path("credentials.json"),
        gmail_token_file=Path("token.json"),
        confidence_threshold=0.8,
        batch_size=20,
        label_acknowledged="Acknowledged",
        label_rejected="Rejected",
        label_followup="FollowUp",
        label_jobboard="JobBoard",
        dry_run=True,
        log_level="INFO",
        database_path=Path("jobmail.db"),
    )

    print("🧪 Testing gpt-oss:120b on Ollama")
    print(f"   Base URL: {config.ollama_base_url}")
    print(f"   Model: {config.ollama_model}\n")

    # Load test corpus
    emails = load_email_corpus()
    if not emails:
        print("❌ No emails to test. Run tests/fetch_test_emails.py first.")
        return

    print(f"📧 Loaded {len(emails)} test emails\n")
    print("=" * 80)

    # Initialize classifier
    classifier = OllamaClassifier(config)

    # Track results
    results = []
    empty_responses = []
    errors = []

    # Test each email
    for i, email in enumerate(emails, 1):
        filename = email.get("filename", f"email_{i}")
        subject = email.get("subject", "No subject")
        from_email = email.get("from", "Unknown sender")
        body = email.get("body", "")

        print(f"\n📨 Test {i}/{len(emails)}: {filename}")
        print(f"   Subject: {subject[:60]}...")
        print(f"   From: {from_email}")
        print(f"   Body length: {len(body)} chars")

        # Measure latency
        start_time = time.time()

        try:
            result = classifier.classify(subject, body)
            latency = time.time() - start_time

            # Check for empty/invalid response
            if result.category == ClassificationCategory.UNKNOWN and result.confidence == 0.0:
                print(f"   ⚠️  EMPTY RESPONSE (latency: {latency:.2f}s)")
                empty_responses.append(
                    {"filename": filename, "subject": subject, "latency": latency}
                )
            else:
                print(
                    f"   ✅ {result.category.value} "
                    f"(confidence: {result.confidence:.2f}, "
                    f"latency: {latency:.2f}s)"
                )
                if result.reasoning:
                    print(f"   💭 {result.reasoning[:100]}...")

            results.append(
                {
                    "filename": filename,
                    "subject": subject,
                    "category": result.category.value,
                    "confidence": result.confidence,
                    "latency": latency,
                    "reasoning": result.reasoning,
                    "is_empty": result.category == ClassificationCategory.UNKNOWN
                    and result.confidence == 0.0,
                }
            )

        except Exception as e:
            latency = time.time() - start_time
            print(f"   ❌ ERROR: {e} (latency: {latency:.2f}s)")
            errors.append(
                {"filename": filename, "subject": subject, "error": str(e), "latency": latency}
            )

    # Summary statistics
    print("\n" + "=" * 80)
    print("\n📊 SUMMARY STATISTICS")
    print("=" * 80)

    total_tests = len(emails)
    successful = len(results)
    failed = len(errors)
    empty = len(empty_responses)
    valid = successful - empty

    print(f"\nTotal tests: {total_tests}")
    print(f"Successful: {successful} ({successful / total_tests * 100:.1f}%)")
    print(f"Valid responses: {valid} ({valid / total_tests * 100:.1f}%)")
    print(f"Empty responses: {empty} ({empty / total_tests * 100:.1f}%)")
    print(f"Errors: {failed} ({failed / total_tests * 100:.1f}%)")

    # Latency statistics
    if results:
        latencies = [r["latency"] for r in results]
        print("\n⏱️  LATENCY:")
        print(f"   Average: {sum(latencies) / len(latencies):.2f}s")
        print(f"   Min: {min(latencies):.2f}s")
        print(f"   Max: {max(latencies):.2f}s")

    # Category distribution (valid responses only)
    if valid > 0:
        valid_results = [r for r in results if not r["is_empty"]]
        categories = {}
        confidences = []

        for r in valid_results:
            cat = r["category"]
            categories[cat] = categories.get(cat, 0) + 1
            confidences.append(r["confidence"])

        print("\n📁 CLASSIFICATIONS (valid responses only):")
        for cat, count in sorted(categories.items()):
            print(f"   {cat}: {count}")

        if confidences:
            print("\n📈 CONFIDENCE:")
            print(f"   Average: {sum(confidences) / len(confidences):.2f}")
            print(f"   Min: {min(confidences):.2f}")
            print(f"   Max: {max(confidences):.2f}")

    # Empty response details
    if empty_responses:
        print("\n⚠️  EMPTY RESPONSES DETAIL:")
        for er in empty_responses:
            print(f"   • {er['filename']}: {er['subject'][:60]}... ({er['latency']:.2f}s)")

    # Error details
    if errors:
        print("\n❌ ERRORS DETAIL:")
        for err in errors:
            print(f"   • {err['filename']}: {err['error']}")

    print("\n" + "=" * 80)
    print("\n🔬 ANALYSIS NOTES:")
    print("=" * 80)
    print(
        """
gpt-oss:120b Observations:
- Large model (120B parameters) - expect higher latency than smaller models
- Empty responses indicate potential issues:
  * Model may not follow JSON output format consistently
  * May be more sensitive to prompt structure
  * Could be truncating responses prematurely
  * Possible temperature/sampling issues

Comparison with other tested models:
- mistral:latest (7B) - Fast, consistent, good for production
- llama3.x models (8B-70B) - Had extraction bias issues (fixed with prompt)
- qwen2.5:72b (72B) - Similar extraction issues
- phi3:14b (14B) - Works correctly
- gpt-4 / claude-sonnet-4-5 - Excellent consistency, higher cost
- gemini-2.0-flash - Fast, consistent

Recommendations will follow after reviewing results above.
"""
    )


if __name__ == "__main__":
    test_gptoss_120b()
