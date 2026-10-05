import logging
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlglot import exp, parse
from sqlglot.errors import ParseError

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URI, pool_pre_ping=True)

FORBIDDEN_NODE_TYPES = {
    "Alter",
    "Analyze",
    "Attach",
    "Command",
    "Commit",
    "Copy",
    "Create",
    "Delete",
    "Detach",
    "Drop",
    "Execute",
    "Grant",
    "Insert",
    "Into",
    "LoadData",
    "Lock",
    "Merge",
    "Pragma",
    "Rollback",
    "Set",
    "Transaction",
    "TruncateTable",
    "Update",
    "Use",
}

FORBIDDEN_FUNCTIONS = {
    "current_setting",
    "dblink",
    "dblink_connect",
    "dblink_exec",
    "lo_export",
    "lo_import",
    "nextval",
    "pg_read_binary_file",
    "pg_read_file",
    "pg_sleep",
    "pg_terminate_backend",
    "pg_write_file",
    "set_config",
    "setval",
}


class UnsafeQueryError(ValueError):
    """Возникает, когда сгенерированный SQL-запрос нарушает политику доступа только для чтения."""


def _function_name(function: exp.Func) -> str:
    if isinstance(function, exp.Anonymous):
        return function.name.lower()
    return function.sql_name().lower()


def _apply_row_limit(statement: exp.Query) -> exp.Query:
    current_limit = statement.args.get("limit")
    if current_limit is not None:
        limit_value = current_limit.expression
        if isinstance(limit_value, exp.Literal) and limit_value.is_int:
            if 0 <= int(limit_value.this) <= settings.SQL_MAX_ROWS:
                return statement
    return statement.limit(settings.SQL_MAX_ROWS)


def validate_and_prepare_query(sql: str) -> str:
    try:
        statements = [statement for statement in parse(sql, read="postgres") if statement]
    except ParseError as exc:
        raise UnsafeQueryError("Не удалось разобрать SQL-запрос в синтаксисе PostgreSQL.") from exc

    if len(statements) != 1:
        raise UnsafeQueryError("Разрешён только один SQL-запрос.")

    statement = statements[0]
    if not isinstance(statement, exp.Query):
        raise UnsafeQueryError("Разрешены только запросы SELECT или WITH.")

    for node in statement.walk():
        if type(node).__name__ in FORBIDDEN_NODE_TYPES:
            raise UnsafeQueryError(f"Запрещённая SQL-операция: {type(node).__name__}.")

    cte_names = {
        cte.alias_or_name.lower()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }
    for table in statement.find_all(exp.Table):
        table_name = table.name.lower()
        schema_name = table.db.lower() if table.db else ""
        if schema_name and schema_name != "public":
            raise UnsafeQueryError(f"Схема не разрешена: {schema_name}.")
        if table_name not in cte_names and table_name not in settings.sql_allowed_tables:
            raise UnsafeQueryError(f"Таблица не разрешена: {table_name}.")

    for function in statement.find_all(exp.Func):
        function_name = _function_name(function)
        if function_name in FORBIDDEN_FUNCTIONS or function_name.startswith(("pg_", "lo_")):
            raise UnsafeQueryError(f"Функция не разрешена: {function_name}.")

    limited_statement = _apply_row_limit(statement.copy())
    return limited_statement.sql(dialect="postgres")


def is_safe_query(sql: str) -> bool:
    try:
        validate_and_prepare_query(sql)
        return True
    except UnsafeQueryError:
        return False


def execute_query(sql: str) -> list[dict[str, Any]]:
    safe_sql = validate_and_prepare_query(sql)

    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(
                text(f"SET LOCAL statement_timeout = {int(settings.SQL_STATEMENT_TIMEOUT_MS)}")
            )
            result = connection.execute(text(safe_sql))

            if not result.returns_rows:
                return []

            rows = result.mappings().fetchmany(settings.SQL_MAX_ROWS)
            return [dict(mapping) for mapping in rows]

    except SQLAlchemyError as exc:
        raw_error = str(getattr(exc, "orig", exc))
        logger.warning("Ошибка БД при выполнении безопасного запроса: %s", raw_error)
        raise RuntimeError(raw_error) from exc
