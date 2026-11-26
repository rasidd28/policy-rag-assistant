
---

## 📍 Current Status: **PHASE 1 COMPLETE — Ready for setup & testing**

**Last updated:** 2026-11-26  
**Conversation ID:** `097a6a9b-6d9a-4429-9775-dd0de8fe18eb`  
**Project Directory:** `C:\Users\Admin\Desktop\rag`

---

## ✅ What Has Been Done (Complete)

### Phase 1: Full Project Build ✅
All code has been written. The project is complete in structure. Here's everything that was built:

| File | Status | Description |
|------|--------|-------------|
| `app/core/config.py` | ✅ Done | Settings from env vars (pydantic-settings) |
| `app/core/logger.py` | ✅ Done | Structured logging with PII masking |
| `app/core/pdf_ingestion.py` | ✅ Done | PDF → chunks, table extraction via pdfplumber |
| `app/core/vector_store.py` | ✅ Done | ChromaDB + sentence-transformers embeddings |
| `app/core/security.py` | ✅ Done | Prompt injection detection + input sanitization |
| `app/core/monitoring.py` | ✅ Done | Token tracking, latency, cost estimation |
| `app/mcp_server/server.py` | ✅ Done | MCP tool server (FastAPI, port 8001) |
| `app/agent/agent.py` | ✅ Done | RAG agent with memory, guardrails, MCP calls |
| `app/main.py` | ✅ Done | Main app with chat UI + REST API (port 8000) |
| `tests/test_rag.py` | ✅ Done | 20 agent integration tests |
| `tests/test_ingestion.py` | ✅ Done | PDF + vector store unit tests |
| `tests/test_security.py` | ✅ Done | Security + injection tests |
| `evaluation/evaluate.py` | ✅ Done | 20-case evaluation with metrics |
| `.github/workflows/ci.yml` | ✅ Done | GitHub Actions CI/CD pipeline |
| `Dockerfile` | ✅ Done | Multi-stage Docker build |
| `.env.example` | ✅ Done | Environment variables template |
| `requirements.txt` | ✅ Done | All Python dependencies |
| `pyproject.toml` | ✅ Done | pytest + ruff + black config |
| `.gitignore` | ✅ Done | Properly excludes .env and secrets |
| `README.md` | ✅ Done | Full setup + usage + deployment guide |
| `DESIGN.md` | ✅ Done | Architecture decisions + flow diagrams |
| `AI_USAGE.md` | ✅ Done | AI tool usage + 3 mistakes corrected |
| `data/pdfs/travel_policy.pdf` | ✅ Done | PDF dataset copied from Desktop |

---

## 🔴 What Still Needs to Be Done (TODO)

### Phase 2: Setup & Test (NEXT STEPS)

**Step 1: Get a free Groq API key**
- Go to https://console.groq.com
- Sign up for free
- Create an API key
- Copy `.env.example` to `.env` and paste the key

**Step 2: Install dependencies**
```bash
cd C:\Users\Admin\Desktop\rag
py -m pip install -r requirements.txt
```

**Step 3: Run the app**
```bash
# In one terminal:
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal:
py -m uvicorn app.mcp_server.server:app --host 0.0.0.0 --port 8001
```

**Step 4: Run tests**
```bash
# Unit tests (no API key needed):
py -m pytest tests/test_ingestion.py tests/test_security.py -v

# Integration tests (need GROQ_API_KEY in .env):
py -m pytest tests/test_rag.py -v

# Evaluation:
py evaluation/evaluate.py
```

**Step 5: Set up GitHub repo**
```bash
cd C:\Users\Admin\Desktop\rag
git init
git add .
git commit -m "Initial commit: Policy RAG Assistant"
git remote add origin <your-github-url>
git push -u origin main
```
Then add `GROQ_API_KEY` to GitHub repo Settings → Secrets → Actions.

### Phase 3: Deployment (AFTER TESTING)
- **Option A**: Hugging Face Spaces (free Docker deployment)
  - Create a Space → Docker SDK
  - Push code → Add `GROQ_API_KEY` secret
- **Option B**: Render.com free tier
  - Connect GitHub repo → Set env vars
- **Option C**: Local Docker demo (record screen)

### Phase 4: Evaluation Report
- Run `py evaluation/evaluate.py` after app is working
- Compare results before/after any improvements
- Report is saved to `evaluation/eval_report.json`
- Create a "before" baseline by running evaluation first
- Make one improvement (e.g., increase chunk size or top_k)
- Run again for "after" metrics

---

## 📂 PDF Dataset Info

**File:** `data/pdfs/travel_policy.pdf` (originally: `sidd data set.pdf` from Desktop)  
**Pages:** 3 pages  
**Content:** Company Travel / HR Policy (Policy HRMAN13)  
**Has tables:** Yes — Page 3 has 2 tables (Control Requirements + Version History)

**Key Policy Facts (for evaluating test answers):**
- Domestic flights: **economy class** (business class needs CEO approval)
- International travel: requires **CEO approval**
- Meal allowances: based on **ATO annual determination**
- Policy number: **HRMAN13**
- Approval authority: **CEO**
- Responsible officer: **CEO**
- Designated officer: **EA, CEO**
- First approved: **July 6, 2022**
- Effective start: **July 6, 2022**
- Review date: **July 6, 2024**
- Policy version: **V1 (June 2022)**

---

## 🧰 Tech Stack Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| LLM | Groq (llama-3.1-8b-instant) | Free tier, fast |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Free, local |
| Vector DB | ChromaDB | Free, local, persistent |
| PDF parsing | pdfplumber | Table extraction support |
| Agent API | FastAPI (async) | MCP-compatible tools |
| Chat UI | Built-in HTML (FastAPI) | Zero extra dependencies |
| Testing | pytest + pytest-asyncio | Async test support |
| CI/CD | GitHub Actions | Automated testing |
| Deployment | Docker + HuggingFace/Render | Free hosting |

---

## ⚠️ Known Issues / Potential Problems

1. **DLL block on pymupdf** — System Application Control blocks pymupdf DLLs. The project uses `pdfplumber` instead (works fine).
2. **Groq rate limits** — Free tier: 14,400 req/day, 30 req/min. If tests fail with rate errors, add `time.sleep(2)` between test cases.
3. **MCP server must be running** — `agent.py` calls `localhost:8001`. If MCP is down, it falls back to direct vector search (graceful degradation built in).
4. **asyncio_mode = "auto"** — Must be set in `pyproject.toml` for async tests to work. Already done.

---

## 🔑 Important Notes for Next Session

1. **Never commit `.env`** — only `.env.example` goes to GitHub
2. **The PDF was renamed** — Original: `sidd data set.pdf` → Stored as `data/pdfs/travel_policy.pdf`
3. **ChromaDB persists** — Vector index is stored in `data/vectordb/` and rebuilt automatically on startup
4. **All 3 requirements met:**
   - ✅ PDF with tables (Page 3 has 2 tables)
   - ✅ Source citation (document name + page number)
   - ✅ "I don't know" fallback (built into system prompt + evaluation)
