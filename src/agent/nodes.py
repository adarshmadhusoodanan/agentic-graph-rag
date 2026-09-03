"""LangGraph node functions: the agent's reasoning step and its tool step.

Two nodes make up the loop this graph runs (wired together in graph.py):
  - agent_node: calls the LLM (with tools bound) on the current message
    history, returning either a final answer or one or more tool calls
  - tool_node: executes whatever tool calls agent_node's last response
    contained, appending the results as ToolMessages

graph.py adds the conditional edge that keeps routing
agent_node -> tool_node -> agent_node -> ... until agent_node responds
with no tool calls left to make.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode

from src.agent.state import AgentState
from src.agent.tools import AGENT_TOOLS
from src.config import settings

_SYSTEM_PROMPT = """You are a research assistant with two tools: \
search_documents (semantic search over indexed text) and search_graph \
(entity relationships in a knowledge graph). Use whichever tool -- or \
both -- the question actually needs. Cite what you found; don't answer \
from general knowledge if a tool could confirm it. If neither tool \
returns anything relevant, say so plainly instead of guessing.
"""


_llm = ChatGoogleGenerativeAI(
    model=settings.LLM_MODEL_NAME,
    vertexai=True,
    project=settings.GOOGLE_CLOUD_PROJECT,
    location=settings.GOOGLE_CLOUD_REGION,
    temperature=0.0,
)
_llm_with_tools = _llm.bind_tools(AGENT_TOOLS)


def agent_node(state: AgentState) -> dict:
    """Call the LLM on the current conversation, with tools bound.

    The system prompt is prepended on every call, not stored in state --
    it's a constant instruction, not part of the conversation history the
    tool-calling loop is appending to.
    """
    messages = [("system", _SYSTEM_PROMPT), *state["messages"]]
    response = _llm_with_tools.invoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(AGENT_TOOLS)
