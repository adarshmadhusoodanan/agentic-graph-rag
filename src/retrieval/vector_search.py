"""Vector similarity search over ingested document chunks.

Query-time counterpart to ingestion/etl.py: embeds a natural-language query
and returns the nearest chunks from Qdrant.
"""

from typing import Any

from src.db.qdrant_vector_client import get_vector_client
from src.db.vertex_client import embed_texts
from src.utils.logger import get_logger

logger = get_logger(__name__)


def vector_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the `limit` chunks most semantically similar to `query`.

    Uses RETRIEVAL_QUERY (not RETRIEVAL_DOCUMENT) when embedding the query
    -- the asymmetric counterpart to how chunks were embedded at ingestion
    time. Each result is {"score", "doc_id", "chunk_index", "text"}.
    """
    [query_vector] = embed_texts([query], task_type="RETRIEVAL_QUERY")

    client = get_vector_client()
    results = client.search(query_vector, limit=limit)

    return [
        {
            "score": r["score"],
            "doc_id": r["payload"].get("doc_id"),
            "chunk_index": r["payload"].get("chunk_index"),
            "text": r["payload"].get("text"),
        }
        for r in results
    ]