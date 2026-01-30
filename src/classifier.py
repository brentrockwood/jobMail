"""AI-powered email classification for job application emails."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import anthropic
import openai
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


# Classification prompt - designed to work well with all AI providers
CLASSIFICATION_PROMPT = """You are an expert email classifier for job application emails.

Analyze the email below and classify it into ONE of these categories:

1. **acknowledgement** - The company confirms they received your application
   - Usually automated responses
   - May mention "received", "reviewing", "thank you for applying"
   - No specific action required yet

2. **rejection** - The company is declining your application
   - May be polite ("we've decided to pursue other candidates")
   - May mention "not moving forward", "not selected", "other applicants"
   - Can occur at any stage (initial screening, after interview, etc.)

3. **followup_required** - Action required from you
   - Scheduling interview requests
   - Requests for additional information
   - Assignment/assessment invitations
   - Any email requiring your response or action

4. **jobboard** - Automated notifications from job boards/platforms
   - Indeed, LinkedIn, Glassdoor, ZipRecruiter alerts
   - "New jobs matching your search"
   - Job recommendations
   - Usually promotional/automated

5. **unknown** - Unclear or doesn't fit above categories
   - Ambiguous emails
   - Unrelated to job applications
   - Spam or unclear intent

Respond with ONLY valid JSON in this exact format:
{{
  "category": "one of: acknowledgement, rejection, followup_required, jobboard, unknown",
  "confidence": 0.95,
  "reasoning": "Brief explanation of why you chose this category"
}}

Email Subject: {subject}

Email Body:
{body}

Classification (JSON only):"""


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

            # Validate required fields
            if "category" not in data or "confidence" not in data:
                raise ValueError(f"Missing required fields in response: {data}")

            # Validate category
            try:
                category = ClassificationCategory(data["category"])
            except ValueError:
                logger.warning(
                    f"Invalid category '{data['category']}', defaulting to unknown"
                )
                category = ClassificationCategory.UNKNOWN

            # Validate confidence
            confidence = float(data["confidence"])
            if not 0.0 <= confidence <= 1.0:
                logger.warning(
                    f"Confidence {confidence} out of range, clamping to [0,1]"
                )
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
            raise ValueError(f"Invalid JSON response from {provider}: {e}")
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
        """Classify email using OpenAI."""
        prompt = CLASSIFICATION_PROMPT.format(subject=subject, body=body)

        logger.debug(f"Classifying with OpenAI model: {self.model}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic output
                max_tokens=500,
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
        """Classify email using Anthropic Claude."""
        prompt = CLASSIFICATION_PROMPT.format(subject=subject, body=body)

        logger.debug(f"Classifying with Anthropic model: {self.model}")
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.0,  # Deterministic output
                messages=[{"role": "user", "content": prompt}],
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
            base_url=config.ollama_base_url, api_key="ollama"  # Ollama doesn't need real key
        )
        self.model = config.ollama_model

    def classify(self, subject: str, body: str) -> ClassificationResult:
        """Classify email using Ollama."""
        prompt = CLASSIFICATION_PROMPT.format(subject=subject, body=body)

        logger.debug(f"Classifying with Ollama model: {self.model}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic output
                max_tokens=500,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Ollama")

            return self._parse_classification_response(content, "ollama", self.model)

        except Exception as e:
            logger.error(f"Ollama classification failed: {e}")
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
    else:
        raise ValueError(
            f"Invalid AI provider: {provider}. "
            "Must be 'openai', 'anthropic', or 'ollama'"
        )
