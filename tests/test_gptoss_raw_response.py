"""
Raw response diagnostic for gpt-oss:120b.

This script makes direct API calls to see exactly what the model returns,
including empty or malformed responses.
"""

import json
from pathlib import Path

from openai import OpenAI


def load_problematic_emails():
    """Load the three emails that failed."""
    corpus_dir = Path(__file__).parent / "fixtures" / "emails"
    emails = []

    for filename in ["email_008.json", "email_009.json", "email_010.json"]:
        filepath = corpus_dir / filename
        with open(filepath, encoding="utf-8") as f:
            email_data = json.load(f)
            email_data["filename"] = filename
            emails.append(email_data)

    return emails


def test_raw_responses():
    """Test raw API responses from gpt-oss:120b."""

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

    emails = load_problematic_emails()

    print("🔬 RAW RESPONSE DIAGNOSTIC FOR gpt-oss:120b")
    print("=" * 80)

    for email in emails:
        filename = email["filename"]
        subject = email["subject"]
        body = email["body"]

        # Apply same truncation as OllamaClassifier
        truncated_body = body[:1500] + "\n\n[...]\n\n" + body[-500:] if len(body) > 2000 else body

        user_message = f"Subject: {subject}\n\nBody:\n{truncated_body}"

        print(f"\n📨 {filename}")
        print(f"   Subject: {subject}")
        print(f"   Body length: {len(body)} chars (truncated: {len(truncated_body)})")
        print("\n   Making API call...")

        try:
            response = client.chat.completions.create(
                model="gpt-oss:120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )

            # Extract raw content
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            print("   ✅ Response received")
            print(f"   Finish reason: {finish_reason}")
            print(f"   Content length: {len(content) if content else 0} chars")
            print("\n   RAW CONTENT:")
            print("   ---")
            if content:
                print(f"   {repr(content)}")
                print("   ---")

                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    print("   ✅ Valid JSON")
                    print(f"   Parsed: {json.dumps(parsed, indent=2)}")
                except json.JSONDecodeError as je:
                    print(f"   ❌ Invalid JSON: {je}")
            else:
                print("   ❌ EMPTY RESPONSE (content is None or empty string)")
                print("   ---")

            # Full response object inspection
            print("\n   RESPONSE OBJECT DETAILS:")
            print(f"   Model: {response.model}")
            print(f"   Usage: {response.usage}")
            print(f"   Choices count: {len(response.choices)}")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            print(f"   Error type: {type(e).__name__}")

    print("\n" + "=" * 80)
    print("\n💡 DIAGNOSTIC INSIGHTS:")
    print(
        """
1. If content is empty but finish_reason is 'stop':
   - Model completed but produced no output
   - May need different prompt structure
   - May need to remove response_format constraint

2. If content is empty and finish_reason is 'length':
   - max_tokens too small (unlikely at 120)
   - Response truncated before any JSON

3. If content is malformed JSON:
   - Model not respecting response_format
   - May need explicit JSON instruction in prompt
   - May need to increase max_tokens

4. If content is valid but wrong structure:
   - Model interpreting task differently
   - Prompt may need simplification
"""
    )


if __name__ == "__main__":
    test_raw_responses()
