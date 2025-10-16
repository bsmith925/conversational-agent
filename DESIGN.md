# Both Options essentially boil down to a RAG system.

Option 1 is described a lot more like Glean's product.

Option 2 is a more refined settings. Essentially more constraints, and calls out larger userbase support. There's the request for multi-turn, precision, and remembering past interactions to personalize responses. Improving based on user feedback or domain-specific data.



# 1. Architecture Overview
The system is built on a RAG (Retrieval-Augmented Generation) architecture and implemented using DSPys programming model. It decouples knowledge sources from the reasoning capabilities of the LLM, allowing for updates to the knowledge-base & code without having to re-train a model.

## Core Components
- User Interface: A Chainlit web interface for prototyping. Later, a custom React app where users interfact with the agent
- Orchestration/Service Layer: A backend service, FastAPI in this case primarily due to my familiarity. It manages the conversational flow. It will receive user queries, coordinate with other services, and formats the final response. We'll use DSPy programs/modules to house the logic.
- Retrieval System: Exposed as a DSPy tool/program (e.g. dspy.retrievers.embedding)
    - Vector Database: This is where we store numerical representations of document chunks (embeddings)
    - Ingestion Pipeline: An automated process that loads, chunks, and embeds new/updated documents
- A Generative Model: Some LLM that receives the user's query and the retrieved context to generate a human-like answer
- Chat history & cache: A key-value store (Redis, Valkey, etc) that maintains the conversation history for context in multi-turn dialogues

Flow:
User Query - UI - Orchestrator - Retrieve Context & Chat History -
Orchestrator Builds Prompt - LLM call - Orchestrator - UI - User

## Technical Tradeoffs
Component | Prototype | Rationale and Tradeoffs
Orchestration | DSPy | Robustness & Performance: Unlike the brittleness of something like LangChain, DSPy provides a programmatic abstraction for prompting LLMs. It provides prompt optimization as an empirical approach (MiProV2, GEPA, etc). There's a bit more up-front effort, but it results in a much more maintainable system.
UI | Chainlit | Purpose Built: Chainlit is designed for LLM apps, that has built-in features like conversational history, showing 'thinking' steps, and session management. This makes it a great accelerator while prototyping.
LLM | OpenRouter/Ollama | Self-Hosted/Private Cloud | Cost vs Privacy: An API is great for speed. Production demands a private endpoint/self-hosted for data security and control. 
Vector DB | ChromaDB(local) | Pinecone/Qdrant/pgvector | Scalability & Reliability: A local DB is great for prototyping but production needs something that is high-throughput, low-latency, and high-availability(if needed)

## Production & Stability Strategy
The path to production with DSPy is more suited to a feedback loop for user-driven features.

1. Infrastructure & Deployment:
- Containerize UI & Backend
    - Docker
        - Create clean dockerfiles for cached layers
        - SemVer image tagging
- Deployment
    - Kubernetes: a scalable platform
        - Auto-scaling
            - Horizontal Pod Auto-scaler(HPA) to scale with traffic
    - Managed Services vs Self-managed
        - Vector DB
        - Redis
