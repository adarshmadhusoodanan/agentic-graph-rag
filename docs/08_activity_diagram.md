# Query Activity Diagram

```mermaid
flowchart TD
    Start([User Query])
    Validate[Validate Query]
    Analyze[Gemini analyzes query]
    Decision{Which retrieval strategy?}

    Vector[Vector Search]
    Graph[Graph Search]
    Both[Vector + Graph Search]

    Normalize[Normalize Candidates]
    Rerank{Jev Semantic Ranking Enabled?}
    JevScore[Score and rank candidates with Jev]
    SkipRerank[Keep Retrieval Ordering]
    Fuse[Fuse and Deduplicate Results]

    Context{Sufficient Context?}
    Retry[Perform Additional Retrieval]
    Generate[Generate Grounded Answer]
    Sources[Attach Sources]
    Response([Return Answer + Sources])
    Error([Return Controlled Error])

    Start --> Validate
    Validate --> Analyze
    Analyze --> Decision

    Decision -->|Semantic| Vector
    Decision -->|Relational| Graph
    Decision -->|Complex| Both

    Vector --> Normalize
    Graph --> Normalize
    Both --> Normalize

    Normalize --> Rerank
    Rerank -->|Yes| JevScore
    Rerank -->|No| SkipRerank

    JevScore --> Fuse
    SkipRerank --> Fuse

    Fuse --> Context
    Context -->|Yes| Generate
    Context -->|No| Retry
    Retry --> Decision

    Generate --> Sources
    Sources --> Response
    Validate -->|Invalid| Error
```

## Activity Notes

- The agent chooses the retrieval path based on the query.
- Retrieval results are normalized before scoring.
- Jev semantic scoring/ranking is configurable and should be applied to a bounded candidate set.
- A Jev failure should use a configured fallback without unnecessarily terminating the whole request.
- If the available context is insufficient, the agent may perform additional retrieval or return a controlled insufficient-context response.

> **TypeSafe alignment note:** The Jev capabilities referenced here are based on the
> official TypeSafe search-and-retrieval use cases: semantic search, query-to-candidate
> relevance scoring, pairwise reranking, cross-encoding, and context selection.
> Implementation-specific SDK methods and response fields must be verified against the
> installed TypeSafe SDK version.
