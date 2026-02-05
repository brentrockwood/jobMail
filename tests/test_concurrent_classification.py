"""
Test concurrent classification requests to measure throughput improvements.

This script tests parallel classification with configurable concurrency levels
to determine optimal parallelism for batch processing.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.classifier import create_classifier
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


def classify_email(classifier, email: dict, email_idx: int) -> dict:
    """Classify a single email and return results with timing."""
    filename = email.get("filename", f"email_{email_idx}")
    subject = email.get("subject", "No subject")
    body = email.get("body", "")

    start_time = time.time()
    try:
        result = classifier.classify(subject, body)
        latency = time.time() - start_time

        return {
            "filename": filename,
            "subject": subject[:60],
            "success": True,
            "category": result.category.value,
            "confidence": result.confidence,
            "latency": latency,
            "error": None,
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "filename": filename,
            "subject": subject[:60],
            "success": False,
            "category": None,
            "confidence": None,
            "latency": latency,
            "error": str(e),
        }


def test_sequential(config: Config, emails: list[dict]) -> dict:
    """Test sequential classification (baseline)."""
    print("\n" + "=" * 80)
    print("🔄 SEQUENTIAL PROCESSING (Baseline)")
    print("=" * 80)

    classifier = create_classifier(config)
    results = []

    start_time = time.time()
    for i, email in enumerate(emails, 1):
        print(f"Processing {i}/{len(emails)}: {email['filename']}", end=" ... ")
        result = classify_email(classifier, email, i)
        results.append(result)
        if result["success"]:
            print(f"✅ {result['category']} ({result['latency']:.2f}s)")
        else:
            print(f"❌ Error ({result['latency']:.2f}s)")

    total_time = time.time() - start_time

    return {
        "mode": "sequential",
        "concurrency": 1,
        "results": results,
        "total_time": total_time,
    }


def test_concurrent(config: Config, emails: list[dict], max_workers: int) -> dict:
    """Test concurrent classification with specified worker count."""
    print("\n" + "=" * 80)
    print(f"⚡ CONCURRENT PROCESSING ({max_workers} workers)")
    print("=" * 80)

    classifier = create_classifier(config)
    results = []

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_email = {
            executor.submit(classify_email, classifier, email, i): email
            for i, email in enumerate(emails, 1)
        }

        # Process as they complete
        for future in as_completed(future_to_email):
            future_to_email[future]
            result = future.result()
            results.append(result)

            if result["success"]:
                print(f"✅ {result['filename']}: {result['category']} ({result['latency']:.2f}s)")
            else:
                print(f"❌ {result['filename']}: Error ({result['latency']:.2f}s)")

    total_time = time.time() - start_time

    # Sort results by filename for consistent comparison
    results.sort(key=lambda x: x["filename"])

    return {
        "mode": "concurrent",
        "concurrency": max_workers,
        "results": results,
        "total_time": total_time,
    }


def print_summary(test_result: dict):
    """Print summary statistics for a test run."""
    mode = test_result["mode"]
    concurrency = test_result["concurrency"]
    results = test_result["results"]
    total_time = test_result["total_time"]

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\n📊 SUMMARY - {mode.upper()} (concurrency={concurrency})")
    print("-" * 80)
    print(f"Total emails: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Avg time per email: {total_time / len(results):.2f}s")

    if successful:
        latencies = [r["latency"] for r in successful]
        print("\nIndividual latencies:")
        print(f"  Average: {sum(latencies) / len(latencies):.2f}s")
        print(f"  Min: {min(latencies):.2f}s")
        print(f"  Max: {max(latencies):.2f}s")

        categories = {}
        for r in successful:
            cat = r["category"]
            categories[cat] = categories.get(cat, 0) + 1

        print("\nClassifications:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")


def compare_results(baseline: dict, test_results: list[dict]):
    """Compare test results and show performance improvements."""
    print("\n" + "=" * 80)
    print("📈 PERFORMANCE COMPARISON")
    print("=" * 80)

    baseline_time = baseline["total_time"]
    baseline["concurrency"]

    print(f"\nBaseline (sequential): {baseline_time:.2f}s")
    print("-" * 80)

    for test in test_results:
        concurrency = test["concurrency"]
        total_time = test["total_time"]
        speedup = baseline_time / total_time
        efficiency = (speedup / concurrency) * 100

        print(f"\nConcurrency {concurrency}:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Speedup: {speedup:.2f}x")
        print(f"  Efficiency: {efficiency:.1f}%")
        print(f"  Time saved: {baseline_time - total_time:.2f}s")

        # Check if results match baseline
        baseline_cats = sorted([r["category"] for r in baseline["results"] if r["success"]])
        test_cats = sorted([r["category"] for r in test["results"] if r["success"]])

        if baseline_cats == test_cats:
            print("  ✅ Results match baseline")
        else:
            print("  ⚠️  Results differ from baseline")


def main():
    """Run concurrent classification tests."""
    # Configuration
    config = Config(
        ai_provider="ollama",
        ollama_base_url="http://ai1.lab:11434/v1",
        # ollama_model="gpt-oss:120b",
        ollama_model="mistral:latest",
        # Other required config fields
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

    print("🧪 CONCURRENT CLASSIFICATION TEST")
    print("=" * 80)
    print(f"Model: {config.ollama_model}")
    print(f"Base URL: {config.ollama_base_url}")

    # Load test corpus
    emails = load_email_corpus()
    if not emails:
        print("❌ No emails to test. Run tests/fetch_test_emails.py first.")
        return

    print(f"Emails loaded: {len(emails)}")

    # Determine test configuration based on model
    if "mistral" in config.ollama_model.lower():
        worker_counts = [2, 4, 8, 16]
        # Replicate corpus to have enough emails for high concurrency testing
        target_emails = 32  # 2x the max workers for good saturation
        if len(emails) < target_emails:
            reps = (target_emails // len(emails)) + 1
            emails = emails * reps
            emails = emails[:target_emails]
            print(f"Replicated corpus to {len(emails)} emails for high concurrency testing")
    else:
        worker_counts = [2, 3, 4]

    # Test sequential (baseline)
    baseline = test_sequential(config, emails)
    print_summary(baseline)

    test_results = []
    for workers in worker_counts:
        result = test_concurrent(config, emails, max_workers=workers)
        print_summary(result)
        test_results.append(result)

    # Compare all results
    compare_results(baseline, test_results)

    # Recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)

    if test_results:
        best_result = max(test_results, key=lambda x: baseline["total_time"] / x["total_time"])
        best_concurrency = best_result["concurrency"]
        best_speedup = baseline["total_time"] / best_result["total_time"]

        print(
            f"""
Best configuration: {best_concurrency} concurrent workers
- Speedup: {best_speedup:.2f}x faster than sequential
- Total time: {best_result["total_time"]:.2f}s vs {baseline["total_time"]:.2f}s
- Time saved: {baseline["total_time"] - best_result["total_time"]:.2f}s

For processing 1000 emails:
- Sequential: ~{(baseline["total_time"] / len(emails)) * 1000:.0f}s ({(baseline["total_time"] / len(emails)) * 1000 / 60:.1f} minutes)
- Concurrent ({best_concurrency}): ~{(best_result["total_time"] / len(emails)) * 1000:.0f}s ({(best_result["total_time"] / len(emails)) * 1000 / 60:.1f} minutes)
- Savings: {((baseline["total_time"] - best_result["total_time"]) / len(emails)) * 1000 / 60:.1f} minutes

Note: Optimal concurrency depends on:
- Server CPU/GPU resources
- Model size and memory requirements
- API rate limits (for cloud providers)
- Network bandwidth (for remote servers)
"""
        )


if __name__ == "__main__":
    main()
