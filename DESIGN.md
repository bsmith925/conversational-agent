# Design Document: A Flexible Framework for Conversational AI

## 1. Intro

This document outlines the architecture of a modular, production-ready conversational AI framework. It is designed to power enterprise-grade applications, such as knowledge assistants, by enabling natural language interaction with large document collections. The framework prioritizes flexibility, scalability, and maintainability, supporting multi-turn conversations, context-aware retrieval, and continuous optimization.

## 2. Core Problem: Unifying Knowledge Retrieval Systems

The initial requirement was to prototype an "Enterprise Knowledge Assistant" or a "Dynamic Knowledge Querying" system. Both scenarios are fundamentally advanced Retrieval-Augmented Generation (RAG) applications. Instead of building a single-purpose application, I  designed a flexible framework capable of supporting both, and many other conversational AI use cases. The initial prototype is an Enterprise Knowledge Assistant, demonstrating the framework's capabilities with a curated knowledge base.

## 3. System Architecture

The system is designed as a set of decoupled services, orchestrated by a central backend.

```
┌─────────────┐
│  Chainlit   │  User Interface (WebSocket streaming)
│   Frontend  │
└──────┬──────┘
       │
┌──────▼──────┐
│   FastAPI   │  API Layer (async, REST + WebSocket)
│   Backend   │
└──────┬──────┘
       │
┌──────-──────┐
│  RAG Service│  DSPy-based orchestration
│  (DSPy)     │  - Query Understanding (HyDE + keywords)
│             │  - Answer Generation (ChainOfThought)
└──────┬──────┘
       │
       ├─────────┬────────--─┐
       │         │           │
┌──────-──────┐ ┌-────────┐ ┌-────────┐
│ PostgreSQL  │ │  Redis  │ │   LLM   │
│ + pgvector  │ │ (Cache) │ │Provider │
└─────────────┘ └─────────┘ └─────────┘
```

### Technology Choices

-   **FastAPI**: Chosen for the backend due to its high performance and my familiarity with it. It enables faster prototyping compared to a more heavyweight framework like Django, without sacrificing production-readiness.
-   **Chainlit**: Used for the frontend to accelerate prototype development. Its Python-based nature allows for rapid iteration and keeps the entire stack within a single language, simplifying the development process.
-   **PostgreSQL**: Selected for its maturity, reliability, and robust feature set. My familiarity with it allows for rapid development, while its support for extensions like `pgvector` is critical for the RAG implementation. It also offers a clear path to high availability and low-latency performance in production, with well-established patterns for migrations and scalability.
-   **Redis**: Implemented for session management and caching. Its in-memory data structure provides the low-latency performance required for a responsive user experience. My familiarity with Redis makes for quick implementation, and its support for clustering and persistence provides a clear path to a high-availability cache layer with necessary fail-safes for production.

### Pluggable Modules

The framework's modularity is achieved through a set of abstractions that allow concrete implementations (modules) to be swapped without altering the core application logic:

-   **Storage Abstraction (`DatabaseService`)**: Defines the interface for data storage. The framework includes modules for PostgreSQL (persistent storage) and Redis (caching and session management).
-   **Embedding Abstraction (`EmbeddingService`)**: Defines the interface for creating vector embeddings. The default module uses `SentenceTransformers` for high-quality local embeddings.
-   **Retrieval Abstraction (`RetrievalService`)**: Defines the interface for finding relevant documents. This allows for plugging in different retrieval modules, such as those for semantic search, keyword-based search, or hybrid models.

## 4. Core Implementation Strategies

### DSPy for Programmatic Optimization

I chose DSPy over alternatives like LangChain for its programmatic approach to prompt engineering. DSPy allows for defining LLM workflows as code modules that can be optimized automatically. This makes the system more maintainable, testable, and adaptable over time without manual prompt tuning. For example, the query understanding engine is a DSPy module:

```python
class QueryUnderstandingEngine(dspy.Module):
    def __init__(self):
        self.extract_keywords = dspy.Predict(ExtractKeywords)
        self.generate_hyde = dspy.Predict(GenerateHypotheticalAnswer)
```

### RAG Pipeline

The core RAG workflow consists of four stages:

1.  **Query Understanding**: The user's query is enriched using DSPy. A hypothetical answer (**HyDE**) is generated to improve the semantic richness of the query and keywords are extracted for targeted retrieval. Chat history is used to resolve context and pronouns.
2.  **Retrieval**: The enriched query vector is used to perform a similarity search against the document embeddings stored in PostgreSQL (`pgvector`).
3.  **Generation**: The retrieved documents, the original question, and the chat history are passed to a `dspy.ChainOfThought` module, which generates a comprehensive, context-aware answer.
4.  **Streaming**: The generated response is streamed to the user in real-time via WebSockets for an interactive experience.

### Session Management

Conversational context is maintained through UUID-based sessions managed in Redis, providing fast access to chat history. This enables multi-turn conversations and ensures that follow-up questions are understood in context. Sessions have a configurable TTL (defaulting to one hour) to manage memory usage effectively.

## 5. Production Readiness Strategy

The framework is designed for scalable, secure, and reliable operation in a production environment.

### Scalability & Performance

The architecture is built for horizontal scaling. The backend FastAPI application is stateless, allowing multiple instances to run behind a load balancer. Performance is further enhanced by using `async/await` throughout the stack, database connection pooling, and a Redis cache for session data and frequently accessed content. PostgreSQL can be scaled with read replicas to handle high query loads.

### Observability

Comprehensive observability is achieved through structured logging (JSON) and health checks. Structured logs provide detailed request/response tracing and performance metrics, making it easy to debug issues and monitor system behavior. A dedicated `/health` endpoint checks the status of all critical dependencies (Database, Cache, LLM provider), enabling automated recovery and intelligent traffic routing in a containerized environment (e.g., Kubernetes).

### Security

Security would be handled via a framework-agnostic approach. The design accounts for authentication and authorization hooks, which would allow integration with any Identity Provider (IdP). While data is already isolated by session and environment variables are used for secure configuration, this design would support standard enterprise security patterns like role-based access control and configurable CORS policies once fully implemented.

### Deployment & DevOps

A Docker-first approach is used, with multi-stage builds to create optimized container images. The included `docker-compose.yaml` file enables a complete local development environment that mirrors production. For production deployments, Infrastructure as Code (IaC) tools like Terraform or Helm charts for Kubernetes are recommended for enabling reproducible and automated deployments. Database migrations are supported to manage schema changes over time.

## 6. Future Roadmap

My framework is extensible, with a clear path for future enhancements:

-   **Immediate Goals**: Integrate alternative retrieval strategies (e.g., BM25 for hybrid search), add more embedding providers & approaches (OpenAI, Cohere, WordLLama), text splitting techniques, and build out a formal evaluation framework for quality assessment.
-   **Advanced Features**: Develop agent-like capabilities for tool use, introduce intent recognition for more sophisticated conversation steering, and explore multi-modal support for processing images and other document types.
