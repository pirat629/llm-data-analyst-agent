import os

os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("APP_SECRET_TOKEN", "test-api-token")
os.environ.setdefault(
    "DATABASE_URI",
    "postgresql+psycopg://analytics_reader:analytics_reader@localhost:5432/analytics_db",
)
