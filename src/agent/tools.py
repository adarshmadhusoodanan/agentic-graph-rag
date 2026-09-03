"""LangGraph agent tools: the functions the LLM can choose to call.

Each tool wraps one of the retrieval functions built earlier, formatted as
plain text for the LLM rather than raw dicts -- the model reasons over
text, and a clean paragraph reads better than a JSON dump of internal
field names it doesn't need (chunk_index, neighbor_type, etc.).

The docstrings below aren't just documentation -- they're the tool
descriptions the LLM actually sees when deciding which tool to call, so
they're written to disambiguate "use this one, not that one" as directly
as possible.
"""

from langchain_core.tools import tool

from src.retrieval.graph_search import graph_search
from src.retrieval.vector_search import vector_search


@tool
def search_documents(query: str) -> str:
    """Search indexed documents for text semantically similar to `query`.

    Use this for questions about what a document says -- descriptions,
    explanations, or facts phrased close to natural language. Not useful
    for "who is connected to X" questions; use search_graph for those.
    """
    results = vector_search(query, limit=5)
    if not results:
        return "No matching documents found."

    return "\n\n".join(f"(similarity: {r['score']:.2f}) {r['text']}" for r in results)


@tool
def search_graph(entity_name: str) -> str:
    """Look up facts connected to a named entity in the knowledge graph.

    Use this for relational questions -- "who does X report to", "what
    does X depend on", "where is X located" -- where the answer is a
    specific connection between named things, not a passage of text.
    entity_name should be the entity as named in the question (e.g.
    "Alice", "Acme Corp"), not a full sentence.
    """
    results = graph_search(entity_name, limit=10)
    if not results:
        return f"No graph connections found for '{entity_name}'."

    return "\n".join(
        f"{r['entity']} --[{r['relationship']}]--> {r['neighbor']}" for r in results
    )


AGENT_TOOLS = [search_documents, search_graph]