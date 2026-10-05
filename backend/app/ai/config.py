"""AI provider configuration, loaded from environment."""
from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    """Sprint 4 AI provider settings.

    No secrets live here: Ollama runs locally and needs no API key.
    """

    AI_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    AI_TIMEOUT_SECONDS: float = 20.0

    class Config:
        env_file = ".env"
        case_sensitive = True


ai_settings = AISettings()
