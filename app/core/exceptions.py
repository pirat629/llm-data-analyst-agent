from fastapi import Request, status
from fastapi.responses import JSONResponse


class AgentProcessingError(Exception):
    """Безопасная обёртка для внутренних ошибок агента."""


async def agent_processing_exception_handler(
    request: Request,
    exc: AgentProcessingError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Сервис аналитического агента временно недоступен."},
    )
