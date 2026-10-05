from functools import cached_property

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENROUTER_API_KEY: SecretStr
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "openai/gpt-4o-mini"
    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"

    APP_URL: str = "http://localhost:8000"
    APP_NAME: str = "Text-to-SQL Agent Project"
    APP_SECRET_TOKEN: SecretStr
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8501"

    COLLECTION_NAME: str = "database_schema_and_examples"

    DATABASE_URI: str = "postgresql+psycopg://analytics_reader:analytics_reader@localhost:5432/analytics_db"
    DATABASE_ADMIN_URI: str = "postgresql+psycopg://postgres:postgres@localhost:5432/analytics_db"
    MILVUS_URI: str = "http://localhost:19530"

    SQL_ALLOWED_TABLES: str = "users,payments,app_events,support_tickets"
    SQL_MAX_ROWS: int = 1000
    SQL_STATEMENT_TIMEOUT_MS: int = 10_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @cached_property
    def sql_allowed_tables(self) -> set[str]:
        return {table.strip().lower() for table in self.SQL_ALLOWED_TABLES.split(",") if table.strip()}

settings = Settings()
