# Agentic Graph RAG

A Retrieval-Augmented Generation system that answers questions by combining
**semantic (vector) search** with **structured (graph) traversal**, orchestrated
by an LLM agent that decides which retrieval strategy a question actually needs.

## Why graph + vector?

Plain vector RAG is great at "what sounds similar to this question" but blind to
relationships: multi-hop questions like *"who else worked with X on project Y"*
or *"what depends on the component that broke"* aren't answerable by embedding
similarity alone — they need graph traversal.

This project gives the agent both tools and lets it decide, per query, whether
it needs semantic recall, relational traversal, or both:

- **Qdrant** (vector store) — fast approximate nearest-neighbour search over
  chunk embeddings, for "find things that mean something like this."
- **Neo4j** (graph store) — entities and relationships extracted at ingestion
  time, for "find things connected to this in a specific way."
- **LangGraph agent** (Vertex AI Gemini) — reasons about the query and calls
  `vector_search`, `graph_search`, or both, then fuses the results.

## Architecture
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
Raw docs -> chunk -> embed (Vertex AI) --------------> Qdrant -> extract entities/relationships --> Neo4j


## Tech stack

| Layer                 | Tool                          | Why                                                             |
|-----------------------|-------------------------------|-----------------------------------------------------------------|
| LLM + embeddings      | Google Vertex AI (Gemini)     | Reasoning model for the agent, embedding model for ingestion    |
| Vector store          | Qdrant                        | Fast, self-hostable ANN search over chunk embeddings            |
| Graph store           | Neo4j                         | Entities/relationships for multi-hop, structured queries        |
| Agent orchestration   | LangGraph                     | Explicit, inspectable state machine for tool-calling agents     |
| API                   | FastAPI                       | Async, typed, auto-documented query endpoint                    |
| Evaluation            | RAGAS                         | Faithfulness / relevancy / context-precision scoring offline    |
| Dependency management | uv                            | Fast, reproducible Python environments                          |
| Local infra           | Docker Compose                | One-command local Qdrant + Neo4j for development                |

## Project structure (target)

This grows commit by commit — see **Build roadmap** below for what actually
exists right now.

src/
├── config.py # env/settings loading
├── ingest.py # ingestion CLI entrypoint
├── agent/ # LangGraph agent: state, tools, nodes, graph
├── api/ # FastAPI app
├── db/ # Neo4j + Qdrant client wrappers
├── eval/ # RAGAS evaluation pipeline
├── ingestion/ # chunk/embed/extract ETL
├── retrieval/ # vector_search, graph_search, fusion
└── utils/ # logging, shared helpers
tests/ # API integration tests


## Build roadmap

- [x] Repo scaffold (`pyproject.toml`, `.gitignore`, `LICENSE`)
- [x] Architecture docs (this file)
- [x] Docker Compose for Neo4j + Qdrant
- [ ] Config module
- [ ] Logging utility
- [ ] Neo4j client
- [ ] Qdrant client
- [ ] Ingestion ETL pipeline
- [ ] Ingestion CLI entrypoint
- [ ] Vector search
- [ ] Graph search
- [ ] Fusion ranker
- [ ] Agent state schema
- [ ] Agent tools
- [ ] Agent node functions
- [ ] Agent graph (LangGraph wiring)
- [ ] FastAPI app
- [ ] RAGAS evaluation pipeline
- [ ] Unit tests (retrieval, agent)
- [ ] Integration tests (API)
- [ ] Pytest config
- [ ] Final polish & usage docs

## Getting started

### 1. Local infrastructure (Neo4j + Qdrant)

```bash
cp .env.example .env
# edit .env and set a real NEO4J_PASSWORD

docker compose up -d
```

- Neo4j Browser: http://localhost:7474 (login `neo4j` / your `NEO4J_PASSWORD`)
- Qdrant Dashboard: http://localhost:6333/dashboard

More steps land here as each subsystem is built — check the roadmap above
for current status.

## License

MIT — see [LICENSE](./LICENSE).