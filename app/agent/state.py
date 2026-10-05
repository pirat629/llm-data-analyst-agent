from typing import Any, Optional, TypedDict

class SQLState(TypedDict):
    question: str
    rag_context: str
    generated_sql: Optional[str]
    is_sql_valid: bool
    error_message: Optional[str]
    retry_count: int
    db_results: Optional[list[dict[str, Any]]]
    chart_spec: Optional[dict[str, Any]]
    plot_base64: Optional[str]
