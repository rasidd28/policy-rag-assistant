"""
app/mcp_server/server.py
------------------------
MCP (Model Context Protocol) server.
Exposes policy search tools via a REST API that the AI agent calls.
"""

import time

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core import vector_store
from app.core.config import settings
from app.core.logger import get_logger
from app.core.security import sanitize_document_content

logger = get_logger(__name__)

app = FastAPI(
    title="Policy RAG MCP Server",
    description="MCP-compatible tool server for policy document retrieval",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response Models ───────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")


class SearchResult(BaseModel):
    content: str
    source: str
    page: int
    is_table: bool
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total_results: int


class DocumentPageRequest(BaseModel):
    source: str = Field(..., description="PDF filename")
    page: int = Field(..., ge=1, description="Page number (1-indexed)")


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict


# ─── MCP Tool Definitions (for LLM to understand) ─────────────────────────────

TOOLS = [
    {
        "name": "search_policy",
        "description": (
            "Search the company policy documents for relevant information. "
            "Use this tool to find answers to questions about travel, leave, "
            "reimbursement, HR rules, or any other policy topic. "
            "Returns ranked chunks with source citations (document name and page number)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query based on the user's question",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of relevant chunks to retrieve (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": "List all policy documents currently available in the system.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_document_info",
        "description": "Get metadata about the vector store (document count, sources).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]


# ─── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "service": "policy-mcp-server", "timestamp": time.time()}


@app.get("/tools", response_model=list[ToolDefinition])
async def list_tools():
    """Return available MCP tools."""
    return TOOLS


@app.post("/tools/search_policy", response_model=SearchResponse)
async def search_policy(request: SearchRequest):
    """
    Search policy documents for relevant information.
    Returns ranked results with source citations.
    """
    try:
        raw_results = vector_store.search(request.query, top_k=request.top_k)
    except Exception as e:
        logger.error("search_failed", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    # Sanitize document content (treat as untrusted)
    results = [
        SearchResult(
            content=sanitize_document_content(r["content"]),
            source=r["source"],
            page=r["page"],
            is_table=r["is_table"],
            score=r["score"],
        )
        for r in raw_results
    ]

    logger.info(
        "search_policy_called",
        query=request.query,
        results_found=len(results),
    )

    return SearchResponse(
        results=results,
        query=request.query,
        total_results=len(results),
    )


@app.get("/tools/list_documents")
async def list_documents():
    """List all indexed policy documents."""
    try:
        sources = vector_store.list_sources()
        count = vector_store.get_collection_count()
        return {
            "documents": sources,
            "total_documents": len(sources),
            "total_chunks": count,
        }
    except Exception as e:
        logger.error("list_documents_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/get_document_info")
async def get_document_info():
    """Get info about the vector store."""
    try:
        count = vector_store.get_collection_count()
        sources = vector_store.list_sources()
        return {
            "collection": settings.collection_name,
            "total_chunks": count,
            "sources": sources,
            "embedding_model": settings.embedding_model,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "app.mcp_server.server:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=False,
    )
