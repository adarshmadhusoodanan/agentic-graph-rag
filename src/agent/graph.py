"""LangGraph wiring: turns agent_node and tool_node into a running agent.

Loop: START -> agent -> (tools, if the LLM made tool calls; else END)
             -> agent -> ...
repeating until the LLM responds with no tool calls left to make.
"""

from langgraph.graph import END, START, StateGraph

from src.agent.nodes import agent_node, tool_node
from src.agent.state import AgentState


def _should_continue(state: AgentState) -> str:
    """Route to tools if the last message requested any, else stop.

    LangGraph's own recursion_limit (passed at invoke time, not configured
    here) is the backstop against a runaway loop -- this function only
    decides one step at a time, not how many steps are allowed total.
    """
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent", _should_continue, {"tools": "tools", END: END}
    )
    graph.add_edge("tools", "agent")

    return graph.compile()


agent_graph = build_agent_graph()