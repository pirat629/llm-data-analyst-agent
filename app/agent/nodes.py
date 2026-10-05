import re
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import Any
from app.core.config import settings

from app.agent.state import SQLState
from app.schemas.responses import ChartSpec
from app.services.milvus_service import search_ddl_and_examples
from app.services.sql_executor import execute_query
from app.services.plot_service import generate_plot
from app.agent.prompts import (
    get_sql_generation_prompt,
    get_sql_fix_prompt,
    get_chart_spec_prompt
)

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
    model=settings.LLM_MODEL,
    temperature=0,
    max_retries=2,
    default_headers={
        "HTTP-Referer": settings.APP_URL,
        "X-Title": settings.APP_NAME,
    }
)
chart_spec_llm = llm.with_structured_output(ChartSpec, method="json_schema")

def extract_code_from_markdown(text: str, language: str = "sql") -> str:
    pattern = rf"```{language}\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def retrieve_schema_node(state: SQLState) -> dict[str, Any]:
    question = state["question"]

    rag_context = search_ddl_and_examples(question)

    return {"rag_context": rag_context}


def generate_sql_node(state: SQLState) -> dict[str, Any]:
    question = state["question"]
    rag_context = state["rag_context"]
    error_message = state.get("error_message")
    generated_sql = state.get("generated_sql")
    retry_count = state.get("retry_count", 0)

    if error_message and generated_sql:
        system_prompt = get_sql_fix_prompt(rag_context)
        human_content = f"Запрос упал с ошибкой:\n{error_message}\n\nПлохой SQL:\n{generated_sql}\n\nИсправь его."
    else:
        system_prompt = get_sql_generation_prompt(rag_context)
        human_content = question

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content)
    ]

    response = llm.invoke(messages)

    clean_sql = extract_code_from_markdown(response.content)

    return {
        "generated_sql": clean_sql,
        "retry_count": retry_count + 1
    }

def execute_sql_node(state: SQLState) -> dict[str, Any]:
    sql = state["generated_sql"]

    try:
        results = execute_query(sql)

        return {
            "is_sql_valid": True,
            "db_results": results,
            "error_message": None
        }
    except Exception as e:
        return {
            "is_sql_valid": False,
            "error_message": str(e),
            "db_results": None
        }


def generate_plot_node(state: SQLState) -> dict[str, Any]:
    question = state["question"]
    db_results = state["db_results"]

    if not db_results:
        return {"chart_spec": None, "plot_base64": None}

    sample_data = db_results[0] if len(db_results) > 0 else {}
    columns = list(sample_data.keys())

    messages = [
        SystemMessage(content=get_chart_spec_prompt(columns, sample_data)),
        HumanMessage(content=f"Выбери визуализацию для вопроса: {question}")
    ]

    try:
        raw_chart_spec = chart_spec_llm.invoke(messages)
        chart_spec = (
            raw_chart_spec
            if isinstance(raw_chart_spec, ChartSpec)
            else ChartSpec.model_validate(raw_chart_spec)
        )
        plot_base64 = generate_plot(chart_spec, db_results)
    except Exception as exc:
        logger.warning("Не удалось построить визуализацию: %s", exc)
        return {"chart_spec": None, "plot_base64": None}

    return {
        "chart_spec": chart_spec.model_dump(),
        "plot_base64": plot_base64
    }
