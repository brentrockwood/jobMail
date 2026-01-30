"""Unit tests for email classifier."""

import json
from unittest.mock import Mock, patch

import pytest

from src.classifier import (
    AnthropicClassifier,
    ClassificationCategory,
    ClassificationResult,
    EmailClassifier,
    GeminiClassifier,
    OllamaClassifier,
    OpenAIClassifier,
    create_classifier,
)
from src.config import Config


@pytest.fixture
def mock_config() -> Config:
    """Create mock config for testing."""
    config = Mock(spec=Config)
    config.openai_api_key = "sk-test-key"
    config.openai_model = "gpt-4"
    config.anthropic_api_key = "sk-ant-test-key"
    config.anthropic_model = "claude-3-5-sonnet-20241022"
    config.ollama_base_url = "http://localhost:11434"
    config.ollama_model = "llama2"
    config.gemini_api_key = "test-gemini-key"
    config.gemini_model = "gemini-2.0-flash-exp"
    config.ai_provider = "openai"
    return config


class TestClassificationResult:
    """Test ClassificationResult dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = ClassificationResult(
            category=ClassificationCategory.ACKNOWLEDGEMENT,
            confidence=0.95,
            provider="openai",
            model="gpt-4",
            reasoning="Clear acknowledgement language",
        )

        expected = {
            "category": "acknowledgement",
            "confidence": 0.95,
            "provider": "openai",
            "model": "gpt-4",
            "reasoning": "Clear acknowledgement language",
        }

        assert result.to_dict() == expected


class TestEmailClassifierParsing:
    """Test base classifier's response parsing."""

    def test_parse_valid_json(self, mock_config: Config) -> None:
        """Test parsing valid JSON response."""

        # Create a concrete subclass for testing
        class TestClassifier(EmailClassifier):
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(ClassificationCategory.UNKNOWN, 0.5, "test", "test")

        classifier = TestClassifier(mock_config)

        response = json.dumps(
            {
                "category": "acknowledgement",
                "confidence": 0.95,
                "reasoning": "Test reasoning",
            }
        )

        result = classifier._parse_classification_response(response, "test", "model-1")

        assert result.category == ClassificationCategory.ACKNOWLEDGEMENT
        assert result.confidence == 0.95
        assert result.provider == "test"
        assert result.model == "model-1"
        assert result.reasoning == "Test reasoning"

    def test_parse_json_with_markdown(self, mock_config: Config) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""

        class TestClassifier(EmailClassifier):
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(ClassificationCategory.UNKNOWN, 0.5, "test", "test")

        classifier = TestClassifier(mock_config)

        response = """```json
{
  "category": "rejection",
  "confidence": 0.88,
  "reasoning": "Contains rejection language"
}
```"""

        result = classifier._parse_classification_response(response, "test", "model-1")

        assert result.category == ClassificationCategory.REJECTION
        assert result.confidence == 0.88

    def test_parse_invalid_category_defaults_to_unknown(self, mock_config: Config) -> None:
        """Test that invalid category defaults to unknown."""

        class TestClassifier(EmailClassifier):
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(ClassificationCategory.UNKNOWN, 0.5, "test", "test")

        classifier = TestClassifier(mock_config)

        response = json.dumps(
            {"category": "invalid_category", "confidence": 0.5, "reasoning": "Test"}
        )

        result = classifier._parse_classification_response(response, "test", "model-1")

        assert result.category == ClassificationCategory.UNKNOWN

    def test_parse_confidence_out_of_range_clamped(self, mock_config: Config) -> None:
        """Test that confidence values are clamped to [0, 1]."""

        class TestClassifier(EmailClassifier):
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(ClassificationCategory.UNKNOWN, 0.5, "test", "test")

        classifier = TestClassifier(mock_config)

        # Test > 1.0
        response = json.dumps({"category": "acknowledgement", "confidence": 1.5})
        result = classifier._parse_classification_response(response, "test", "model-1")
        assert result.confidence == 1.0

        # Test < 0.0
        response = json.dumps({"category": "acknowledgement", "confidence": -0.5})
        result = classifier._parse_classification_response(response, "test", "model-1")
        assert result.confidence == 0.0

    def test_parse_missing_required_fields_raises_error(self, mock_config: Config) -> None:
        """Test that missing required fields raises ValueError."""

        class TestClassifier(EmailClassifier):
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(ClassificationCategory.UNKNOWN, 0.5, "test", "test")

        classifier = TestClassifier(mock_config)

        # Missing confidence
        response = json.dumps({"category": "acknowledgement"})
        with pytest.raises(ValueError, match="Missing required fields"):
            classifier._parse_classification_response(response, "test", "model-1")

        # Missing category
        response = json.dumps({"confidence": 0.5})
        with pytest.raises(ValueError, match="Missing required fields"):
            classifier._parse_classification_response(response, "test", "model-1")

    def test_parse_invalid_json_raises_error(self, mock_config: Config) -> None:
        """Test that invalid JSON raises ValueError."""

        class TestClassifier(EmailClassifier):
            def classify(self, subject: str, body: str) -> ClassificationResult:
                return ClassificationResult(ClassificationCategory.UNKNOWN, 0.5, "test", "test")

        classifier = TestClassifier(mock_config)

        response = "not valid json"
        with pytest.raises(ValueError, match="Invalid JSON response"):
            classifier._parse_classification_response(response, "test", "model-1")


class TestOpenAIClassifier:
    """Test OpenAI classifier."""

    def test_requires_api_key(self, mock_config: Config) -> None:
        """Test that OpenAI classifier requires API key."""
        mock_config.openai_api_key = None
        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            OpenAIClassifier(mock_config)

    @patch("src.classifier.OpenAI")
    def test_classify_success(self, mock_openai_class: Mock, mock_config: Config) -> None:
        """Test successful classification with OpenAI."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "category": "acknowledgement",
                "confidence": 0.92,
                "reasoning": "Email confirms receipt",
            }
        )
        mock_client.chat.completions.create.return_value = mock_response

        classifier = OpenAIClassifier(mock_config)
        result = classifier.classify("Thank you for applying", "We received your application")

        assert result.category == ClassificationCategory.ACKNOWLEDGEMENT
        assert result.confidence == 0.92
        assert result.provider == "openai"
        assert result.model == "gpt-4"

        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4"
        assert call_args.kwargs["temperature"] == 0.0


class TestAnthropicClassifier:
    """Test Anthropic classifier."""

    def test_requires_api_key(self, mock_config: Config) -> None:
        """Test that Anthropic classifier requires API key."""
        mock_config.anthropic_api_key = None
        with pytest.raises(ValueError, match="Anthropic API key not configured"):
            AnthropicClassifier(mock_config)

    @patch("src.classifier.anthropic.Anthropic")
    def test_classify_success(self, mock_anthropic_class: Mock, mock_config: Config) -> None:
        """Test successful classification with Anthropic."""
        # Mock Anthropic response
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps(
            {
                "category": "rejection",
                "confidence": 0.88,
                "reasoning": "Polite rejection language",
            }
        )
        mock_client.messages.create.return_value = mock_response

        classifier = AnthropicClassifier(mock_config)
        result = classifier.classify(
            "Application Update", "We've decided to pursue other candidates"
        )

        assert result.category == ClassificationCategory.REJECTION
        assert result.confidence == 0.88
        assert result.provider == "anthropic"
        assert result.model == "claude-3-5-sonnet-20241022"

        # Verify API call
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-3-5-sonnet-20241022"
        assert call_args.kwargs["temperature"] == 0.0


class TestOllamaClassifier:
    """Test Ollama classifier."""

    @patch("src.classifier.OpenAI")
    def test_classify_success(self, mock_openai_class: Mock, mock_config: Config) -> None:
        """Test successful classification with Ollama."""
        # Mock Ollama response (uses OpenAI-compatible API)
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "category": "followup_required",
                "confidence": 0.95,
                "reasoning": "Interview scheduling request",
            }
        )
        mock_client.chat.completions.create.return_value = mock_response

        classifier = OllamaClassifier(mock_config)
        result = classifier.classify("Interview Request", "Are you available for an interview?")

        assert result.category == ClassificationCategory.FOLLOWUP
        assert result.confidence == 0.95
        assert result.provider == "ollama"
        assert result.model == "llama2"

        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "llama2"


class TestGeminiClassifier:
    """Test Gemini classifier."""

    def test_requires_api_key(self, mock_config: Config) -> None:
        """Test that Gemini classifier requires API key."""
        mock_config.gemini_api_key = None
        with pytest.raises(ValueError, match="Gemini API key not configured"):
            GeminiClassifier(mock_config)

    @patch("src.classifier.OpenAI")
    def test_classify_success(self, mock_openai_class: Mock, mock_config: Config) -> None:
        """Test successful classification with Gemini."""
        # Mock Gemini response (uses OpenAI-compatible API)
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "category": "jobboard",
                "confidence": 0.97,
                "reasoning": "Job board notification email",
            }
        )
        mock_client.chat.completions.create.return_value = mock_response

        classifier = GeminiClassifier(mock_config)
        result = classifier.classify("New jobs for you", "We found 5 new jobs matching your search")

        assert result.category == ClassificationCategory.JOBBOARD
        assert result.confidence == 0.97
        assert result.provider == "gemini"
        assert result.model == "gemini-2.0-flash-exp"

        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gemini-2.0-flash-exp"
        assert call_args.kwargs["temperature"] == 0.0


class TestCreateClassifier:
    """Test classifier factory function."""

    def test_create_openai_classifier(self, mock_config: Config) -> None:
        """Test creating OpenAI classifier."""
        mock_config.ai_provider = "openai"
        classifier = create_classifier(mock_config)
        assert isinstance(classifier, OpenAIClassifier)

    def test_create_anthropic_classifier(self, mock_config: Config) -> None:
        """Test creating Anthropic classifier."""
        mock_config.ai_provider = "anthropic"
        classifier = create_classifier(mock_config)
        assert isinstance(classifier, AnthropicClassifier)

    def test_create_ollama_classifier(self, mock_config: Config) -> None:
        """Test creating Ollama classifier."""
        mock_config.ai_provider = "ollama"
        classifier = create_classifier(mock_config)
        assert isinstance(classifier, OllamaClassifier)

    def test_create_gemini_classifier(self, mock_config: Config) -> None:
        """Test creating Gemini classifier."""
        mock_config.ai_provider = "gemini"
        classifier = create_classifier(mock_config)
        assert isinstance(classifier, GeminiClassifier)

    def test_invalid_provider_raises_error(self, mock_config: Config) -> None:
        """Test that invalid provider raises ValueError."""
        mock_config.ai_provider = "invalid"
        with pytest.raises(ValueError, match="Invalid AI provider"):
            create_classifier(mock_config)
