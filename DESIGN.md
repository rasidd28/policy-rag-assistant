# DESIGN.md — Architecture & Technical Decisions

## 1. System Overview

The Policy Document Assistant is a RAG (Retrieval-Augmented Generation) system built to answer employee questions about company policy documents. The system retrieves relevant document sections and uses an LLM to generate grounded, cited answers.

---

## 2. Architecture Decisions

### 2.1 Why ChromaDB?
- **Free and local** — no cloud database needed for development
- **Persistent storage** — data survives restarts
- **Easy to use** — Python-native, no separate server process required
- **Trade-off**: Not as scalable as Pinecone/Weaviate for large corpora (acceptable for this use case)

### 2.2 Why Sentence Transformers (all-MiniLM-L6-v2)?
- **Completely free** — no API calls, no cost
- **Runs locally** — no internet dependency during inference
- **Good quality** — 384-dimensional embeddings with strong semantic search
- **Fast** — optimized for CPU inference
- **Trade-off**: Lower quality than OpenAI ada-002 but zero cost

### 2.3 Why Groq (llama-3.1-8b)?
- **Free tier available** — generous rate limits for development
- **Very fast inference** — Groq's LPU hardware is significantly faster than GPU-based APIs
- **Good instruction following** — llama-3.1 follows system prompt constraints well
- **Trade-off**: Less capable than GPT-4, but sufficient for grounded Q&A over structured policy docs

### 2.4 Why pdfplumber over PyMuPDF?
- **Table extraction** — pdfplumber has superior table detection
- **No DLL issues** — works without native dependencies that might be blocked by security policies
- **Trade-off**: Slower for large PDFs, no image extraction (image-based pages fallback noted)

### 2.5 Why FastAPI for the MCP Server?
- **MCP compatibility** — FastAPI's auto-schema generation is similar to MCP tool definitions
- **Async native** — matches the agent's async architecture
- **Pydantic validation** — automatic input validation for all tool calls
- **OpenAPI docs** — built-in `/docs` endpoint for tool exploration

### 2.6 Why not LangGraph/LangChain Agent?
- **Transparency** — custom agent code is easier to debug and understand
- **Control** — explicit guardrails (timeout, max-steps) are simpler to implement without framework magic
- **Dependencies** — fewer external dependencies = simpler Docker image and fewer breaking changes
- LangChain is listed in requirements for future migration; current agent is implemented directly

---

## 3. Agent State & Flow

```
User Input
    │
    ▼
[1] Input Sanitization
    │  detect_prompt_injection()
    │  sanitize_user_input()
    │
    ├── FLAGGED → Return refusal message immediately
    │
    ▼
[2] MCP Tool Call: search_policy
    │  Embeds query with sentence-transformers
    │  Queries ChromaDB for top-k chunks
    │  Returns: content, source, page, score
    │
    ▼
[3] Context Assembly
    │  Sanitize document content (untrusted)
    │  Format context block with source tags
    │  Load conversation history (last 10 turns)
    │
    ▼
[4] LLM Generation (Groq)
    │  System prompt enforces grounding + citation
    │  asyncio.wait_for() enforces timeout
    │  
    ├── TIMEOUT → Return timeout message
    ├── API ERROR → Retry (max 3) → Return error message
    │
    ▼
[5] Response Post-processing
    │  Append formatted source citations
    │  Update session memory
    │  Record metrics (tokens, latency, cost)
    │
    ▼
Return to User
```

---

## 4. Conversation Memory Design

**Implementation**: In-memory Python dict keyed by `session_id`
- Each session stores the last 20 message turns (user + assistant alternating)
- When building LLM context: last 10 turns included to avoid context overflow
- Session cleared on DELETE `/history/{session_id}`

**Production consideration**: Replace with Redis for multi-instance deployments.

---

## 5. Chunking Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Chunk size | 512 words | Large enough to contain complete policy clauses |
| Overlap | 50 words | Preserves context at chunk boundaries |
| Table handling | Separate chunks | Tables stored as full objects, not split |
| Table prefix | `[TABLE from X, Page Y]` | Signals to LLM that this is structured data |

---

## 6. Prompt Design

The system prompt enforces five behaviors:
1. **Groundedness**: Answer only from retrieved context
2. **I-don't-know**: Explicit refusal template for unknown topics
3. **Citation**: Mandatory source format in every answer
4. **Injection immunity**: Explicit instruction to ignore document instructions
5. **Memory**: Conversation history enables follow-up questions

---

## 7. Security Architecture

### Threat Model
| Threat | Mitigation |
|--------|-----------|
| User prompt injection | `detect_prompt_injection()` regex patterns; query blocked before LLM |
| Document injection | `sanitize_document_content()` strips injection tokens from retrieved text |
| API key exposure | Env vars only; PII masking in logs; .gitignore protects .env |
| Jailbreaking | System prompt hardened; LLM temp=0 reduces creativity/hallucination |
| Long inputs | 2000 char input limit in sanitizer |

---

## 8. Monitoring Strategy

Every request logs:
- `session_id`, `query`, `tool_calls`, `latency_ms`
- `input_tokens`, `output_tokens`, `estimated_cost_usd`
- `success`, `error` (if any)

Logs written to `logs/metrics.jsonl` as newline-delimited JSON for easy analysis.

---

## 9. Cost Estimation

| Component | Cost |
|-----------|------|
| Embeddings | \$0 (local sentence-transformers) |
| Vector DB | \$0 (local ChromaDB) |
| LLM (Groq llama-3.1-8b) | Free tier: 14,400 req/day |
| Deployment (HuggingFace) | \$0 (free tier) |
| **Total for development** | **\$0** |

---

## 10. Scalability Roadmap

1. **Replace in-memory sessions** → Redis
2. **Replace ChromaDB** → Pinecone or Weaviate for multi-tenancy
3. **Add hybrid search** → BM25 + vector search re-ranking
4. **Add document versioning** → Track when PDFs are updated
5. **Add streaming responses** → Server-Sent Events for real-time typing
