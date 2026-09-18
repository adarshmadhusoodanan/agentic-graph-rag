# Class Diagram

```mermaid
classDiagram

    class QueryRequest {
        +str query
        +int top_k
        +int rerank_candidates
        +bool enable_reranking
    }

    class QueryResponse {
        +str answer
        +list sources
        +list retrieval_methods
        +dict metadata
    }

    class AgentState {
        +str query
        +str retrieval_strategy
        +list vector_results
        +list graph_results
        +list normalized_candidates
        +list reranked_results
        +list fused_context
        +list sources
        +str final_answer
    }

    class VectorSearchTool {
        +search(query, top_k)
    }

    class GraphSearchTool {
        +search(query)
        +traverse(entity)
    }

    class QdrantClient {
        +create_collection()
        +upsert()
        +search()
    }

    class Neo4jClient {
        +execute_query()
        +create_node()
        +create_relationship()
    }

    class EmbeddingService {
        +embed(text)
    }

    class CandidateNormalizer {
        +normalize_vector_results(results)
        +normalize_graph_results(results)
    }

    class JevReranker {
        +rerank(query, candidates)
        +score_candidate(query, candidate)
    }

    class FusionRanker {
        +merge_results()
        +deduplicate()
        +prepare_context()
    }

    class LLMService {
        +generate(prompt)
        +structured_output()
    }

    class AgentGraph {
        +run(state)
        +route_query()
        +retrieve()
        +rerank()
        +generate_answer()
    }

    QueryRequest --> AgentGraph
    AgentGraph --> AgentState
    AgentGraph --> VectorSearchTool
    AgentGraph --> GraphSearchTool
    VectorSearchTool --> QdrantClient
    GraphSearchTool --> Neo4jClient
    AgentGraph --> CandidateNormalizer
    CandidateNormalizer --> JevReranker
    AgentGraph --> FusionRanker
    AgentGraph --> LLMService
    EmbeddingService --> QdrantClient
```

## Design Note

The exact class names and method signatures should be synchronized with the implementation once the project modules are created. The diagram represents the intended responsibility boundaries.

> **TypeSafe alignment note:** The Jev capabilities referenced here are based on the
> official TypeSafe search-and-retrieval use cases: semantic search, query-to-candidate
> relevance scoring, pairwise reranking, cross-encoding, and context selection.
> Implementation-specific SDK methods and response fields must be verified against the
> installed TypeSafe SDK version.
