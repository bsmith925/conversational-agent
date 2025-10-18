# Framework Development Notes

## Evaluation & Optimization
- **LLM as a Judge** - Use LLM to evaluate response quality
- **NLI Evaluation** - Natural Language Inference to check if answers actually answer questions
  - Check entailment, contradiction, and neutral labels
  - Evaluate Q->A without context to verify answer quality
- **Flexible Evaluation** - Build system to evaluate anything and pick what works best
- **Hallucination Detection*** - LettuceDetect

## Memory & Conversation Management
- **Session Memory** - Look into different approaches
- **Conversation Summarization** - When session ends, summarize and add to history
  - Extract keywords, compact summaries
  - Queue-based processing for session cleanup
- **User Profiling** - Build profiles based on conversation patterns
  - Role-based: sales engineer, engineer, HR, finance
  - Specific roles: accounts receivable, etc.
  - Use for personalization

## UI/UX Improvements
- **Chat Bubbles/Pills** - Dynamic clarification system
  - Help clarify user intentions
  - Compact, powerful interface
  - Auto-generate clarification options
  - Allow users to steer conversation direction
- **Intent Recognition** - Better than generic chatbots
  - Explicit search interfaces for specific use cases
  - Research mode and other specialized interfaces
  - Intent matching system for better user experience

## Framework Philosophy
- **Specific Use Cases** - Better to design for specific use cases than generic agents
- **Explicit Tools** - Provide clear ways to search/query rather than hoping agents figure it out
- **Interface Variety** - Different interfaces for different modes (research, support, etc.)

## Action Items / TODOs

### Documentation & Readme
- **License**: Add a proper license file (e.g., MIT, Apache 2.0).
- **RAG Nuances**: Add notes explaining nuance of vector similarity search in PostgreSQL.
- **Search Methods**: Add notes on search methods like SPLADE as a hybrid approach.
- **Source Links**: Figure out how to implement links to content source/CDN.

### Testing & Quality
- **Test Coverage**: Finish setting up tests for frontend & ingest services.
- **Mypy Command**: Fix or verify the `mypy` example command.

### Performance & Evaluation
- **Embedding Scalability**: Test database performance with a varying number of embeddings.
- **Throughput Evaluation**: Evaluate system throughput and add metrics to README.
- **Request/Sec Evaluation**: Create a table for requests/sec based on different approaches.

### Framework Enhancements
- **Retrieval Strategies**: Implement BM25, hybrid search, and reranking.
- **Embedding Providers**: Add support for OpenAI, Cohere, and other local models.
- **Memory Systems**: Investigate advanced memory systems like conversation summarization and user profiling.
- **Evaluation Framework**: Build a pluggable evaluation framework to test combinations of settings (embedding, retrieval, metric, etc).
- **Monitoring**: Integrate OpenTelemetry (Otel) for monitoring.