"""Combine vector and graph retrieval results into one ranked evidence list.

Vector search and graph search return structurally different things -- text
chunks with a cosine similarity score, versus entity/relationship/neighbor
facts with no comparable numeric score -- so this doesn't attempt a single
mathematical re-ranking across both (e.g. reciprocal rank fusion assumes
both rankings are over the same candidate set, which isn't true here).
Instead it normalizes both into one common "evidence" shape the agent can
reason over: scored vector matches first (best match first, a genuine
similarity ranking), then graph facts (exact, not similarity-ranked, so
ordering among them doesn't carry the same meaning).
"""

from typing import Any, Literal, TypedDict


class Evidence(TypedDict):
    source: Literal["vector", "graph"]
    text: str
    score: float | None


def _vector_result_to_evidence(result: dict[str, Any]) -> Evidence:
    return {"source": "vector", "text": result["text"], "score": result["score"]}


def _graph_result_to_evidence(result: dict[str, Any]) -> Evidence:
    text = f"{result['entity']} {result['relationship']} {result['neighbor']}"
    return {"source": "graph", "text": text, "score": None}


def fuse(
    vector_results: list[dict[str, Any]],
    graph_results: list[dict[str, Any]],
    max_items: int | None = None,
) -> list[Evidence]:
    """Merge vector + graph results into one evidence list.

    Vector evidence is sorted by score (descending) since it's a genuine
    similarity ranking; graph evidence follows, in the order graph_search
    returned it, since Cypher traversal order isn't a relevance ranking to
    begin with. Exact-duplicate text across both sources is deduplicated,
    keeping the vector version -- it carries a score, so it's strictly more
    informative than the graph version of the same fact.

    max_items truncates the final list (after ordering), to bound how much
    evidence gets fed into the agent's prompt.
    """
    vector_evidence = sorted(
        (_vector_result_to_evidence(r) for r in vector_results),
        key=lambda e: e["score"] or 0.0,
        reverse=True,
    )
    seen_text = {e["text"] for e in vector_evidence}

    graph_evidence = [
        evidence
        for r in graph_results
        if (evidence := _graph_result_to_evidence(r))["text"] not in seen_text
    ]

    fused = vector_evidence + graph_evidence
    return fused[:max_items] if max_items is not None else fused
