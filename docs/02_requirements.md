# Requirements Specification

## Functional Requirements

### FR-01 — Document Ingestion
The system shall accept supported documents as input for ingestion.

### FR-02 — Document Chunking
The system shall split documents into smaller chunks suitable for embedding and retrieval.

### FR-03 — Embedding Generation
The system shall generate embeddings for document chunks using Vertex AI.

### FR-04 — Vector Storage
The system shall store embeddings and associated metadata in Qdrant.

### FR-05 — Entity Extraction
The system shall identify relevant entities from ingested documents.

### FR-06 — Relationship Extraction
The system shall identify relationships between extracted entities.

### FR-07 — Knowledge Graph Construction
The system shall store extracted entities and relationships in Neo4j.

### FR-08 — Query Processing
The API shall accept natural-language questions through the query endpoint.

### FR-09 — Retrieval Strategy Selection
The agent shall determine whether the query requires vector retrieval, graph retrieval, or hybrid retrieval.

### FR-10 — Vector Retrieval
The system shall retrieve semantically relevant document chunks from Qdrant.

### FR-11 — Graph Retrieval
The system shall retrieve relevant entities, relationships, and graph-derived facts from Neo4j.

### FR-12 — Candidate Normalization
The system shall convert retrieval outputs into a consistent candidate structure containing text or facts and source metadata.

### FR-13 — Jev Semantic Search, Scoring, and Ranking
The system shall optionally score each retrieval candidate with TypeSafe Jev using the user query and candidate content.

### FR-14 — Jev Semantic Ranking
The system shall reorder candidates by relevance score, placing failed or unavailable scores after successfully scored candidates.

### FR-15 — Result Fusion
The system shall combine candidates from vector and graph retrieval when hybrid retrieval is selected.

### FR-16 — Context Preparation
The system shall prepare ranked and deduplicated context for answer generation.

### FR-17 — Answer Generation
The system shall use Vertex AI Gemini to generate an answer grounded in retrieved context.

### FR-18 — Source Attribution
The response shall contain source references for the retrieved documents or graph facts used in the answer.


### FR-15 — Multiple Jev Ranking Modes
The system should provide an abstraction that can support per-candidate semantic scoring,
pairwise comparisons, and cross-encoded query-candidate ranking when enabled by the
configured TypeSafe workflow.

### FR-16 — Context Selection
The system shall support selecting a bounded set of high-value candidates after Jev
scoring or ranking and before answer generation.

### FR-19 — Controlled Failure Handling
A failed Jev scoring request shall not automatically fail the entire query. The system shall log the failure and apply a defined fallback ordering.

### FR-20 — Evaluation
The system shall support offline evaluation of retrieval, reranking, and answer quality.

## Non-Functional Requirements

### NFR-01 — Performance
The system should provide acceptable query latency under normal workload. An initial target may be less than five seconds, subject to benchmarking.

### NFR-02 — Reranking Efficiency
The system should limit the number of candidates sent to Jev using configurable retrieval and reranking limits.

### NFR-03 — Scalability
The architecture should support increasing numbers of documents, chunks, entities, relationships, and concurrent queries.

### NFR-04 — Reliability
Failures in Qdrant, Neo4j, Gemini, or Jev should be handled using controlled errors, retries where appropriate, fallback behavior, or partial results.

### NFR-05 — Maintainability
The codebase shall separate API, agent, retrieval, reranking, ingestion, database, evaluation, and utility modules.

### NFR-06 — Observability
Structured logs should include query ID, retrieval strategy, tool calls, candidate counts, Jev scoring failures, retrieval latency, reranking latency, LLM latency, and errors.

### NFR-07 — Security
API keys and database credentials shall not be hardcoded and shall be supplied through environment variables.

### NFR-08 — Privacy
Sensitive document content shall not be sent to external services without an explicit data-handling decision and documented configuration.

### NFR-09 — Reproducibility
The local development environment shall be reproducible using Docker Compose and uv.

### NFR-10 — Testability
Retrieval, reranking, fusion, agent routing, and API behavior shall be independently testable.

### NFR-11 — Extensibility
The system should allow additional retrieval or scoring tools to be added without major changes to the agent interface.

### NFR-12 — Explainability
The system should expose retrieval methods, source metadata, and—when configured—reranking scores for debugging and evaluation.

> **TypeSafe alignment note:** The Jev capabilities referenced here are based on the
> official TypeSafe search-and-retrieval use cases: semantic search, query-to-candidate
> relevance scoring, pairwise reranking, cross-encoding, and context selection.
> Implementation-specific SDK methods and response fields must be verified against the
> installed TypeSafe SDK version.
