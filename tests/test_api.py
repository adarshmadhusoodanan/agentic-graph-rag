"""Tests for the HTTP layer.

These go through FastAPI's TestClient so routing, request validation,
response serialization, and error handling are exercised as a real client
would hit them -- but the agent and both datastores are mocked, so the
suite stays fast and needs nothing running.

The startup checks in main.py's lifespan are patched out rather than
skipped: TestClient only runs lifespan inside a `with` block, so a test
that forgets it would silently never exercise startup at all.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.api.main import app


@pytest.fixture
def client():
    """TestClient with startup checks mocked out.

    Entered as a context manager so lifespan actually runs -- that's what
    makes the startup-check assertions below meaningful.
    """
    with patch("src.api.main.get_neo4j_client") as mock_neo4j, patch(
        "src.api.main.get_vector_client"
    ) as mock_vector:
        with TestClient(app) as test_client:
            test_client.mock_neo4j = mock_neo4j
            test_client.mock_vector = mock_vector
            yield test_client


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


def test_startup_verifies_both_datastores(client):
    """Fail-fast at startup is the whole point of the lifespan hook, so
    assert it actually ran rather than trusting it did."""
    assert client.mock_neo4j.return_value.verify_connectivity.called
    assert client.mock_vector.return_value.ensure_collection.called


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /query
# ---------------------------------------------------------------------------


def test_query_returns_agent_answer(client):
    with patch("src.api.routers.query.agent_graph") as mock_graph:
        mock_graph.invoke.return_value = {
            "messages": [AIMessage(content="Alice works at Acme Corp.")]
        }

        response = client.post("/query", json={"question": "Where does Alice work?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Alice works at Acme Corp."}


def test_query_passes_question_to_the_agent(client):
    with patch("src.api.routers.query.agent_graph") as mock_graph:
        mock_graph.invoke.return_value = {"messages": [AIMessage(content="answer")]}

        client.post("/query", json={"question": "Who does Alice report to?"})

    state = mock_graph.invoke.call_args[0][0]
    assert state["messages"][0].content == "Who does Alice report to?"


def test_query_applies_recursion_limit(client):
    """Without a recursion limit, a model that keeps calling tools would
    loop until something else gives out."""
    with patch("src.api.routers.query.agent_graph") as mock_graph:
        mock_graph.invoke.return_value = {"messages": [AIMessage(content="answer")]}

        client.post("/query", json={"question": "anything"})

    config = mock_graph.invoke.call_args.kwargs["config"]
    assert config["recursion_limit"] > 0


def test_query_rejects_missing_question(client):
    """Pydantic validation should reject this before any agent call."""
    with patch("src.api.routers.query.agent_graph") as mock_graph:
        response = client.post("/query", json={})

    assert response.status_code == 422
    assert not mock_graph.invoke.called


def test_query_returns_500_without_leaking_internals(client):
    """An agent failure must not surface a stack trace or internal error
    text to the caller."""
    with patch("src.api.routers.query.agent_graph") as mock_graph:
        mock_graph.invoke.side_effect = RuntimeError("neo4j password is hunter2")

        response = client.post("/query", json={"question": "anything"})

    assert response.status_code == 500
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text


# ---------------------------------------------------------------------------
# OpenAPI contract
# ---------------------------------------------------------------------------


def test_openapi_registers_both_routes(client):
    """Catches a router that was written but never included in main.py."""
    paths = client.get("/openapi.json").json()["paths"]

    assert "/health" in paths
    assert "/query" in paths