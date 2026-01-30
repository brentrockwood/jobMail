"""Test Gemini classifier with real API."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.classifier import ClassificationCategory, GeminiClassifier
from src.config import Config


def test_gemini_real():
    """Test Gemini with real API key."""

    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        print("ERROR: GEMINI_API_KEY environment variable not set or still using placeholder")
        print("Please set GEMINI_API_KEY environment variable:")
        print("  export GEMINI_API_KEY=your-actual-api-key")
        print("Or add it to secrets.env:")
        print("  echo 'GEMINI_API_KEY=your-actual-api-key' >> secrets.env")
        sys.exit(1)

    # Create config with Gemini settings
    config = Config.from_env()
    config.ai_provider = "gemini"
    config.gemini_api_key = api_key
    config.gemini_model = "gemini-2.0-flash-exp"

    print(f"Testing Gemini classifier with model: {config.gemini_model}")
    print(f"API key: {api_key[:10]}...{api_key[-4:]}")
    print()

    # Create classifier
    classifier = GeminiClassifier(config)

    # Test cases
    test_cases = [
        {
            "subject": "Application Received - Software Engineer",
            "body": (
                "Thank you for applying to our Software Engineer position. "
                "We have received your application and will review it shortly."
            ),
            "expected": ClassificationCategory.ACKNOWLEDGEMENT,
        },
        {
            "subject": "New jobs matching your search",
            "body": (
                "We found 10 new Software Engineer jobs that match your criteria. View them now!"
            ),
            "expected": ClassificationCategory.JOBBOARD,
        },
        {
            "subject": "Interview Scheduling",
            "body": (
                "Thank you for your interest. Are you available for an "
                "interview next Tuesday at 2pm?"
            ),
            "expected": ClassificationCategory.FOLLOWUP,
        },
        {
            "subject": "Application Update",
            "body": (
                "Thank you for your interest in our company. After careful "
                "consideration, we have decided to move forward with other "
                "candidates."
            ),
            "expected": ClassificationCategory.REJECTION,
        },
    ]

    print("Running test classifications:")
    print("=" * 80)

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Subject: {test['subject']}")
        print(f"Body: {test['body'][:60]}...")
        print(f"Expected: {test['expected'].value}")

        try:
            result = classifier.classify(test["subject"], test["body"])

            print(f"Result: {result.category.value}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Provider: {result.provider}")
            print(f"Model: {result.model}")
            print(f"Reasoning: {result.reasoning}")

            if result.category == test["expected"]:
                print("✓ PASS")
            else:
                print(f"✗ FAIL - Expected {test['expected'].value}, got {result.category.value}")
                all_passed = False

        except Exception as e:
            print(f"✗ ERROR: {e}")
            all_passed = False

        print("-" * 80)

    print()
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(test_gemini_real())
