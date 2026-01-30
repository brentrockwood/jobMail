"""Configuration management for JobMail."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from secrets.env (takes precedence over .env)
load_dotenv("secrets.env")
load_dotenv(".env.example")

AIProvider = Literal["openai", "anthropic", "ollama"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class Config:
    """Application configuration."""

    # AI Provider
    ai_provider: AIProvider
    openai_api_key: str | None
    openai_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    ollama_base_url: str
    ollama_model: str

    # Gmail
    gmail_credentials_file: Path
    gmail_token_file: Path

    # Classification
    confidence_threshold: float
    batch_size: int

    # Labels
    label_acknowledged: str
    label_rejected: str
    label_followup: str
    label_jobboard: str

    # Processing
    dry_run: bool
    log_level: LogLevel

    # Database
    database_path: Path

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            # AI Provider
            ai_provider=os.getenv("AI_PROVIDER", "openai"),  # type: ignore
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama2"),
            # Gmail
            gmail_credentials_file=Path(os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")),
            gmail_token_file=Path(os.getenv("GMAIL_TOKEN_FILE", "token.json")),
            # Classification
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.8")),
            batch_size=int(os.getenv("BATCH_SIZE", "20")),
            # Labels
            label_acknowledged=os.getenv("LABEL_ACKNOWLEDGED", "Acknowledged"),
            label_rejected=os.getenv("LABEL_REJECTED", "Rejected"),
            label_followup=os.getenv("LABEL_FOLLOWUP", "FollowUp"),
            label_jobboard=os.getenv("LABEL_JOBBOARD", "JobBoard"),
            # Processing
            dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),  # type: ignore
            # Database
            database_path=Path(os.getenv("DATABASE_PATH", "jobmail.db")),
        )

    def validate(self) -> None:
        """Validate configuration and raise ValueError if invalid."""
        # Validate AI provider configuration
        if self.ai_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER is 'openai'")
        if self.ai_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when AI_PROVIDER is 'anthropic'")
        if self.ai_provider not in ["openai", "anthropic", "ollama"]:
            raise ValueError(
                f"Invalid AI_PROVIDER: {self.ai_provider}. "
                "Must be 'openai', 'anthropic', or 'ollama'"
            )

        # Validate confidence threshold
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"CONFIDENCE_THRESHOLD must be between 0.0 and 1.0, "
                f"got {self.confidence_threshold}"
            )

        # Validate batch size
        if self.batch_size < 1:
            raise ValueError(f"BATCH_SIZE must be at least 1, got {self.batch_size}")


def setup_logging(level: LogLevel = "INFO") -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, level)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduce noise from googleapiclient
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
