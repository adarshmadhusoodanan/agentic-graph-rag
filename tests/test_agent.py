"""Unit tests for the agent layer: tools, routing, and the graph loop.

The LLM itself is mocked throughout -- these tests verify the machinery
around it (does the right tool get called, does the loop terminate, does
tool output reach the LLM), not the model's judgment about which tool to
pick. That's what src/eval/evaluate_ragas.py measures, and it needs a real
model to mean anything.
"""

from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from src.agent.graph import _should_continue, agent_graph
from src.agent.tools import AGENT_TOOLS, search_documents, search_graph


# ---------------------------------------------------------------------------
# Tool metadata -- this is what the LLM sees when choosing a tool
# ---------------------------------------------------------------------------


def test_both_tools_are_registered():
    assert {t.name for t in AGENT_TOOLS} == {"search_documents", "search_graph"}


def test_tools_expose_descriptions_to_the_llm():
    """Descriptions come from docstrings and are the LLM's only basis for
    choosing between the tools, so an empty one would quietly hurt tool
    selection without failing anything."""
    for tool in AGENT_TOOLS:
        assert tool.description.strip()


def test_tool_arg_schemas_match_their_signatures():
    assert "query" in search_documents.args_schema.model_json_schema()["properties"]
    assert "entity_name" in search_graph.args_schema.model_json_schema()["properties"]


# ---------------------------------------------------------------------------
# Tool behavior
# ---------------------------------------------------------------------------


@patch("src.agent.tools.vector_search")
def test_search_documents_formats_results_as_text(mock_vector_search):
    """Tools return text, not dicts -- the LLM reasons over prose, and
    internal field names like chunk_index would just be noise."""
    mock_vector_search.return_value = [
        {"score": 0.91, "doc_id": "d1", "chunk_index": 0, "text": "Alice works at Acme."}
    ]

    result = search_documents.invoke({"query": "where does alice work"})

    assert isinstance(result, str)
    assert "Alice works at Acme." in result
    assert "0.91" in result


@patch("src.agent.tools.vector_search")
def test_search_documents_handles_no_results(mock_vector_search):
    """An empty result must read as a clear statement, not an empty string
    -- the LLM needs something to reason about."""
    mock_vector_search.return_value = []

    result = search_documents.invoke({"query": "nothing matches this"})

    assert result.strip()
    assert "No matching documents" in result


@patch("src.agent.tools.graph_search")
def test_search_graph_formats_relationships_readably(mock_graph_search):
    mock_graph_search.return_value = [
        {
            "entity": "Alice",
            "relationship": "reports to",
            "neighbor": "Bob",
            "neighbor_type": "PERSON",
        }
    ]

    result = search_graph.invoke({"entity_name": "Alice"})

    assert "Alice" in result and "Bob" in result and "reports to" in result


@patch("src.agent.tools.graph_search")
def test_search_graph_handles_no_results(mock_graph_search):
    mock_graph_search.return_value = []

    result = search_graph.invoke({"entity_name": "Nobody"})

    assert "Nobody" in result


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def test_should_continue_routes_to_tools_when_tool_calls_present():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "search_documents", "args": {"query": "x"}, "id": "1"}
                ],
            )
        ]
    }

    assert _should_continue(state) == "tools"


def test_should_continue_ends_when_no_tool_calls():
    state = {"messages": [AIMessage(content="Here is the final answer.")]}

    assert _should_continue(state) == END


# ---------------------------------------------------------------------------
# The full loop
# ---------------------------------------------------------------------------


@patch("src.agent.tools.vector_search")
@patch("src.agent.nodes._llm_with_tools")
def test_agent_loop_runs_tool_then_answers(mock_llm, mock_vector_search):
    """The core contract: question -> tool call -> tool result -> answer.

    Asserts the full message trace, so a break anywhere in the loop (tool
    result never reaching the LLM, graph not looping back) shows up here.
    """
    mock_llm.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_documents",
                    "args": {"query": "Where does Alice work?"},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="Alice works at Acme Corp."),
    ]
    mock_vector_search.return_value = [
        {"score": 0.9, "doc_id": "d1", "chunk_index": 0, "text": "Alice works at Acme Corp."}
    ]

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Where does Alice work?")]}
    )

    kinds = [type(m).__name__ for m in result["messages"]]
    assert kinds == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    assert result["messages"][-1].content == "Alice works at Acme Corp."
    assert mock_llm.invoke.call_count == 2


@patch("src.agent.nodes._llm_with_tools")
def test_agent_loop_answers_directly_without_tools(mock_llm):
    """If the LLM answers without calling a tool, the graph must stop
    immediately rather than looping."""
    mock_llm.invoke.return_value = AIMessage(content="No tools needed for this.")

    result = agent_graph.invoke({"messages": [HumanMessage(content="hello")]})

    assert [type(m).__name__ for m in result["messages"]] == [
        "HumanMessage",
        "AIMessage",
    ]
    assert mock_llm.invoke.call_count == 1


@patch("src.agent.tools.graph_search")
@patch("src.agent.tools.vector_search")
@patch("src.agent.nodes._llm_with_tools")
def test_agent_loop_handles_multiple_tool_calls_in_one_turn(
    mock_llm, mock_vector_search, mock_graph_search
):
    """A question needing both tools should produce both ToolMessages
    before the LLM is asked again."""
    mock_llm.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "search_documents", "args": {"query": "Alice"}, "id": "c1"},
                {"name": "search_graph", "args": {"entity_name": "Alice"}, "id": "c2"},
            ],
        ),
        AIMessage(content="Combined answer from both sources."),
    ]
    mock_vector_search.return_value = [
        {"score": 0.8, "doc_id": "d1", "chunk_index": 0, "text": "Alice works at Acme."}
    ]
    mock_graph_search.return_value = [
        {
            "entity": "Alice",
            "relationship": "reports to",
            "neighbor": "Bob",
            "neighbor_type": "PERSON",
        }
    ]

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content="Where does Alice work and who does she report to?")]}
    )

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 2
    assert result["messages"][-1].content == "Combined answer from both sources."