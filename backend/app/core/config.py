from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_env: str = "development"
    data_backend: str = "json"
    database_enabled: bool = False
    database_url: str = "sqlite:///./agents_dev.db"
    es_enabled: bool = False
    es_url: str = "http://127.0.0.1:9200"
    es_username: str | None = None
    es_password: str | None = None
    es_index_knowledge: str = "aviation_material_knowledge"
    bge_enabled: bool = False
    bge_model_path: str | None = None
    embedding_backend: str = "none"
    retrieval_mode: str = "hybrid"
    llm_enabled: bool = False
    llm_resource_generation_enabled: bool = False
    llm_semantic_review_enabled: bool = False
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout: int = 60
    llm_max_tokens: int = 1800
    llm_retries: int = 1
    version: str = "1.2.0-context-assistant"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
