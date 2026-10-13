from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    ollama_host: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    embedding_model: str = "nomic-embed-text"

    data_path: str = "data/"
    chroma_path: str = "chroma_db/"


@lru_cache
def get_settings() -> Settings:
    return Settings()