import pytest

from scholarai.infrastructure.config.settings import Environment, LLMProvider, LLMSettings, Settings


def test_llm_falls_back_to_offline_without_api_key():
    settings = LLMSettings(provider=LLMProvider.OPENAI, openai_api_key=None)
    assert settings.effective_provider == LLMProvider.OFFLINE


def test_llm_uses_openai_when_key_present():
    settings = LLMSettings(provider=LLMProvider.OPENAI, openai_api_key="sk-test")
    assert settings.effective_provider == LLMProvider.OPENAI


def test_groq_falls_back_to_offline_without_key():
    settings = LLMSettings(provider=LLMProvider.GROQ, groq_api_key=None)
    assert settings.effective_provider == LLMProvider.OFFLINE


def test_groq_is_selected_when_key_present():
    settings = LLMSettings(provider=LLMProvider.GROQ, groq_api_key="gsk_test")
    assert settings.effective_provider == LLMProvider.GROQ


def test_ollama_provider_does_not_fall_back():
    settings = LLMSettings(provider=LLMProvider.OLLAMA)
    assert settings.effective_provider == LLMProvider.OLLAMA


def test_production_requires_api_keys():
    with pytest.raises(ValueError, match="requires at least one"):
        Settings(environment=Environment.PRODUCTION, api={"api_keys": ()})


def test_production_boots_with_api_keys_configured():
    settings = Settings(environment=Environment.PRODUCTION, api={"api_keys": ("secret-key",)})
    assert settings.api.auth_required is True


def test_dev_mode_has_no_auth_required_by_default():
    settings = Settings()
    assert settings.api.auth_required is False
