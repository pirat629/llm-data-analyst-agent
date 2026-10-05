import uuid
from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Вопрос пользователя на естественном языке",
        examples=["Покажи ARPU пользователей по месяцам за 2026 год"]
    )

    thread_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Correlation ID запроса. Если не передан, генерируется автоматически.",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
