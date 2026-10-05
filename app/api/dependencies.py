import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_token_header = APIKeyHeader(
    name="X-Api-Token",
    auto_error=False,
    description=(
        "Вставьте значение APP_SECRET_TOKEN из .env"
    ),
)


async def require_api_token(api_token: str | None = Security(api_token_header)) -> None:
    expected_token = settings.APP_SECRET_TOKEN.get_secret_value()
    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Отсутствует заголовок X-Api-Token. Нажмите Authorize в Swagger "
                "и введите значение APP_SECRET_TOKEN."
            ),
        )
    if not secrets.compare_digest(api_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Неверный X-Api-Token. Введите только значение APP_SECRET_TOKEN "
                "без кавычек и префикса Bearer."
            ),
        )
