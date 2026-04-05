from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Interview Platform", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    api_prefix: str = Field(default="/api/v1", description="API prefix")

    deepseek_api_key: str = Field(default="", description="DeepSeek API key")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek OpenAI-compatible API base URL",
    )
    deepseek_model: str = Field(default="deepseek-chat", description="Default DeepSeek model")
    deepseek_timeout: float = Field(default=30.0, description="LLM request timeout in seconds")

    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Default Groq model")
    llm_provider: str = Field(default="groq", description="Preferred LLM provider (deepseek, groq)")

    deepgram_api_key: str = Field(default="", description="Deepgram API key")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
