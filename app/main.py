import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import router as agent_router
from app.core.config import settings
from app.core.exceptions import AgentProcessingError, agent_processing_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Запуск {settings.APP_NAME}...")
    yield
    logger.info("Выключение сервиса. Очистка ресурсов...")
    from app.services.sql_executor import engine
    from app.services.milvus_service import close_milvus_client

    engine.dispose()
    close_milvus_client()

app = FastAPI(
    title=settings.APP_NAME,
    description="API для AI-агента, который переводит текст в SQL, исполняет его и строит графики.",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AgentProcessingError, agent_processing_exception_handler)

app.include_router(agent_router)

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "docs_url": "/docs"
    }


@app.get("/health/live", tags=["Health"])
async def liveness():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
