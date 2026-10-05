from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class ChartSpec(BaseModel):
    chart_type: Literal["bar", "line", "scatter", "pie"] = Field(
        description="Тип визуализации"
    )
    x: str = Field(description="Колонка для оси X или подписей pie chart")
    y: str = Field(description="Числовая колонка для оси Y")
    group_by: Optional[str] = Field(
        default=None,
        description="Необязательная колонка для разбиения на серии"
    )
    title: str = Field(min_length=1, max_length=160)
    x_label: Optional[str] = Field(default=None, max_length=80)
    y_label: Optional[str] = Field(default=None, max_length=80)


class ChatQueryResponse(BaseModel):
    thread_id: str = Field(
        ...,
        description="Correlation ID запроса"
    )

    sql_query: Optional[str] = Field(
        None,
        description="Успешно выполненный SQL-запрос (для отображения пользователю)",
        examples=["SELECT DATE_TRUNC('month', created_at), SUM(amount) FROM payments GROUP BY 1;"]
    )

    data: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Данные из базы, ограниченные серверным лимитом"
    )

    chart_spec: Optional[ChartSpec] = Field(
        None,
        description="Проверенное структурированное описание визуализации"
    )

    plot_base64: Optional[str] = Field(
        None,
        description="Сгенерированный график в формате base64 (готовый к вставке в <img src='data:image/png;base64,...'>)"
    )

    error: Optional[str] = Field(
        None,
        description="Текст ошибки, если агент окончательно сдался (например, исчерпал лимит попыток)"
    )
