"""Unit tests for the retrieval layer.

Every external dependency (Vertex AI, Qdrant, Neo4j) is mocked -- these
tests are about *our* logic: do we pass the right arguments, reshape
results correctly, and order/deduplicate fused evidence the way we claim
to? Tests that need live services would be integration tests, and would
make the suite slow, costly, and dependent on what happens to be ingested.
"""

from unittest.mock import MagicMock, patch

from src.retrieval.fusion import fuse
from src.retrieval.graph_search import graph_search
from src.retrieval.vector_search import vector_search


# ---------------------------------------------------------------------------
# vector_search
# ---------------------------------------------------------------------------


@patch("src.retrieval.vector_search.get_vector_client")
@patch("src.retrieval.vector_search.embed_texts")
def test_vector_search_embeds_query_with_retrieval_query_task_type(
    mock_embed, mock_get_client
):
    """The query must be embedded as a QUERY, not as a DOCUMENT.

    Getting this wrong doesn't raise -- it silently degrades retrieval
    quality -- so it's worth asserting explicitly.
    """
    mock_embed.return_value = [[0.1, 0.2]]
    mock_get_client.return_value.search.return_value = []

    vector_search("where does alice work")

    assert mock_embed.call_args.kwargs["task_type"] == "RETRIEVAL_QUERY"


@patch("src.retrieval.vector_search.get_vector_client")
@patch("src.retrieval.vector_search.embed_texts")
def test_vector_search_flattens_qdrant_payload(mock_embed, mock_get_client):
    """Qdrant's nested {payload: {...}} shape is flattened for callers."""
    mock_embed.return_value = [[0.1, 0.2]]
    mock_get_client.return_value.search.return_value = [
        {
            "id": "abc",
            "score": 0.87,
            "payload": {"doc_id": "d1", "chunk_index": 3, "text": "Alice works here."},
        }
    ]

    results = vector_search("alice", limit=1)

    assert results == [
        {"score": 0.87, "doc_id": "d1", "chunk_index": 3, "text": "Alice works here."}
    ]


@patch("src.retrieval.vector_search.get_vector_client")
@patch("src.retrieval.vector_search.embed_texts")
def test_vector_search_passes_limit_through(mock_embed, mock_get_client):
    mock_embed.return_value = [[0.1, 0.2]]
    mock_get_client.return_value.search.return_value = []

    vector_search("alice", limit=7)

    assert mock_get_client.return_value.search.call_args.kwargs["limit"] == 7


# ---------------------------------------------------------------------------
# graph_search
# ---------------------------------------------------------------------------


@patch("src.retrieval.graph_search.get_neo4j_client")
def test_graph_search_passes_query_parameters(mock_get_client):
    """Entity name and limit go through as bound parameters, not string
    interpolation -- the injection-safety property we rely on."""
    mock_client = MagicMock()
    mock_client.read.return_value = []
    mock_get_client.return_value = mock_client

    graph_search("Alice", limit=4)

    assert mock_client.read.call_args.kwargs == {"entity_name": "Alice", "limit": 4}


@patch("src.retrieval.graph_search.get_neo4j_client")
def test_graph_search_reshapes_records(mock_get_client):
    mock_client = MagicMock()
    mock_client.read.return_value = [
        {
            "entity": "Alice",
            "relationship": "works at",
            "neighbor": "Acme Corp",
            "neighbor_type": "ORGANIZATION",
        }
    ]
    mock_get_client.return_value = mock_client

    results = graph_search("alice")

    assert results == [
        {
            "entity": "Alice",
            "relationship": "works at",
            "neighbor": "Acme Corp",
            "neighbor_type": "ORGANIZATION",
        }
    ]


@patch("src.retrieval.graph_search.get_neo4j_client")
def test_graph_search_returns_empty_list_when_no_matches(mock_get_client):
    mock_client = MagicMock()
    mock_client.read.return_value = []
    mock_get_client.return_value = mock_client

    assert graph_search("nobody") == []


# ---------------------------------------------------------------------------
# fuse
# ---------------------------------------------------------------------------


def test_fuse_sorts_vector_results_by_score_descending():
    vector_results = [
        {"score": 0.4, "text": "low"},
        {"score": 0.9, "text": "high"},
        {"score": 0.6, "text": "mid"},
    ]

    fused = fuse(vector_results, [])

    assert [e["text"] for e in fused] == ["high", "mid", "low"]


def test_fuse_puts_graph_evidence_after_vector_evidence():
    """Graph results aren't similarity-ranked, so they follow the scored
    vector results rather than being interleaved with them."""
    vector_results = [{"score": 0.1, "text": "weak vector match"}]
    graph_results = [
        {"entity": "Alice", "relationship": "reports to", "neighbor": "Bob"}
    ]

    fused = fuse(vector_results, graph_results)

    assert [e["source"] for e in fused] == ["vector", "graph"]


def test_fuse_formats_graph_results_as_readable_text():
    graph_results = [
        {"entity": "Alice", "relationship": "reports to", "neighbor": "Bob"}
    ]

    fused = fuse([], graph_results)

    assert fused[0]["text"] == "Alice reports to Bob"
    assert fused[0]["score"] is None


def test_fuse_deduplicates_identical_text_keeping_vector_version():
    """When both sources produce the same text, keep the vector one -- it
    carries a score, so it's strictly more informative."""
    vector_results = [{"score": 0.8, "text": "Alice reports to Bob"}]
    graph_results = [
        {"entity": "Alice", "relationship": "reports to", "neighbor": "Bob"}
    ]

    fused = fuse(vector_results, graph_results)

    assert len(fused) == 1
    assert fused[0]["source"] == "vector"
    assert fused[0]["score"] == 0.8


def test_fuse_respects_max_items():
    vector_results = [{"score": 0.9, "text": "a"}, {"score": 0.8, "text": "b"}]
    graph_results = [{"entity": "X", "relationship": "rel", "neighbor": "Y"}]

    assert len(fuse(vector_results, graph_results, max_items=2)) == 2


def test_fuse_handles_both_sources_empty():
    assert fuse([], []) == []