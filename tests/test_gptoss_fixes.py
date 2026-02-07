"""
Test different configurations to fix gpt-oss:120b empty response issue.

Issue identified: finish_reason='length' with 120 max_tokens causes empty responses
"""

import json
from pathlib import Path

from openai import OpenAI


def load_email_010():
    """Load the problematic email."""
    corpus_dir = Path(__file__).parent / "fixtures" / "emails"
    filepath = corpus_dir / "email_010.json"

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def test_configurations():
    """Test different API configurations."""

    client = OpenAI(
        base_url="http://ai1.lab:11434/v1",
        api_key="ollama",
    )

    system_prompt = """Classify the email TYPE. Output this JSON:
{"category": "X", "confidence": 0.0-1.0, "reasoning": "brief"}

category must be ONE of: acknowledgement, rejection, followup_required, jobboard, unknown

How to classify:
- Multiple job listings (>1 job) = jobboard
- "We received your application" = acknowledgement
- "We're not moving forward" / "position filled" = rejection
- "Please schedule" / "complete assessment" = followup_required
- Spam/unclear = unknown

Examples:
Subject: "New jobs for you" → jobboard
Subject: "Application received" → acknowledgement
Subject: "Interview request" → followup_required
Subject: "Application status" + body has "other candidates" → rejection

Output ONLY the JSON. Do NOT extract job details."""

    email = load_email_010()
    subject = email["subject"]
    body = email["body"]

    # Apply truncation
    truncated_body = body[:1500] + "\n\n[...]\n\n" + body[-500:] if len(body) > 2000 else body

    user_message = f"Subject: {subject}\n\nBody:\n{truncated_body}"

    print("🧪 TESTING DIFFERENT CONFIGURATIONS")
    print("=" * 80)
    print("\n📨 Test Email: email_010.json")
    print(f"   Subject: {subject}")
    print(f"   Body length: {len(body)} chars")
    print("\n" + "=" * 80)

    configs = [
        {
            "name": "Current config (baseline)",
            "params": {
                "temperature": 0.0,
                "max_tokens": 120,
                "response_format": {"type": "json_object"},
            },
        },
        {
            "name": "Increased max_tokens to 200",
            "params": {
                "temperature": 0.0,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            },
        },
        {
            "name": "Increased max_tokens to 300",
            "params": {
                "temperature": 0.0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
        },
        {
            "name": "No response_format constraint (max_tokens=120)",
            "params": {
                "temperature": 0.0,
                "max_tokens": 120,
            },
        },
        {
            "name": "No response_format + max_tokens=200",
            "params": {
                "temperature": 0.0,
                "max_tokens": 200,
            },
        },
    ]

    for i, config in enumerate(configs, 1):
        print(f"\n🔬 Test {i}: {config['name']}")
        print(f"   Parameters: {config['params']}")
        print("   Making API call...")

        try:
            response = client.chat.completions.create(
                model="gpt-oss:120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                **config["params"],
            )

            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            print(f"   Finish reason: {finish_reason}")
            print(f"   Content length: {len(content) if content else 0} chars")

            if content:
                print("   ✅ Response received")
                # Try to parse
                try:
                    parsed = json.loads(content)
                    print("   ✅ Valid JSON")
                    print(f"   Category: {parsed.get('category', 'MISSING')}")
                    print(f"   Confidence: {parsed.get('confidence', 'MISSING')}")
                except json.JSONDecodeError:
                    print("   ⚠️  Invalid JSON")
                    print(f"   Raw: {content[:100]}...")
            else:
                print("   ❌ Empty response")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 80)
    print("\n📊 CONCLUSION:")
    print(
        """
Based on the test results above, we can determine:
1. Whether max_tokens increase fixes empty responses
2. Whether response_format constraint causes the issue
3. The minimum safe max_tokens value for this model
4. Whether the model can follow JSON format without response_format
"""
    )


if __name__ == "__main__":
    test_configurations()
