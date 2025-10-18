# Conversational AI Framework

A flexible, modular framework for building conversational AI applications with configurable memory, embeddings, and retrieval strategies. Built with FastAPI, DSPy, and pluggable storage backends.

## Overview

This framework provides a foundation for building any conversational AI application by abstracting core components like memory management, embedding generation, and retrieval strategies. It will support multiple backends and can be configured for different use cases from simple chatbots to enterprise knowledge assistants.


## Features

### Core Framework Capabilities
- **Pluggable Memory Systems** - Redis, PostgreSQL, or custom backends for conversation history
- **Multiple Embedding Providers** - SentenceTransformers, OpenAI, or custom embedding services
- **Flexible Retrieval Strategies** - Vector similarity, keyword search, hybrid approaches
- **DSPy Orchestration** - Programmatic, optimizable prompt management

### Application Features
- **Multi-Turn Conversations** - Maintains context across conversation turns
- **Source Attribution** - Every answer cites specific documents and pages
- **Real-Time Streaming** - Responses stream as they're generated
- **Advanced Query Understanding** - HyDE + keyword extraction for better retrieval

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- uv (Python package manager, for local development)

### Docker Setup (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd conversational-agent

# Set up environment variables
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY and any other settings

# Build and start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# Run document ingestion (one-time setup)
docker-compose exec backend python -m src.ingest.ingest

# View logs
docker-compose logs -f backend frontend
```

Access the UI at http://localhost:8080

### Local Development Setup

```bash
# Clone repository
git clone <repository-url>
cd conversational-agent

# Install dependencies
uv sync

# Start infrastructure (PostgreSQL + Redis)
docker-compose up -d postgres redis

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration (use localhost for DATABASE_HOST and REDIS_HOST)

# Run document ingestion
python src/ingest/ingest.py

# Start backend API
uvicorn src.backend.app.main:app --reload --port 8000

# Start frontend (separate terminal)
chainlit run src/frontend/app.py --port 8080
```

Access the UI at http://localhost:8080

## Documentation

**[Design Overview](DESIGN.md)** - Start here for project overview and documentation index

### Detailed Documentation

- **[System Design](SYSTEM_DESIGN.md)** - Architecture, components, technical decisions
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Step-by-step deployment instructions
- **[Roadmap](docs/ROADMAP.md)** - Roadmap
- **[Notes & Ideas](docs/Notes.md)** - Notes & Ideas
## Architecture

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
┌──────▼──────┐
│  RAG Service│  DSPy-based orchestration
│  (DSPy)     │  - Query Understanding (HyDE + keywords)
│             │  - Answer Generation (ChainOfThought)
└──────┬──────┘
       │
       ├─────────┬─────────┐
       │         │         │
┌──────▼──────┐ ┌▼────────┐ ┌▼────────┐
│ PostgreSQL  │ │  Redis  │ │   LLM   │
│ + pgvector  │ │ (Cache) │ │Provider │
└─────────────┘ └─────────┘ └─────────┘
```

### Framework Components

The framework is built with pluggable components that can be swapped based on your needs:

**Memory Systems:**
- `RedisDatabase` - Fast in-memory storage with TTL
- `PostgresDatabase` - Persistent storage with ACID guarantees
- Custom implementations via `DatabaseService` interface

**Embedding Providers:**
- `SentenceTransformersEmbedding` - Local embeddings (default)
- `OpenAIEmbedding` - Cloud-based embeddings
- Custom implementations via `EmbeddingService` interface

**Retrieval Strategies:**
- `HyDESearch` - Hypothetical Document Embeddings
- `VectorRetrieval` - Direct vector similarity
- Custom implementations via `RetrievalService` interface

## Technology Stack

### Core Framework
- **Backend:** FastAPI, Python 3.12+
- **Orchestration:** DSPy (LLM programming framework)
- **Language:** Python 3.12+ with async/await support

### Pluggable Components
- **Vector Storage:** PostgreSQL+pgvector, Pinecone, Qdrant, Weaviate
- **Memory/Cache:** Redis, PostgreSQL, in-memory
- **Embeddings:** SentenceTransformers, OpenAI, Cohere, custom models
- **LLM Providers:** OpenRouter, OpenAI, Anthropic, local models
- **Frontend:** Chainlit (prototype) → React/Vue/Angular (production)

## Project Structure

```
conversational-agent/
├── src/
│   ├── backend/           # FastAPI framework
│   │   └── app/
│   │       ├── api/       # API routes
│   │       ├── database/  # Database abstractions (PostgreSQL, Redis)
│   │       ├── embeddings/ # Embedding providers (SentenceTransformers, OpenAI)
│   │       ├── retrieval/ # Retrieval strategies (HyDE, Vector, custom)
│   │       ├── services/ # Business logic (chat, cache)
│   │       ├── models/    # Pydantic models
│   │       ├── dependencies/  # Dependency injection
│   │       └── core/      # Configuration, logging
│   ├── frontend/          # Chainlit UI (example implementation)
│   └── ingest/            # Document ingestion pipeline
├── docs/                  # Detailed documentation
├── DESIGN.md              # Design overview (start here)
├── SYSTEM_DESIGN.md       # Technical architecture
└── docker-compose.yaml    # Local infrastructure
```

## Key Components

### Framework Architecture

The framework is built around three core abstractions:

1. **Database** - Abstract storage interface
   - PostgreSQL implementation for persistent storage
   - Redis implementation for fast caching
   - Custom implementations 

2. **Embedding** - Abstract embedding generation
   - SentenceTransformers for local embeddings
   - OpenAI/Cohere for cloud-based embeddings
   - Custom models 

3. **Retrieva** - Abstract retrieval strategies
   - HyDESearch for hypothetical document embeddings
   - VectorRetrieval for direct similarity search
   - Custom strategies 

### RAG Pipeline (Example Implementation)

1. **Query Understanding** - Synthesizes enhanced search query
   - HyDE: Generates hypothetical answer for semantic matching
   - Keywords: Extracts key entities and concepts
   
2. **Retrieval** - Configurable retrieval strategy
   - Vector similarity search (PostgreSQL+pgvector) TODO: notes explaining nuance
   - Keyword-based search (TODO: add notes on search meethods and how SPLADE is a good hybrid for this)
   - Hybrid approaches (BM25 + SPLADE, BM25 + rerank, etc)
   - Custom retrieval logic

3. **Generation** - DSPy ChainOfThought answer generation
   - Inputs: Retrieved context + original question + chat history
   - Output: Comprehensive answer with source citations TODO: links to content on source/CDN/etc
   - Constraints: Answer only from provided context

4. **Streaming** - Real-time response delivery via WebSocket

### Session Management

- UUID-based session IDs
- Pluggable storage backends (Redis, PostgreSQL, custom)
- Configurable TTL (default: 1 hour)
- Retrieved context stored per message for traceability & multi-turn chat

## Performance

**Current (single instance):**
- Latency: ? seconds (first token)
- Throughput: ? concurrent users
- Database: TOOD: test at varying number of embeddings in db.

**Production target (with scaling):**
 TODO: eval and see what throughput we have
- p95 latency: < ? seconds
 TODO: table eval for per unit requests/sec by appraoch
- Concurrent users: 1,000-10,000
- Availability: 99.9%

## Development

### Running Tests

 TODO: finish setting up tests for frontend & ingest
```bash
# Unit tests
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/integration/

# All tests
uv run pytest
```

### Code Quality
TODO: fix mypy example command
```bash
# Linting
uv run ruff check src/

# Type checking
uv run mypy src/
```

## Deployment

### Local (Docker Compose)

The application is fully Dockerized with multi-stage builds (large backend image b/c of torch):

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```


## Configuration

Key environment variables (see `.env.example`):

```bash
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=vectordb

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=openrouter/google/gemini-2.5-pro

# RAG Settings
RAG_K=3                             # Top-k documents to retrieve
RETRIEVAL_SIMILARITY_THRESHOLD=0.3  # Minimum similarity score
CHAT_HISTORY_LIMIT=20               # Max messages to include
```

## Framework Benefits

**Core Advantages:**
- **Modular Architecture** - Swap components without changing application logic
- **Async-First Design** - Built for high concurrency and scalability
- **DSPy Integration** - Programmatic prompt optimization and evaluation
- **Production-Ready Patterns** - Dependency injection, service abstraction
- **Multiple Backends** - Choose storage and embedding providers based on needs

**Use Cases:**
- **Enterprise Knowledge Assistants** - RAG with document search
- **Customer Support Bots** - Multi-turn conversations with knowledge bases
- **Internal Chatbots** - Company documentation and FAQ systems
- **Custom Applications** - Build any conversational AI with your own logic

**Production Considerations:**
- Authentication & authorization (framework-agnostic)
- Comprehensive testing (built-in test patterns, unit & integration)
- Monitoring & alerting (pluggable observability)
- Security hardening (configurable security layers, e.g., IdP permission scopes from headers)

## Contributing

1. Review [System Design](SYSTEM_DESIGN.md) to understand framework architecture
2. Check [Gap Analysis](docs/GAPS.md) for priority areas
3. Follow code style (ruff configuration)
4. Write tests for new components and features
5. Update documentation for new abstractions
6. Add examples for new use cases 

## License
TODO: add license here
[Add your license here]


---

For detailed documentation, see [DESIGN.md](DESIGN.md) or explore the `docs/` directory.

## Framework Roadmap

### Current Status
- ✅ Core framework abstractions (Database, Embedding, Retrieval services)
- ✅ DSPy integration for query understanding and answer generation
- ✅ Async architecture with FastAPI
- ✅ Example implementations (HyDE, Vector retrieval, Redis/PostgreSQL storage)
- ✅ Working prototype with Chainlit UI

### TODO
- **Additional Retrieval Strategies** - BM25, hybrid search, reranking
- **More Embedding Providers** - OpenAI, Cohere, local model support
- **Advanced Memory Systems** - Conversation summarization, user profiling
- **Evaluation Framework** - Plug-in a combination of settings (embedding, retrieval, metric, etc)
- **Monitoring** - Otel

### Framework Extensions
- **Intent Recognition** - Dynamic conversation steering and clarification (pills).
- **Personalization** - User profiling and adaptive responses  
- **Multi-Modal Support** - Image, audio, and document processing
- **Agent Capabilities** - Tool use and external API integration
- **Advanced Caching** - Response caching and query optimization

- **DSPy** - LLM programming framework



