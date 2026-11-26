# Policy Document Assistant — RAG Application

A production-grade **Retrieval-Augmented Generation (RAG)** system that lets employees ask natural language questions about company policy documents and get cited, accurate answers.

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- A free [Groq API key](https://console.groq.com) (or Gemini/OpenRouter)

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd policy-rag-assistant
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Add Policy PDFs
Place your PDF files in `data/pdfs/`. The travel policy is already included.

### 4. Run the Application
```bash
# Terminal 1: Start the main app (auto-indexes PDFs on startup)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 (optional): Start the MCP server
uvicorn app.mcp_server.server:app --host 0.0.0.0 --port 8001
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### 5. Run with Docker
```bash
docker build -t policy-rag-assistant .
docker run -p 8000:8000 --env-file .env policy-rag-assistant
```

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Chat UI /     │────▶│  FastAPI App      │────▶│  RAG Agent       │
│   REST API      │     │  (app/main.py)    │     │  (app/agent/)    │
└─────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                           │
                              ┌────────────────────────────┤
                              ▼                            ▼
                   ┌──────────────────┐       ┌──────────────────────┐
                   │  MCP Tool Server │       │   Vector Store       │
                   │  (port 8001)     │       │   ChromaDB           │
                   └──────────────────┘       └──────────────────────┘
                              │                            │
                              ▼                            ▼
                   ┌──────────────────┐       ┌──────────────────────┐
                   │  Groq LLM API   │       │   PDF Ingestion      │
                   │  (llama-3.1-8b) │       │   pdfplumber         │
                   └──────────────────┘       └──────────────────────┘
```

**Data Flow:**
1. PDFs → Ingested on startup → Split into chunks → Embedded (sentence-transformers) → Stored in ChromaDB
2. User question → Sanitized → MCP `search_policy` tool → Retrieve top-k chunks → LLM generates grounded answer
3. Answer returned with source citations (document name + page number)

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Suites
```bash
# Unit tests (no API key needed)
pytest tests/test_ingestion.py tests/test_security.py -v

# Security/injection tests
pytest tests/test_security.py -v

# Full agent integration tests (requires GROQ_API_KEY)
pytest tests/test_rag.py -v
```

### Run Evaluation (20 test cases)
```bash
python evaluation/evaluate.py
```

---

## 📊 Evaluation Report

The evaluation computes:
| Metric | Description | Threshold |
|--------|-------------|-----------|
| **Overall Accuracy** | % of test cases passed | ≥ 70% |
| **Faithfulness** | Answers grounded in retrieved docs | ≥ 75% |
| **Source Citation Rate** | Answers with citations | — |
| **Avg Latency** | Response time in ms | — |

Report saved to `evaluation/eval_report.json` after each run.

---

## 🔒 Security

- ✅ Prompt injection detection (regex + pattern matching)
- ✅ All user input treated as untrusted
- ✅ Document content sanitized before LLM context
- ✅ API keys in environment variables only
- ✅ PII masking in logs (emails, phones)
- ✅ Session ID validation

---

## 🛡️ Guardrails

| Guardrail | Setting | Config Key |
|-----------|---------|------------|
| LLM timeout | 30s | `LLM_TIMEOUT_SECONDS` |
| Max agent steps | 10 | `MAX_STEPS_PER_QUERY` |
| Max retries | 3 | `MAX_RETRIES` |
| Input max length | 2000 chars | Hardcoded |

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chat UI |
| `/health` | GET | Health check + index stats |
| `/chat` | POST | Ask a question |
| `/history/{session_id}` | GET | Get conversation history |
| `/history/{session_id}` | DELETE | Clear conversation |
| `/admin/reindex` | POST | Re-ingest PDFs |

### Chat Request Example
```json
POST /chat
{
  "query": "What class must domestic flights be booked in?",
  "session_id": "user-abc-123"
}
```

### Chat Response Example
```json
{
  "answer": "Domestic flights must be booked in economy class, unless exceptional circumstances apply. Approval for business class must be obtained from the CEO.\n\nSources:\n📄 travel_policy.pdf, Page 1",
  "session_id": "user-abc-123",
  "sources": [{"source": "travel_policy.pdf", "page": 1, "score": 0.92, "is_table": false}],
  "metrics": {"latency_ms": 1240, "input_tokens": 850, "output_tokens": 120},
  "flagged": false
}
```

---

## 🚀 Deployment

### Hugging Face Spaces (Recommended — Free)
1. Create a Space with Docker SDK
2. Push your code to GitHub
3. Connect the Space to your repo
4. Add `GROQ_API_KEY` to Space secrets

### Render / Fly.io
```bash
# Render: Connect GitHub repo, set env vars, done
# Fly.io:
fly launch
fly secrets set GROQ_API_KEY=your_key
fly deploy
```

### Rollback
```bash
# Git rollback
git revert HEAD
git push

# Docker rollback
docker pull policy-rag-assistant:previous-tag
docker run -p 8000:8000 --env-file .env policy-rag-assistant:previous-tag
```

---

## 📁 Project Structure

```
policy-rag-assistant/
├── app/
│   ├── core/
│   │   ├── config.py          # Settings from env vars
│   │   ├── logger.py          # Structured logging + PII masking
│   │   ├── pdf_ingestion.py   # PDF → Document chunks
│   │   ├── vector_store.py    # ChromaDB embeddings & search
│   │   ├── security.py        # Injection detection & sanitization
│   │   └── monitoring.py      # Metrics tracking
│   ├── mcp_server/
│   │   └── server.py          # MCP tool server (FastAPI)
│   ├── agent/
│   │   └── agent.py           # RAG agent with memory
│   └── main.py                # Main app + chat UI
├── data/
│   ├── pdfs/                  # Policy PDF files
│   └── vectordb/              # ChromaDB persistent store
├── tests/
│   ├── conftest.py
│   ├── test_ingestion.py      # PDF + vector store unit tests
│   ├── test_security.py       # Security & injection tests
│   └── test_rag.py            # 20 agent integration tests
├── evaluation/
│   ├── evaluate.py            # 20-case evaluation script
│   └── eval_report.json       # Generated evaluation report
├── .github/workflows/
│   └── ci.yml                 # GitHub Actions CI/CD
├── logs/                      # Runtime logs & metrics
├── .env.example               # Environment variable template
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── .gitignore
├── README.md
├── DESIGN.md
├── AI_USAGE.md
└── PROJECT.md                 # Progress tracker
```

---

## 🌍 Environment Variables

See [`.env.example`](.env.example) for all configuration options.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key |
| `LLM_MODEL` | No | `llama-3.1-8b-instant` | LLM model name |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Sentence transformer model |
| `TOP_K_RESULTS` | No | `5` | Retrieved chunks per query |
| `MIN_FAITHFULNESS_SCORE` | No | `0.75` | CI eval threshold |
