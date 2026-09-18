# Ingestion Sequence Diagram

```mermaid
sequenceDiagram
    actor Admin
    participant CLI as Ingestion CLI
    participant Loader as Document Loader
    participant Chunker as Chunker
    participant Embedder as Vertex AI Embeddings
    participant Qdrant as Qdrant
    participant Extractor as Entity/Relation Extractor
    participant Gemini as Vertex AI Gemini
    participant Neo4j as Neo4j

    Admin->>CLI: Start ingestion
    CLI->>Loader: Load documents
    Loader-->>CLI: Raw documents

    CLI->>Chunker: Split documents
    Chunker-->>CLI: Document chunks

    loop Each chunk
        CLI->>Embedder: Generate embedding
        Embedder-->>CLI: Vector
        CLI->>Qdrant: Store vector + metadata
    end

    CLI->>Extractor: Extract entities and relationships
    Extractor->>Gemini: Analyze document
    Gemini-->>Extractor: Entities + relationships

    Extractor->>Neo4j: Create or merge entities
    Extractor->>Neo4j: Create or merge relationships

    CLI-->>Admin: Ingestion completed
```

## Reranking Note

Jev semantic search, scoring, and ranking are primarily query-time retrieval operations. It is not required for storing embeddings or constructing the initial knowledge graph. Ingestion should preserve sufficient text and source metadata so that retrieved vector chunks and graph-derived facts can later be scored by Jev.

> **TypeSafe alignment note:** The Jev capabilities referenced here are based on the
> official TypeSafe search-and-retrieval use cases: semantic search, query-to-candidate
> relevance scoring, pairwise reranking, cross-encoding, and context selection.
> Implementation-specific SDK methods and response fields must be verified against the
> installed TypeSafe SDK version.
