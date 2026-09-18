# Use Case Diagram

```mermaid
flowchart LR
    User((User))
    Admin((Administrator))
    JevService((TypeSafe Jev Service))
    GeminiService((Vertex AI Gemini))

    subgraph Agentic Graph RAG System
        UC1[Submit Query]
        UC2[Select Retrieval Strategy]
        UC3[Retrieve Semantic Context]
        UC4[Traverse Knowledge Graph]
        UC5[Normalize Candidates]
        UC6[Semantic Search and Score Candidates]
        UC7[Rank / Rerank Candidates]
        UC8[Fuse Retrieval Results]
        UC9[Generate Grounded Answer]
        UC10[View Sources]

        UC11[Upload Documents]
        UC12[Run Ingestion Pipeline]
        UC13[Generate Embeddings]
        UC14[Extract Entities and Relationships]
        UC15[Build Knowledge Graph]

        UC16[Run Evaluation]
    end

    User --> UC1
    User --> UC10

    UC1 --> UC2
    UC2 --> UC3
    UC2 --> UC4
    UC3 --> UC5
    UC4 --> UC5
    UC5 --> UC6
    UC6 --> UC7
    UC7 --> UC8
    UC8 --> UC9
    UC9 --> UC10

    UC6 -.-> JevService
    UC9 -.-> GeminiService
    UC14 -.-> GeminiService

    Admin --> UC11
    Admin --> UC12
    UC12 --> UC13
    UC12 --> UC14
    UC14 --> UC15
    Admin --> UC16
```

## Main Actors

- **User:** Submits questions and views grounded answers and sources.
- **Administrator:** Manages ingestion and evaluation workflows.
- **TypeSafe Jev Service:** Scores candidate relevance.
- **Vertex AI Gemini:** Supports agent reasoning, extraction, and answer generation.

> **TypeSafe alignment note:** The Jev capabilities referenced here are based on the
> official TypeSafe search-and-retrieval use cases: semantic search, query-to-candidate
> relevance scoring, pairwise reranking, cross-encoding, and context selection.
> Implementation-specific SDK methods and response fields must be verified against the
> installed TypeSafe SDK version.
