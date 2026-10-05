import base64

from fastapi.testclient import TestClient

from app.agent.graph import route_after_execution
from app.main import app
from app.schemas.responses import ChartSpec
from app.services.plot_service import generate_plot
from app.services.sql_executor import is_safe_query, validate_and_prepare_query
from data.load_data import get_raw_documents


def test_sql_validator_accepts_analytics_query_and_adds_limit():
    sql = """
        WITH revenue AS (
            SELECT user_id, SUM(amount) AS total
            FROM payments
            WHERE status = 'success'
            GROUP BY user_id
        )
        SELECT user_id, total FROM revenue ORDER BY total DESC
    """

    prepared = validate_and_prepare_query(sql)

    assert "LIMIT 1000" in prepared
    assert is_safe_query(sql)


def test_sql_validator_preserves_a_smaller_limit_and_caps_a_larger_one():
    assert validate_and_prepare_query("SELECT * FROM payments LIMIT 10").endswith("LIMIT 10")
    assert validate_and_prepare_query("SELECT * FROM payments LIMIT 5000").endswith("LIMIT 1000")


def test_sql_validator_rejects_unsafe_queries():
    unsafe_queries = [
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT pg_sleep(600)",
        "CREATE TEMP TABLE x(a int)",
        "COPY (SELECT 1) TO PROGRAM 'id'",
        "SELECT 1; SELECT 2",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM unknown_table",
        "WITH changed AS (DELETE FROM payments RETURNING *) SELECT * FROM changed",
    ]

    assert all(not is_safe_query(sql) for sql in unsafe_queries)


def test_plot_renderer_returns_png_without_executing_code():
    spec = ChartSpec(
        chart_type="bar",
        x="country",
        y="revenue",
        title="Revenue by country",
    )

    encoded = generate_plot(
        spec,
        [
            {"country": "Germany", "revenue": 120.5},
            {"country": "France", "revenue": 95.0},
        ],
    )

    assert encoded is not None
    assert base64.b64decode(encoded).startswith(b"\x89PNG\r\n\x1a\n")


def test_plot_renderer_rejects_unknown_columns():
    spec = ChartSpec(chart_type="line", x="month", y="missing", title="Trend")
    assert generate_plot(spec, [{"month": "2026-01", "revenue": 10}]) is None


def test_graph_retries_failed_sql_and_finishes_after_limit():
    assert route_after_execution({"is_sql_valid": False, "retry_count": 1}) == "generate_sql"
    assert route_after_execution({"is_sql_valid": False, "retry_count": 3}) == "__end__"
    assert route_after_execution({"is_sql_valid": True, "retry_count": 1}) == "generate_plot"


def test_rag_documents_include_every_database_table():
    documents = get_raw_documents()
    ddl_text = "\n".join(
        document["text"] for document in documents if document["doc_type"] == "ddl_table"
    )

    for table in ("users", "payments", "app_events", "support_tickets"):
        assert f"CREATE TABLE {table}" in ddl_text


def test_api_requires_token():
    with TestClient(app) as client:
        response = client.post("/api/v1/agent/query", json={"query": "Show revenue"})

    assert response.status_code == 401
    assert "Отсутствует заголовок X-Api-Token" in response.json()["detail"]


def test_api_rejects_invalid_token():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/query",
            headers={"X-Api-Token": "wrong-token"},
            json={"query": "Show revenue"},
        )

    assert response.status_code == 401
    assert "Неверный X-Api-Token" in response.json()["detail"]


def test_api_validates_query_length():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/query",
            headers={"X-Api-Token": "test-api-token"},
            json={"query": "x"},
        )

    assert response.status_code == 422
