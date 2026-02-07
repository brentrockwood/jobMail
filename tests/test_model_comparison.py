"""Test different Ollama models to find one that works for classification."""

import logging

from src.classifier import create_classifier
from src.config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


# Test email with multiple job listings (the problematic case)
TEST_SUBJECT = "New jobs matching your preferences"
TEST_BODY = """
Hi there,

We found several new positions matching your search:

1. Senior DevOps Engineer at INHABIT IQ INC - Alpharetta, GA
   Build and optimize containerized workloads on Kubernetes.
   Salary: $120,000 - $160,000/year

2. Application Architect at Computer Task Group - Remote
   Quality Engineering focus, lead technical initiatives.
   Salary: $90,000 - $110,000/year

3. Technical Integrations Consultant at Professional Employment Group - Remote
   Work with enterprise clients on system integrations.
   Salary: $90,000 - $150,000/year

Click here to view all opportunities and apply!

Best regards,
The Jobs Team
"""


def test_model(model_name: str) -> dict:
    """Test a specific model and return results."""
    print(f"\n{'=' * 70}")
    print(f"Testing: {model_name}")
    print(f"{'=' * 70}")

    # Create config with this model
    from pathlib import Path

    config = Config(
        ai_provider="ollama",
        ollama_base_url="http://ai1.lab:11434/v1",
        ollama_model=model_name,
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        openai_model="gpt-4",
        anthropic_model="claude-sonnet-4-5-20250929",
        gemini_model="gemini-2.0-flash-exp",
        gmail_credentials_file=Path("credentials.json"),
        gmail_token_file=Path("token.json"),
        label_acknowledged="Acknowledged",
        label_rejected="Rejected",
        label_followup="FollowUp",
        label_jobboard="JobBoard",
        confidence_threshold=0.8,
        batch_size=10,
        dry_run=False,
        log_level="INFO",
        database_path=Path("test_jobmail.db"),
    )

    try:
        classifier = create_classifier(config)
        result = classifier.classify(TEST_SUBJECT, TEST_BODY)

        print("✓ SUCCESS!")
        print(f"  Category: {result.category.value}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Reasoning: {result.reasoning}")

        # Check if it's correct (should be jobboard)
        is_correct = result.category.value == "jobboard"
        print(f"  Correct: {'✓ YES' if is_correct else '✗ NO (expected jobboard)'}")

        return {
            "model": model_name,
            "status": "success",
            "category": result.category.value,
            "confidence": result.confidence,
            "correct": is_correct,
            "reasoning": result.reasoning,
        }

    except Exception as e:
        error_msg = str(e)
        print("✗ FAILED!")
        print(f"  Error: {error_msg[:200]}")

        # Check if it's extraction behavior
        if "Missing required fields" in error_msg or "Unterminated string" in error_msg:
            behavior = "job_extraction"
            print("  Behavior: Job extraction detected")
        else:
            behavior = "other_error"

        return {
            "model": model_name,
            "status": "failed",
            "error": error_msg[:200],
            "behavior": behavior,
        }


def main():
    """Test all models."""
    models = [
        "mistral:latest",
        "phi3:14b",
        "llama3.2:3b-instruct-fp16",
        "gemma2:9b-instruct-q8_0",
    ]

    print("=" * 70)
    print("MODEL COMPARISON TEST")
    print("=" * 70)
    print("Test case: Job board email with 3 job listings")
    print("Expected: category='jobboard'")
    print()

    results = []
    for model in models:
        try:
            result = test_model(model)
            results.append(result)
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            break
        except Exception as e:
            print(f"\n✗ Unexpected error testing {model}: {e}")
            results.append({"model": model, "status": "error", "error": str(e)[:200]})

    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    success_count = sum(1 for r in results if r.get("status") == "success")
    correct_count = sum(1 for r in results if r.get("status") == "success" and r.get("correct"))

    for result in results:
        model = result["model"]
        status = result.get("status")

        if status == "success":
            correct = "✓" if result.get("correct") else "✗"
            print(
                f"{correct} {model:35} → {result['category']:20} "
                f"(confidence: {result['confidence']:.2f})"
            )
        else:
            behavior = result.get("behavior", "unknown")
            print(f"✗ {model:35} → FAILED ({behavior})")

    print()
    print(f"Success rate: {success_count}/{len(results)}")
    print(f"Correct classifications: {correct_count}/{len(results)}")

    if correct_count > 0:
        print("\n✓ WORKING MODELS FOUND!")
        for r in results:
            if r.get("status") == "success" and r.get("correct"):
                print(f"  - {r['model']}")
    else:
        print("\n✗ No working models found. All attempted job extraction.")


if __name__ == "__main__":
    main()
