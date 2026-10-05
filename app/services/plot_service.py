import io
import base64
import logging
import matplotlib

matplotlib.use('Agg')
from matplotlib.figure import Figure
import pandas as pd

from app.schemas.responses import ChartSpec

logger = logging.getLogger(__name__)


def _validate_columns(spec: ChartSpec, dataframe: pd.DataFrame) -> None:
    requested_columns = {spec.x, spec.y}
    if spec.group_by:
        requested_columns.add(spec.group_by)

    missing = requested_columns.difference(dataframe.columns)
    if missing:
        raise ValueError(f"ChartSpec содержит неизвестные колонки: {sorted(missing)}")


def generate_plot(spec: ChartSpec, db_results: list[dict]) -> str | None:
    if not db_results:
        return None

    try:
        dataframe = pd.DataFrame(db_results)
        _validate_columns(spec, dataframe)

        dataframe = dataframe.copy()
        dataframe[spec.y] = pd.to_numeric(dataframe[spec.y], errors="coerce")
        dataframe = dataframe.dropna(subset=[spec.x, spec.y])
        if dataframe.empty:
            raise ValueError("После преобразования чисел не осталось данных для построения графика")

        figure = Figure(figsize=(10, 6), constrained_layout=True)
        axis = figure.subplots()

        if spec.chart_type == "pie":
            values = dataframe.groupby(spec.x, dropna=False)[spec.y].sum().head(12)
            axis.pie(values.values, labels=values.index.astype(str), autopct="%1.1f%%")
            axis.set_ylabel("")
        elif spec.group_by:
            grouped = dataframe.pivot_table(
                index=spec.x,
                columns=spec.group_by,
                values=spec.y,
                aggfunc="sum",
            )
            if spec.chart_type == "bar":
                grouped.plot(kind="bar", ax=axis)
            elif spec.chart_type == "line":
                grouped.plot(kind="line", marker="o", ax=axis)
            else:
                for group_name, group in dataframe.groupby(spec.group_by):
                    axis.scatter(group[spec.x], group[spec.y], label=str(group_name))
                axis.legend(title=spec.group_by)
        elif spec.chart_type == "bar":
            axis.bar(dataframe[spec.x].astype(str), dataframe[spec.y])
        elif spec.chart_type == "line":
            axis.plot(dataframe[spec.x], dataframe[spec.y], marker="o")
        else:
            axis.scatter(dataframe[spec.x], dataframe[spec.y])

        axis.set_title(spec.title)
        axis.set_xlabel(spec.x_label or spec.x)
        if spec.chart_type != "pie":
            axis.set_ylabel(spec.y_label or spec.y)
            axis.grid(True, alpha=0.3)
        axis.tick_params(axis="x", rotation=30)

        buf = io.BytesIO()
        figure.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)

        return base64.b64encode(buf.read()).decode("utf-8")

    except Exception as e:
        logger.warning("Ошибка при генерации графика: %s", e)
        return None
