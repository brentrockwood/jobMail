"""AI-powered email classification for job application emails."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import anthropic
from openai import OpenAI

from src.config import Config

logger = logging.getLogger(__name__)


class ClassificationCategory(str, Enum):
    """Email classification categories."""

    ACKNOWLEDGEMENT = "acknowledgement"
    REJECTION = "rejection"
    FOLLOWUP = "followup_required"
    JOBBOARD = "jobboard"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of email classification."""

    category: ClassificationCategory
    confidence: float
    provider: str
    model: str
    reasoning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "category": self.category.value,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
            "reasoning": self.reasoning,
        }


# System message - sets context once, sent with every request
SYSTEM_MESSAGE = """Classify email type. Output ONLY this JSON (no other text):
{"category": "X", "confidence": Y, "reasoning": "Z"}

category must be ONE of: acknowledgement, rejection, followup_required, jobboard, unknown

Key distinctions:
- acknowledgement: About YOUR specific application (received, sent to, viewed, thanks)
- jobboard: Multiple job listings or job alerts
- followup_required: Action needed from you (schedule, complete, respond)
- rejection: Application declined or position filled
- unknown: Spam or unclear

Examples:
"We received your application" → {"category": "acknowledgement", "confidence": 0.95,
"reasoning": "received"}
"Your application was sent to hiring manager" → {"category": "acknowledgement",
"confidence": 0.95, "reasoning": "sent notification"}
"Your application was viewed" → {"category": "acknowledgement", "confidence": 0.95,
"reasoning": "viewed notification"}
"Thanks for applying to this position" → {"category": "acknowledgement", "confidence": 0.95,
"reasoning": "application confirmation"}
"We're moving forward with other candidates" → {"category": "rejection",
"confidence": 0.95, "reasoning": "declined"}
"Schedule your interview here" → {"category": "followup_required",
"confidence": 0.95, "reasoning": "action needed"}
"5 new jobs: Engineer at Google, Dev at Amazon" → {"category": "jobboard",
"confidence": 0.95, "reasoning": "job alert"}
"Buy cheap watches" → {"category": "unknown", "confidence": 0.90,
"reasoning": "spam"}

Do NOT extract job details. Do NOT list jobs. Output ONLY the classification JSON."""

# User message template - ultra minimal
USER_MESSAGE_TEMPLATE = """Subject: {subject}
Body: {body}

Output JSON only:"""


class EmailClassifier(ABC):
    """Abstract base class for email classifiers."""

    def __init__(self, config: Config) -> None:
        """Initialize classifier with config."""
        self.config = config

    @abstractmethod
    def classify(self, subject: str, body: str) -> ClassificationResult:
        """
        Classify an email.

        Args:
            subject: Email subject line
            body: Email body text

        Returns:
            ClassificationResult with category, confidence, and metadata

        Raises:
            Exception: If classification fails
        """
        pass

    def _parse_classification_response(
        self, response_text: str, provider: str, model: str
    ) -> ClassificationResult:
        """
        Parse JSON response from AI provider.

        Args:
            response_text: Raw response text from AI
            provider: Provider name (openai, anthropic, ollama)
            model: Model name

        Returns:
            ClassificationResult

        Raises:
            ValueError: If response is invalid
        """
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)

            # Validate required fields - category is required, confidence is optional
            if "category" not in data:
                raise ValueError(f"Missing required 'category' field in response: {data}")

            # Validate category
            try:
                category = ClassificationCategory(data["category"])
            except ValueError:
                logger.warning(f"Invalid category '{data['category']}', defaulting to unknown")
                category = ClassificationCategory.UNKNOWN

            # Validate confidence (default to config threshold if missing)
            if "confidence" not in data:
                default_confidence = self.config.confidence_threshold
                logger.warning(
                    f"Missing confidence in response from {provider}, "
                    f"defaulting to configured threshold: {default_confidence}"
                )
                confidence = default_confidence
            else:
                confidence = float(data["confidence"])
                if not 0.0 <= confidence <= 1.0:
                    logger.warning(f"Confidence {confidence} out of range, clamping to [0,1]")
                    confidence = max(0.0, min(1.0, confidence))

            return ClassificationResult(
                category=category,
                confidence=confidence,
                provider=provider,
                model=model,
                reasoning=data.get("reasoning"),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {response_text}")
            raise ValueError(f"Invalid JSON response from {provider}: {e}") from e
        except Exception as e:
            logger.error(f"Error parsing classification response: {e}")
            raise


class OpenAIClassifier(EmailClassifier):
    """OpenAI-based email classifier."""

    def __init__(self, config: Config) -> None:
        """Initialize OpenAI classifier."""
        super().__init__(config)
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = config.openai_model

    def classify(self, subject: str, body: str) -> ClassificationResult:
        """Classify email using OpenAI (SDK has built-in retry logic)."""
        user_message = USER_MESSAGE_TEMPLATE.format(subject=subject, body=body)

        logger.debug(f"Classifying with OpenAI model: {self.model}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,  # Deterministic output
                max_tokens=500,
                response_format={"type": "json_object"},  # Force JSON output
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")

            return self._parse_classification_response(content, "openai", self.model)

        except Exception as e:
            logger.error(f"OpenAI classification failed: {e}")
            raise


class AnthropicClassifier(EmailClassifier):
    """Anthropic (Claude) based email classifier."""

    def __init__(self, config: Config) -> None:
        """Initialize Anthropic classifier."""
        super().__init__(config)
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = config.anthropic_model

    def classify(self, subject: str, body: str) -> ClassificationResult:
        """Classify email using Anthropic Claude (SDK has built-in retry logic)."""
        user_message = USER_MESSAGE_TEMPLATE.format(subject=subject, body=body)

        logger.debug(f"Classifying with Anthropic model: {self.model}")
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.0,  # Deterministic output
                system=SYSTEM_MESSAGE,
                messages=[{"role": "user", "content": user_message}],
            )

            content = response.content[0].text
            if not content:
                raise ValueError("Empty response from Anthropic")

            return self._parse_classification_response(content, "anthropic", self.model)

        except Exception as e:
            logger.error(f"Anthropic classification failed: {e}")
            raise


class OllamaClassifier(EmailClassifier):
    """Ollama (local) based email classifier using OpenAI-compatible API."""

    def __init__(self, config: Config) -> None:
        """Initialize Ollama classifier."""
        super().__init__(config)
        self.client = OpenAI(
            base_url=config.ollama_base_url,
            api_key="ollama",  # Ollama doesn't need real key
        )
        self.model = config.ollama_model

    def classify(self, subject: str, body: str) -> ClassificationResult:
        """Classify email using Ollama (SDK has built-in retry logic)."""
        # Ollama-specific prompt: concise examples, strict format
        system_prompt = """Classify the email TYPE. Output this JSON:
{"category": "X", "confidence": 0.0-1.0, "reasoning": "brief"}

category must be ONE of: acknowledgement, rejection, followup_required, jobboard, unknown

How to classify:
- Multiple job listings (>1 job) = jobboard
- "received", "was sent to", "was viewed", "thanks for applying" = acknowledgement
- "not moving forward" / "position filled" = rejection
- "schedule" / "complete assessment" / "action required" = followup_required
- Spam/unclear = unknown

CRITICAL: acknowledgement vs jobboard
- "Your application was sent to Google" = acknowledgement (about YOUR application)
- "Your application was viewed by hiring manager" = acknowledgement (YOUR app activity)
- "Thanks for applying to Software Engineer" = acknowledgement (confirmation)
- "5 new jobs matching your search" = jobboard (multiple job listings)

Examples:
Subject: "Application sent to Company X" → acknowledgement
Subject: "Your application was viewed" → acknowledgement
Subject: "Thanks for applying" → acknowledgement
Subject: "New jobs for you" → jobboard
Subject: "Interview request" → followup_required
Subject: "Position filled" → rejection

Output ONLY the JSON. Do NOT extract job details."""

        # Smart truncation: first 1500 chars + last 500 chars
        # This captures opening (category clues) and closing (signatures/actions)
        truncated_body = body[:1500] + "\n\n[...]\n\n" + body[-500:] if len(body) > 2000 else body

        user_message = USER_MESSAGE_TEMPLATE.format(subject=subject, body=truncated_body)

        logger.debug(f"Classifying with Ollama model: {self.model}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,  # Deterministic output
                max_tokens=120,  # Tight limit to prevent extraction
                response_format={"type": "json_object"},  # Force JSON output
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Ollama")

            return self._parse_classification_response(content, "ollama", self.model)

        except Exception as e:
            logger.error(f"Ollama classification failed: {e}")
            raise


class GeminiClassifier(EmailClassifier):
    """Google Gemini based email classifier using OpenAI-compatible API."""

    def __init__(self, config: Config) -> None:
        """Initialize Gemini classifier."""
        super().__init__(config)
        if not config.gemini_api_key:
            raise ValueError("Gemini API key not configured")
        self.client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=config.gemini_api_key,
        )
        self.model = config.gemini_model

    def classify(self, subject: str, body: str) -> ClassificationResult:
        """Classify email using Gemini (SDK has built-in retry logic)."""
        user_message = USER_MESSAGE_TEMPLATE.format(subject=subject, body=body)

        logger.debug(f"Classifying with Gemini model: {self.model}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,  # Deterministic output
                max_tokens=500,
                response_format={"type": "json_object"},  # Force JSON output
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Gemini")

            return self._parse_classification_response(content, "gemini", self.model)

        except Exception as e:
            logger.error(f"Gemini classification failed: {e}")
            raise


def create_classifier(config: Config) -> EmailClassifier:
    """
    Factory function to create appropriate classifier based on config.

    Args:
        config: Application configuration

    Returns:
        EmailClassifier instance

    Raises:
        ValueError: If provider is invalid or not configured
    """
    provider = config.ai_provider.lower()

    if provider == "openai":
        return OpenAIClassifier(config)
    elif provider == "anthropic":
        return AnthropicClassifier(config)
    elif provider == "ollama":
        return OllamaClassifier(config)
    elif provider == "gemini":
        return GeminiClassifier(config)
    else:
        raise ValueError(
            f"Invalid AI provider: {provider}. Must be 'openai', 'anthropic', 'ollama', or 'gemini'"
        )
