from langgraph.graph import StateGraph, START, END

from app.agent.state import SQLState
from app.agent.nodes import (
    retrieve_schema_node,
    generate_sql_node,
    execute_sql_node,
    generate_plot_node
)

MAX_RETRIES = 3

def route_after_execution(state: SQLState):
    if state.get("is_sql_valid"):
        return "generate_plot"

    if state.get("retry_count", 0) < MAX_RETRIES:
        return "generate_sql"

    return END

def build_graph():
    graph = StateGraph(SQLState)

    graph.add_node("retrieve_schema", retrieve_schema_node)
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("generate_plot", generate_plot_node)

    graph.add_edge(START, "retrieve_schema")
    graph.add_edge("retrieve_schema", "generate_sql")
    graph.add_edge("generate_sql", "execute_sql")

    graph.add_conditional_edges(
        "execute_sql",
        route_after_execution
    )

    graph.add_edge("generate_plot", END)

    return graph.compile()

agent_graph = build_graph()