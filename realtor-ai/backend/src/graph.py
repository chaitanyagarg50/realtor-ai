from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from src.util.state import State
from src.graph_nodes.search_criteria_agent import search_criteria_agent
from src.graph_nodes.main_agent import main_agent_runnable, route_main_agent
from src.graph_nodes.database_query_node import query_database
from src.graph_nodes.appointment_agent import appointment_agent_runnable, route_appointment_tools
from src.util.create_node import Assistant, back_to_main, create_tool_node
from src.util.appointment_tools import sensitive_tools, safe_tools


def create_graph() -> CompiledGraph:
    builder = StateGraph(State)

    # main agent
    builder.add_node("main_agent", Assistant(main_agent_runnable))
    builder.add_node("leave_specialized_agent", back_to_main)

    builder.set_entry_point("main_agent")
    builder.add_conditional_edges("main_agent", route_main_agent)
    builder.add_edge("leave_specialized_agent", "main_agent")

    # search agent
    builder.add_node("search_criteria_agent", search_criteria_agent)
    builder.add_node("query_database", query_database)

    builder.add_edge("search_criteria_agent", "query_database")
    builder.add_edge("query_database", "main_agent")

    # appointment agent
    builder.add_node("appointment_agent", Assistant(appointment_agent_runnable, True))
    builder.add_node("safe_appointment_tools", create_tool_node(safe_tools))
    builder.add_node("sensitive_appointment_tools", create_tool_node(sensitive_tools))

    builder.add_conditional_edges("appointment_agent", route_appointment_tools)
    builder.add_edge("safe_appointment_tools", "appointment_agent")
    builder.add_edge("sensitive_appointment_tools", "appointment_agent")

    # The checkpointer lets the graph persist its state
    memory = SqliteSaver.from_conn_string(":memory:")
    return builder.compile(
        checkpointer=memory,
        interrupt_before=["sensitive_appointment_tools"]
    )