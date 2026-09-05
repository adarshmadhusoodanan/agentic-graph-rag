"""The agent's query endpoint."""

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from src.agent.graph import agent_graph
from src.api.schemas import QueryRequest, QueryResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["query"])

_RECURSION_LIMIT = 5


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """Run one question through the agent and return its final answer.

    Stateless by design: each request starts a fresh conversation. Multi-
    turn memory would need a LangGraph checkpointer (Redis/Postgres-backed)
    -- a deliberate scope cut for now, not an oversight.
    """
    try:
        result = agent_graph.invoke(
            {"messages": [HumanMessage(content=request.question)]},
            config={"recursion_limit": _RECURSION_LIMIT},
        )
    except Exception:
        logger.exception("Agent invocation failed for question: %r", request.question)
        raise HTTPException(status_code=500, detail="Failed to process the question.")

    answer = result["messages"][-1].content
    return QueryResponse(answer=answer)