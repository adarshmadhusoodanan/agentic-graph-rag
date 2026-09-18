# Query Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant Agent as LangGraph Agent
    participant Gemini as Vertex AI Gemini
    participant Qdrant as Qdrant
    participant Neo4j as Neo4j
    participant Normalizer as Candidate Normalizer
    participant Jev as TypeSafe Jev
    participant Fusion as Fusion
    participant Sources as Source Builder

    User->>API: POST /query
    API->>Agent: QueryRequest

    Agent->>Gemini: Analyze query
    Gemini-->>Agent: Retrieval strategy

    alt Vector Search Required
        Agent->>Qdrant: Semantic search
        Qdrant-->>Agent: Candidate chunks
    end

    alt Graph Search Required
        Agent->>Neo4j: Graph traversal
        Neo4j-->>Agent: Candidate graph facts
    end

    Agent->>Normalizer: Normalize retrieval candidates
    Normalizer-->>Agent: Common candidate list

    loop Each candidate
        Agent->>Jev: Score, compare, or cross-encode candidates
        Jev-->>Agent: Scores / ranking decisions
    end

    Agent->>Fusion: Merge, deduplicate, and rerank candidates
    Fusion-->>Agent: Ranked context

    Agent->>Gemini: Generate grounded answer
    Gemini-->>Agent: Draft answer

    Agent->>Sources: Attach source references
    Sources-->>Agent: Answer + sources

    Agent-->>API: QueryResponse
    API-->>User: Answer + Sources
```

## Failure Path

If a Jev request fails, the system should log the error and apply a configured fallback. The fallback may preserve the provider score/order, omit the failed candidate from the selected context, or continue with partial results depending on the ranking mode. The exact fallback behavior should be covered by tests.

> **TypeSafe alignment note:** The Jev capabilities referenced here are based on the
> official TypeSafe search-and-retrieval use cases: semantic search, query-to-candidate
> relevance scoring, pairwise reranking, cross-encoding, and context selection.
> Implementation-specific SDK methods and response fields must be verified against the
> installed TypeSafe SDK version.
