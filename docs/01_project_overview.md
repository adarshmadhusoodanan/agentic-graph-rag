# Project Overview

Agentic Graph RAG is an intelligent Retrieval-Augmented Generation system that combines semantic vector retrieval and structured graph retrieval.

Unlike traditional RAG systems that rely only on vector similarity, this system allows an LLM-powered agent to dynamically determine whether a question requires:

Semantic retrieval
Graph traversal
Both retrieval strategies

The retrieved information is then combined, reranked, and passed to the LLM to generate a grounded answer with source references.

## Core technologies
        Component	            Technology
        API	                    FastAPI
        Agent	                LangGraph
        LLM	                    Google Vertex AI Gemini
        Embeddings	            Vertex AI
        Vector DB	            Qdrant
        Graph DB	            Neo4j
        Evaluation	            RAGAS
        Task/ETL	            Python
        Package Manager	        uv
        Infrastructure	        Docker Compose
        Testing	                Pytest

# Problem Statement

Traditional RAG systems primarily perform similarity-based retrieval.

For example:

"What is Kubernetes?"

A vector database can retrieve documents discussing Kubernetes effectively.

However, consider:

"Which services depend on the authentication service used by Project X?"

This requires understanding relationships such as:

            Project X
            ↓
            uses
            ↓
            Authentication Service
            ↓
            used_by
            ↓
            Service A
            Service B
            Service C

Vector similarity alone cannot reliably perform this type of multi-hop reasoning.

Therefore, the system combines:

            Vector Search
                +
            Graph Search
                +
            LLM Agent

to provide more accurate answers to both semantic and relational questions.

# Objectives

The main objectives are:

    Build a production-oriented Graph RAG architecture.
    Combine vector and graph retrieval.
    Allow an LLM agent to select retrieval strategies dynamically.
    Support multi-hop relationship queries.
    Provide grounded answers with sources.
    Separate ingestion from query-time processing.
    Evaluate retrieval and answer quality using RAGAS.
    Provide an API through FastAPI.
    Make the entire local infrastructure reproducible using Docker Compose.

# System Scope
    In scope
    Document ingestion
    Document chunking
    Embedding generation
    Vector storage
    Entity extraction
    Relationship extraction
    Knowledge graph construction
    Semantic retrieval
    Graph retrieval
    Retrieval fusion
    LLM-based reasoning
    Source attribution
    API access
    Evaluation
    Automated testing
    Out of scope

Initially, you can explicitly state that these are not supported:

Real-time document synchronization
Multi-user authentication
Fine-tuning Gemini
Distributed Qdrant/Neo4j clusters
Production-scale horizontal deployment
Automatic knowledge graph correction

This makes the project scope clear.