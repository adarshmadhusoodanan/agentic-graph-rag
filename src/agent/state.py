"""LangGraph state schema for the agent.

Deliberately minimal: just the running message history. Tool-calling
agents in LangGraph don't need custom fields for intermediate retrieval
results -- a tool call's output becomes a ToolMessage appended to
`messages`, so the LLM sees prior retrieval results the same way it sees
everything else: as part of the conversation it's continuing.

Runaway tool-calling loops are bounded by LangGraph's own recursion_limit
at invoke time (set in agent/graph.py), not by anything in this state --
no need to duplicate that here.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]