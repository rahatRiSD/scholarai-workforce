"""Application configuration via Pydantic Settings.

Everything is environment-driven (`.env`, or real environment variables) —
see `.env.example`. Nothing here has a real secret baked in, and
``Settings`` deliberately makes OpenAI-with-no-key still boot (agents fall
back to a deterministic offline mode; see
``infrastructure.llm.offline_client``) so the project is runnable on a
laptop with zero paid API access, per the build spec's "no fake
functionality, but graceful fallback when a key is missing" rule.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root(start: Path | None = None) -> Path:
    """Locate runtime assets in both source checkouts and installed images."""
    candidates = (start or Path.cwd(), *Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file() and (candidate / "data").is_dir():
            return candidate
    return start or Path.cwd()


_PROJECT_ROOT = _find_project_root()


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class LLMProvider(StrEnum):
    OPENAI = "openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OFFLINE = "offline"
    """No network calls at all — deterministic canned responses for CI/demo."""


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHOLARAI_LLM__", extra="ignore")

    provider: LLMProvider = LLMProvider.OPENAI
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_min_request_interval_seconds: float = 2.1
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    temperature: float = 0.2
    max_tokens: int = 2000
    request_timeout_seconds: float = 60.0

    @property
    def effective_provider(self) -> LLMProvider:
        """Fall back to OFFLINE if the configured provider has no credentials.

        This is what lets ``scholarai demo`` and the test suite run with zero
        setup while still defaulting to OpenAI the moment a key is present.
        """
        if self.provider is LLMProvider.OPENAI and not self.openai_api_key:
            return LLMProvider.OFFLINE
        if self.provider is LLMProvider.GROQ and not self.groq_api_key:
            return LLMProvider.OFFLINE
        if self.provider is LLMProvider.ANTHROPIC and not self.anthropic_api_key:
            return LLMProvider.OFFLINE
        return self.provider


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHOLARAI_DATABASE__", extra="ignore")

    url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'scholarai.db'}"
    echo: bool = False


class VectorStoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHOLARAI_VECTORSTORE__", extra="ignore")

    url: str | None = None
    """None => in-process Qdrant (":memory:"), good enough for a laptop demo."""
    collection_prefix: str = "scholarai"


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHOLARAI_API__", extra="ignore")

    api_keys: tuple[str, ...] = ()
    """Empty => unauthenticated dev mode (loud warning per request, never silent)."""

    @property
    def auth_required(self) -> bool:
        return bool(self.api_keys)


class WebSearchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHOLARAI_WEBSEARCH__", extra="ignore")

    tavily_api_key: SecretStr | None = None
    enabled: bool = True
    provider: str = "duckduckgo"


class HumanReviewSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHOLARAI_REVIEW__", extra="ignore")

    max_critic_revisions: int = 2
    """After this many REVISE cycles, force human review instead of looping forever."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="SCHOLARAI_",
        extra="ignore",
    )

    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"

    data_dir: Path = _PROJECT_ROOT / "data"
    knowledge_base_dir: Path = _PROJECT_ROOT / "data" / "knowledge_base"
    uploads_dir: Path = _PROJECT_ROOT / "data" / "uploads"
    max_upload_size_mb: int = 15
    allowed_upload_extensions: tuple[str, ...] = (".pdf", ".txt", ".docx")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vectorstore: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    api: SecuritySettings = Field(default_factory=SecuritySettings)
    websearch: WebSearchSettings = Field(default_factory=WebSearchSettings)
    review: HumanReviewSettings = Field(default_factory=HumanReviewSettings)

    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def _require_api_keys_in_production(self) -> Settings:
        if self.environment is Environment.PRODUCTION and not self.api.auth_required:
            msg = "environment=production requires at least one SCHOLARAI_API__API_KEYS entry"
            raise ValueError(msg)
        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    """Process-wide cached settings. Call ``reload_settings`` in tests that mutate env."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    global _settings
    _settings = Settings()
    return _settings
