"""
app/main.py
-----------
Main FastAPI application — the user-facing chat API.
Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.agent.agent import clear_session, get_session_history, process_query
from app.core import vector_store
from app.core.config import settings
from app.core.logger import get_logger
from app.core.pdf_ingestion import ingest_all_pdfs

logger = get_logger(__name__)


# ─── Startup: Ingest PDFs and build index ─────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ingest PDFs on startup."""
    logger.info("starting_up", service="policy-rag-assistant")
    try:
        docs = ingest_all_pdfs()
        if docs:
            vector_store.embed_and_store(docs)
            logger.info("startup_indexing_complete", chunks=len(docs))
        else:
            logger.warning("no_documents_found_at_startup")
    except Exception as e:
        logger.error("startup_indexing_failed", error=str(e))
    yield
    logger.info("shutting_down")


# ─── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Policy Document Assistant",
    description="RAG-powered AI assistant for company policy documents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ─── Request / Response Models ─────────────────────────────────────────────────


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User question")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Session ID for conversation continuity",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[dict]
    metrics: dict
    flagged: bool = False


class HistoryResponse(BaseModel):
    session_id: str
    history: list[dict]


# ─── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve a simple chat UI."""
    return HTMLResponse(content=CHAT_HTML)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "policy-rag-assistant",
        "chunks_indexed": vector_store.get_collection_count(),
        "sources": vector_store.list_sources(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Send a question, get back an answer with source citations.
    """
    try:
        result = await process_query(
            user_query=request.query,
            session_id=request.session_id,
            top_k=request.top_k,
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.error("chat_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """Get conversation history for a session."""
    history = get_session_history(session_id)
    return HistoryResponse(session_id=session_id, history=history)


@app.delete("/history/{session_id}")
async def delete_history(session_id: str):
    """Clear conversation history for a session."""
    clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.post("/admin/reindex")
async def reindex(background_tasks: BackgroundTasks):
    """Re-ingest all PDFs and rebuild the index."""

    def _reindex():
        docs = ingest_all_pdfs()
        if docs:
            vector_store.embed_and_store(docs)
            logger.info("reindex_complete", chunks=len(docs))

    background_tasks.add_task(_reindex)
    return {"status": "reindexing_started"}


# ─── Minimal Chat UI HTML ──────────────────────────────────────────────────────

CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Policy Document Assistant</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; height: 100vh; display: flex; flex-direction: column; }
  header { background: #1a73e8; color: white; padding: 16px 24px; font-size: 1.2rem; font-weight: 600; }
  #chat-window { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 12px; }
  .msg { max-width: 75%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; }
  .user-msg { align-self: flex-end; background: #1a73e8; color: white; border-bottom-right-radius: 2px; }
  .bot-msg { align-self: flex-start; background: white; color: #333; border-bottom-left-radius: 2px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .sources { font-size: 0.75rem; color: #666; margin-top: 8px; }
  #input-area { padding: 16px 24px; background: white; border-top: 1px solid #e0e0e0; display: flex; gap: 12px; }
  #query-input { flex: 1; padding: 12px 16px; border: 1px solid #ddd; border-radius: 24px; outline: none; font-size: 0.95rem; }
  #send-btn { padding: 12px 24px; background: #1a73e8; color: white; border: none; border-radius: 24px; cursor: pointer; font-size: 0.95rem; }
  #send-btn:hover { background: #1557b0; }
  .typing { color: #999; font-style: italic; }
  #session-id { font-size: 0.75rem; color: #aaa; padding: 4px 24px; }
</style>
</head>
<body>
<header>🏢 Policy Document Assistant</header>
<div id="chat-window">
  <div class="msg bot-msg">Hello! I'm your Policy Document Assistant. Ask me anything about company policies — travel, leave, reimbursement, and more.</div>
</div>
<div id="session-id">Session: <span id="sid"></span></div>
<div id="input-area">
  <input id="query-input" type="text" placeholder="Ask about company policies..." autocomplete="off" />
  <button id="send-btn">Send</button>
</div>
<script>
const sessionId = crypto.randomUUID();
document.getElementById('sid').textContent = sessionId;
const chatWindow = document.getElementById('chat-window');
const input = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');

function addMsg(text, role, sources=[]) {
  const div = document.createElement('div');
  div.className = 'msg ' + (role === 'user' ? 'user-msg' : 'bot-msg');
  div.textContent = text;
  if (sources.length > 0 && role === 'bot') {
    const src = document.createElement('div');
    src.className = 'sources';
    const unique = [...new Set(sources.map(s => s.source + ' p.' + s.page))];
    src.textContent = '📄 Sources: ' + unique.join(', ');
    div.appendChild(src);
  }
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

async function sendQuery() {
  const query = input.value.trim();
  if (!query) return;
  input.value = '';
  addMsg(query, 'user');
  const typing = addMsg('Thinking...', 'bot');
  typing.classList.add('typing');
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query, session_id: sessionId})
    });
    const data = await res.json();
    typing.remove();
    addMsg(data.answer, 'bot', data.sources || []);
  } catch(e) {
    typing.textContent = 'Error: Could not reach the server.';
    typing.classList.remove('typing');
  }
}

sendBtn.onclick = sendQuery;
input.addEventListener('keydown', e => { if (e.key === 'Enter') sendQuery(); });
</script>
</body>
</html>"""


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
