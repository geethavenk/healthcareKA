"""
Centralized application settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- API / APP -----
    app_name: str = "Healthcare Knowledge and Appointment Assistant"
    environment: str = "development"
    api_key: str
    allowed_origins: str = "http://localhost:8501"

    # ---- PostgreSQL ------
    database_url: str

    # ---- Neo4j -----
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # ----- OpenAI -----
    openai_api_key: str 
    embedding_model: str = "text-embedding-3-small"
    chat_model:str = "gpt-4o-mini"

    # --- Rate limiting -------
    rate_limit_ask: str = "5/minute"
    rate_limit_search: str = "10/minute"
    rate_limit_documents: str = "20/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Turn the comma separated ALLOWED_ORIGINS string into a clean list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    """
    Cached Settings() -- which reads env vars / .env file -- only runs
    once per process, instead of re-parsing on every import or request.
    """  
    return Settings()

settings = get_settings()