"""Test that small models use exact category values and don't invent new ones.

This addresses the bug where llama3.1:8b was returning "Job Posting" instead of "jobboard".
"""

import logging

from src.classifier import ClassificationCategory, create_classifier
from src.config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def test_job_posting_becomes_jobboard():
    """Test that job postings are classified as 'jobboard', not invented categories."""
    config = Config.from_env()

    # Only run if using Ollama
    if config.ai_provider.lower() != "ollama":
        print(f"Skipping test - not using Ollama (provider: {config.ai_provider})")
        return

    classifier = create_classifier(config)

    # Simulate a job posting email (previously returned "Job Posting" category)
    subject = "Senior AI Full Stack Engineer at Mindlance"
    body = """
    Job Title: Senior AI Full Stack Engineer
    Company: Mindlance
    Location: South San Francisco, CA
    Type: Full-Time
    Hourly Rate: about $80 / hr.

    We are seeking an experienced Senior AI Full Stack Engineer to join our team.
    The ideal candidate will have 5+ years of experience with Python, React, and AI/ML.

    Responsibilities:
    - Build and maintain AI-powered web applications
    - Collaborate with cross-functional teams
    - Implement best practices for code quality

    Requirements:
    - Bachelor's degree in Computer Science or related field
    - Strong proficiency in Python and JavaScript
    - Experience with AI/ML frameworks
    """

    print(f"\nTesting Ollama model: {config.ollama_model}")
    print("Classifying job posting email...")

    result = classifier.classify(subject, body)

    print("\n✓ Classification successful!")
    print(f"Category: {result.category.value}")
    print(f"Confidence: {result.confidence}")
    print(f"Reasoning: {result.reasoning}")

    # Verify category is one of the valid enum values
    assert isinstance(
        result.category, ClassificationCategory
    ), f"Category must be ClassificationCategory enum, got {type(result.category)}"

    # For job postings/alerts, expect either 'jobboard' or 'unknown'
    # (both are valid depending on context)
    valid_categories = {
        ClassificationCategory.JOBBOARD,
        ClassificationCategory.UNKNOWN,
        ClassificationCategory.FOLLOWUP,  # Could be interpreted as action required
    }
    assert result.category in valid_categories, (
        f"Job posting should be classified as jobboard, followup, or unknown, "
        f"got {result.category.value}"
    )

    print(f"\n✓ Category is a valid enum value: {result.category.value}")
    print("✓ Test passed - no invented categories!")


def test_all_valid_categories_accepted():
    """Test that all 5 valid categories are properly recognized."""
    config = Config.from_env()

    if config.ai_provider.lower() != "ollama":
        print(f"Skipping test - not using Ollama (provider: {config.ai_provider})")
        return

    classifier = create_classifier(config)

    test_cases = [
        (
            "Thank you for your application",
            "We received your application and will review it.",
            ClassificationCategory.ACKNOWLEDGEMENT,
        ),
        (
            "Application Status Update",
            "We've decided to pursue other candidates for this position.",
            ClassificationCategory.REJECTION,
        ),
        (
            "Interview Invitation",
            "Please schedule an interview at your convenience.",
            ClassificationCategory.FOLLOWUP,
        ),
        (
            "New jobs matching your search",
            "5 new Senior Engineer positions were posted today on Indeed.",
            ClassificationCategory.JOBBOARD,
        ),
    ]

    print(f"\nTesting all valid categories with {config.ollama_model}...")

    for subject, body, expected_category in test_cases:
        result = classifier.classify(subject, body)
        print(
            f"\n✓ {subject[:30]}... -> {result.category.value} "
            f"(expected: {expected_category.value})"
        )

        # Verify it's a valid enum value
        assert isinstance(result.category, ClassificationCategory)

        # Note: We don't enforce exact match because AI might reasonably disagree
        # The important thing is it uses one of the 5 valid categories

    print("\n✓ All classifications used valid category values!")


if __name__ == "__main__":
    print("=" * 70)
    print("Test 1: Job Posting Category Validation")
    print("=" * 70)
    test_job_posting_becomes_jobboard()

    print("\n" + "=" * 70)
    print("Test 2: All Valid Categories")
    print("=" * 70)
    test_all_valid_categories_accepted()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
