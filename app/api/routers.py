import logging
from fastapi import APIRouter, Depends

from app.api.dependencies import require_api_token
from app.core.exceptions import AgentProcessingError
from app.schemas.requests import ChatQueryRequest
from app.schemas.responses import ChatQueryResponse
from app.agent.graph import agent_graph

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["AI Agent"],
    dependencies=[Depends(require_api_token)],
)


@router.post("/query", response_model=ChatQueryResponse)
async def process_text_to_sql_query(request: ChatQueryRequest):
    thread_id = str(request.thread_id)
    logger.info("Получен аналитический запрос (thread_id: %s)", thread_id)

    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "question": request.query,
        "retry_count": 0,
        "error_message": None
    }

    try:
        result_state = await agent_graph.ainvoke(initial_state, config)

        is_valid = result_state.get("is_sql_valid", False)

        response = ChatQueryResponse(
            thread_id=thread_id,
            sql_query=result_state.get("generated_sql") if is_valid else None,
            data=result_state.get("db_results") if is_valid else None,
            chart_spec=result_state.get("chart_spec") if is_valid else None,
            plot_base64=result_state.get("plot_base64"),
            error=(
                "Не удалось построить безопасный SQL-запрос после нескольких попыток."
                if not is_valid
                else None
            ),
        )

        return response


    except Exception as exc:
        logger.error(
            "Ошибка при выполнении агента: %s",
            exc,
            exc_info=True
        )
        raise AgentProcessingError from exc
