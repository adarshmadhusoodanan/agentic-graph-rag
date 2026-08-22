# Functional Requirements

These describe what the system must do.

FR-01 — Document ingestion

The system shall accept documents as input for ingestion.

FR-02 — Document chunking

The system shall split documents into smaller chunks suitable for embedding and retrieval.

FR-03 — Embedding generation

The system shall generate vector embeddings for each document chunk using Vertex AI.

FR-04 — Vector storage

The system shall store embeddings and associated metadata in Qdrant.

FR-05 — Entity extraction

The system shall identify relevant entities from documents.

Example:

    John
    Project Alpha
    PostgreSQL
    Authentication Service
    FR-06 — Relationship extraction

The system shall identify relationships between entities.

Example:

    John ──WORKED_ON──> Project Alpha
    Project Alpha ──USES──> PostgreSQL
    FR-07 — Knowledge graph construction

The extracted entities and relationships shall be stored in Neo4j.

FR-08 — Query processing

The API shall accept natural-language questions.

Example:

    POST /query
    {
    "query": "Who worked on Project Alpha?"
    }

FR-09 — Retrieval strategy selection

The agent shall determine whether the query requires:

    Vector Search
    Graph Search
    Vector + Graph Search
    FR-10 — Vector retrieval

The system shall retrieve semantically relevant document chunks from Qdrant.

FR-11 — Graph retrieval

The system shall retrieve relevant entities and relationships from Neo4j.

FR-12 — Result fusion

The system shall combine results from different retrieval strategies.

FR-13 — Answer generation

The LLM shall generate an answer using the retrieved context.

FR-14 — Source attribution

The response shall contain references to the source documents/chunks used to generate the answer.

FR-15 — Evaluation

The system shall support offline evaluation using RAGAS metrics.

# Non-Functional Requirements

These describe how well the system should operate.

NFR-01 — Performance

Query responses should complete within an acceptable latency target under normal workload.

For example:

    Target: < 5 seconds for normal queries

You can change this after benchmarking.

NFR-02 — Scalability

The architecture should support increasing numbers of:

    Documents
    Chunks
    Entities
    Relationships
    Concurrent queries

without requiring major architectural changes.

NFR-03 — Reliability

Failures in one retrieval mechanism should not unnecessarily crash the entire query pipeline.

For example:

    Qdrant unavailable
        ↓
    Agent detects failure
        ↓
    Graph retrieval / fallback
        ↓
    Return partial result or controlled error

NFR-04 — Maintainability

The system should use modular components:

    agent/
    retrieval/
    ingestion/
    db/
    api/
    eval/
    NFR-05 — Observability

The system should provide structured logging for:

    Query ID
    Agent decisions
    Tool calls
    Retrieval latency
    Number of retrieved results
    LLM latency
    Errors

NFR-06 — Security

Credentials must not be hardcoded.

Sensitive configuration must be provided through environment variables.

NFR-07 — Reproducibility

The local development environment should be reproducible using Docker Compose and uv.

NFR-08 — Testability

Core components should be independently testable.

NFR-09 — Extensibility

The architecture should allow additional retrieval tools to be added later.

For example:

        vector_search
        graph_search
        keyword_search
        SQL_search
        web_search