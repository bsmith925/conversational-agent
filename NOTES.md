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