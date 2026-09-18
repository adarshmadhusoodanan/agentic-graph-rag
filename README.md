# Agentic Graph RAG

A Retrieval-Augmented Generation system that answers questions by combining
**semantic (vector) search** with **structured (graph) traversal**, orchestrated
by an LLM agent that decides which retrieval strategy a question actually needs.

## Why graph + vector?

Plain vector RAG is great at "what sounds similar to this question" but blind to
relationships: multi-hop questions like *"who else worked with X on project Y"*
or *"what depends on the component that broke"* aren't answerable by embedding
similarity alone, since they need graph traversal.

This project gives the agent both tools and lets it decide, per query, whether
it needs semantic recall, relational traversal, or both:

- **Qdrant** (vector store): fast approximate nearest-neighbour search over
  chunk embeddings, for "find things that mean something like this."
- **Neo4j** (graph store): entities and relationships extracted at ingestion
  time, for "find things connected to this in a specific way."
- **LangGraph agent** (Vertex AI Gemini): reasons about the query and calls
  `vector_search`, `graph_search`, or both, then reasons over the combined
  evidence to produce a final answer.

## Architecture

```
                     ┌───────────────────────┐
                     │   FastAPI  (/query)    │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │    LangGraph Agent      │
                     │   (Vertex AI Gemini)    │
                     └────┬──────────────┬─────┘
                          │              │
              ┌───────────▼──┐     ┌─────▼──────────┐
              │ vector_search │     │  graph_search   │
              │   (Qdrant)    │     │    (Neo4j)      │
              └───────┬───────┘     └────────┬────────┘
                      │                       │
                      └───────────┬───────────┘
                                  │
                         ┌────────▼─────────┐
                         │  Fusion / Rerank  │
                         └────────┬──────────┘
                                  │
                         ┌────────▼──────────┐
                         │ Synthesized Answer │
                         │    + Sources       │
                         └────────────────────┘

Ingestion (offline, run separately from query time):
  Raw docs -> chunk -> embed (Vertex AI) --------------> Qdrant
                    -> extract entities/relationships --> Neo4j
```

The agent doesn't call `fuse()` directly today; retrieval results reach it as
tool output in its own message history. `retrieval/fusion.py` exists as a
standalone, tested module for combining results outside the agent loop (for
example, in the evaluation pipeline or a future non-agentic retrieval mode).

## Tech stack

| Layer                | Tool                          | Why                                                            |
|-----------------------|-------------------------------|-----------------------------------------------------------------|
| LLM + embeddings      | Google Vertex AI (Gemini)     | Reasoning model for the agent, embedding model for ingestion    |
| Vector store          | Qdrant                        | Fast, self-hostable ANN search over chunk embeddings            |
| Graph store           | Neo4j                         | Entities/relationships for multi-hop, structured queries        |
| Agent orchestration   | LangGraph                     | Explicit, inspectable state machine for tool-calling agents     |
| API                   | FastAPI                       | Async, typed, auto-documented query endpoint                    |
| Evaluation            | RAGAS                         | Faithfulness / context-precision / context-recall scoring       |
| Dependency management | uv                            | Fast, reproducible Python environments                          |
| Local infra           | Docker Compose                | One-command local Qdrant + Neo4j for development                |

## Project structure

```
src/
├── config.py              # typed Settings, loaded once from env/.env
├── ingest.py               # CLI entrypoint: ingest a file or directory
├── agent/
│   ├── state.py             # LangGraph state schema (message history)
│   ├── tools.py              # search_documents, search_graph (LLM-callable)
│   ├── nodes.py               # agent_node (LLM+tools), tool_node
│   └── graph.py                # wires nodes into the tool-calling loop
├── api/
│   ├── main.py               # app creation, startup checks, router registration
│   ├── schemas.py             # request/response models
│   └── routers/
│       ├── health.py            # GET /health
│       └── query.py              # POST /query
├── db/
│   ├── neo4j_client.py       # Neo4j driver wrapper (read/write)
│   ├── vector_client.py       # Qdrant wrapper (ensure_collection/upsert/search)
│   └── vertex_client.py        # Vertex AI client (embeddings + generation)
├── eval/
│   └── evaluate_ragas.py      # offline RAGAS scoring against a labeled test set
├── ingestion/
│   └── etl.py                # chunk -> embed -> Qdrant; extract -> Neo4j
├── retrieval/
│   ├── vector_search.py      # query-time semantic search
│   ├── graph_search.py        # query-time graph traversal
│   └── fusion.py               # standalone evidence combiner (see note above)
└── utils/
    └── logger.py              # structured logging (human-readable / JSON)
tests/
├── test_retrieval.py         # vector_search, graph_search, fuse (mocked)
├── test_agent.py              # tools, routing, the full tool-calling loop (mocked)
└── test_api.py                  # HTTP layer via TestClient (mocked)
```

## Build roadmap

- [x] Repo scaffold (`pyproject.toml`, `.gitignore`, `LICENSE`)
- [x] Architecture docs (this file)
- [x] Docker Compose for Neo4j + Qdrant
- [x] Config module
- [x] Logging utility
- [x] Neo4j client
- [x] Qdrant client
- [x] Ingestion ETL pipeline
- [x] Ingestion CLI entrypoint
- [x] Vector search
- [x] Graph search
- [x] Fusion ranker
- [x] Agent state schema
- [x] Agent tools
- [x] Agent node functions
- [x] Agent graph (LangGraph wiring)
- [x] FastAPI app
- [x] RAGAS evaluation pipeline
- [x] Unit tests (retrieval, agent)
- [x] Integration tests (API)
- [x] Pytest config
- [x] Final polish & usage docs

## Getting started

### 1. Local infrastructure (Neo4j + Qdrant)

```bash
cp .env.example .env
# edit .env and set a real NEO4J_PASSWORD, and GOOGLE_CLOUD_PROJECT

docker compose up -d --wait
```

- Neo4j Browser: http://localhost:7474 (login `neo4j` / your `NEO4J_PASSWORD`)
- Qdrant Dashboard: http://localhost:6333/dashboard

> **Note:** Neo4j only applies `NEO4J_AUTH` the *first* time its data volume
> initializes. If you change `NEO4J_PASSWORD` in `.env` after the container
> has already started once, reset it with `docker compose down -v` (safe
> pre-ingestion; destroys local data) so it re-initializes with the new
> credentials.

### 2. Configure environment variables and Google Cloud auth

`.env` needs at minimum `GOOGLE_CLOUD_PROJECT` and `NEO4J_PASSWORD` (see
`.env.example` for the full list). Then authenticate so the Vertex AI SDK
can find credentials:

```bash
gcloud auth application-default login
```

### 3. Ingest a document

```bash
uv run python -m src.ingest path/to/document.txt
# or a whole directory of .txt/.md files:
uv run python -m src.ingest path/to/docs_dir/
```

Re-running on the same file updates it in place rather than duplicating it.

### 4. Run the API

```bash
uv run fastapi dev src/api/main.py
```

Open http://localhost:8000/docs for the interactive Swagger UI, or:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Where does Alice work?"}'
```

### Running tests

```bash
uv run pytest
```

All external services are mocked, so the suite needs no running containers,
no GCP credentials, and no ingested data.

### Running the evaluation

```bash
uv run python -m src.eval.evaluate_ragas
```

Scores the agent's answers on a small labeled test set (edit the
`sample_cases` list in `evaluate_ragas.py` to use your own questions and
reference answers). This makes real Vertex AI calls (a few cents per run),
unlike the test suite above.

## Known limitations and deliberate scope cuts

Called out here rather than left implicit, since knowing what's *not* handled
is as much a part of understanding this project as what is:

- **Document storage.** Raw source documents aren't stored anywhere durable,
  only derived data (chunks, extracted entities) lands in Qdrant/Neo4j. A
  production version would treat object storage (for example, GCS) as the
  source of truth, track a content hash per document for idempotent
  re-ingestion, and propagate a `source_uri` through to both stores so
  retrieved results can cite their origin document.
- **Entity resolution.** Entities merge on exact (case-insensitive substring)
  name match. "Alice" and "Alice Smith" become two separate graph nodes
  rather than one; there's no canonicalization or deduplication step.
- **One-hop graph traversal.** `graph_search` returns only the immediate
  neighborhood of a matched entity. Multi-hop (variable-length path)
  traversal is a natural extension, not included here.
- **Stateless API.** `/query` starts a fresh conversation on every request.
  Multi-turn memory would need a LangGraph checkpointer (Redis- or
  Postgres-backed).
- **RAGAS AnswerRelevancy is excluded.** It needs an embeddings model, not
  just an LLM judge, which is one more wrapper to introduce for one more
  metric. Faithfulness, ContextPrecision, and ContextRecall already cover
  grounding, ranking, and coverage.
- **`langchain-community` is pinned to `0.3.31`.** RAGAS 0.4.3 still imports
  a module that was removed from later `langchain-community` releases as
  part of that package's sunset. Remove the pin once a RAGAS release fixes
  this upstream.

## License

MIT, see [LICENSE](./LICENSE).