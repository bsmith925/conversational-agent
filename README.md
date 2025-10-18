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

- **[Design Document](DESIGN.md)**: The primary source for architecture, technical decisions, and production strategy.
- **[Development Notes](NOTES.md)**: A collection of raw notes, ideas, and future action items.

## Technology Stack

### Core Framework
- **Backend:** FastAPI, Python 3.12+
- **Orchestration:** DSPy
- **Language:** Python 3.12+ with async/await support

### Pluggable Components
- **Vector Storage:** PostgreSQL with `pgvector`
- **Memory/Cache:** Redis
- **Embeddings:** SentenceTransformers (default), OpenAI, Cohere
- **LLM Providers:** OpenRouter, OpenAI, Anthropic, local models
- **Frontend:** Chainlit (for rapid prototyping)

## Project Structure

```
conversational-agent/
├── src/
│   ├── backend/           # FastAPI application
│   │   └── app/
│   │       ├── api/       # API routes
│   │       ├── database/  # Storage abstractions (PostgreSQL, Redis)
│   │       ├── embeddings/ # Embedding provider abstractions
│   │       ├── retrieval/ # Retrieval strategy abstractions
│   │       ├── services/  # Core business logic
│   │       ├── models/    # Pydantic models
│   │       ├── dependencies/  # Dependency injection
│   │       └── core/      # Configuration and logging
│   │   ├── frontend/          # Chainlit UI
│   │   └── ingest/            # Document ingestion pipeline
│   ├── docs/                  # Supporting documentation
│   ├── DESIGN.md              # Core architecture and design document
│   └── docker-compose.yaml    # Local development infrastructure
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific part of the application
uv run pytest src/backend/tests/
```

### Code Quality

```bash
# Linting
uv run ruff check src/

# Type checking
uv run mypy src/
```

## Contributing

1. Review the **[Design Document](DESIGN.md)** to understand the framework architecture.
2. Check for open tasks in **[Development Notes](NOTES.md)** or create a GitHub Issue.
3. Follow the existing code style (enforced by `ruff`).
4. Write tests for new components and features.
5. Update documentation for any new abstractions or features.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

For detailed documentation, see the files linked in the [Documentation](#documentation) section.

## Framework Roadmap

### Current Status
- ✅ Core framework abstractions (Database, Embedding, Retrieval services)
- ✅ DSPy integration for query understanding and answer generation
- ✅ Async architecture with FastAPI
- ✅ Example implementations (HyDE, Vector retrieval, Redis/PostgreSQL storage)
- ✅ Working prototype with Chainlit UI

### Next Steps

The near-term roadmap and long-term goals are tracked in the **[Development Notes](NOTES.md)**. Key areas for future work include:

- **Advanced Retrieval**: Implementing strategies like hybrid search and reranking.
- **Expanded Integrations**: Adding more embedding providers and memory systems.
- **Evaluation & Monitoring**: Building a formal evaluation framework and integrating OpenTelemetry.
- **Agent Capabilities**: Developing features for tool use and intent recognition.



