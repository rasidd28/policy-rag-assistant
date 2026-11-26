"""
app/core/vector_store.py
------------------------
Manages the ChromaDB vector store:
 - Embeds documents using sentence-transformers (free, local)
 - Stores and retrieves chunks
 - Returns results with source citations
"""

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.core.config import settings
from app.core.logger import get_logger
from app.core.pdf_ingestion import Document

logger = get_logger(__name__)

# Singleton instances
_client: Optional[chromadb.PersistentClient] = None
_collection = None
_embedder = None


class _OnnxEmbedderAdapter:
    """Adapter around Chroma's ONNX DefaultEmbeddingFunction (all-MiniLM-L6-v2)."""

    def __init__(self):
        self._ef = embedding_functions.DefaultEmbeddingFunction()

    def encode(self, texts: list[str], show_progress_bar: bool = False):
        return _VectorList(self._ef(texts))


class _VectorList(list):
    """Provides .tolist() compatibility with SentenceTransformer output."""

    def tolist(self):
        return [list(map(float, v)) for v in self]


def _get_embedder():
    global _embedder
    if _embedder is None:
        logger.info("loading_embedder", model=settings.embedding_model)
        try:
            from sentence_transformers import SentenceTransformer

            _embedder = SentenceTransformer(settings.embedding_model)
        except (OSError, ImportError) as exc:
            logger.warning(
                "sentence_transformers_unavailable_using_onnx_fallback",
                error=str(exc),
            )
            _embedder = _OnnxEmbedderAdapter()
    return _embedder


def _get_client():
    global _client
    if _client is None:
        Path(settings.vectordb_path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.vectordb_path, settings=ChromaSettings(anonymized_telemetry=False)
        )
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=settings.collection_name, metadata={"hnsw:space": "cosine"}
        )
    return _collection


def embed_and_store(documents: list[Document]) -> None:
    """Embed documents and store in ChromaDB."""
    if not documents:
        logger.warning("no_documents_to_store")
        return

    collection = _get_collection()
    embedder = _get_embedder()

    # Check which chunk IDs already exist
    existing_ids = set(collection.get(include=[])["ids"])

    new_docs = [d for d in documents if d.chunk_id not in existing_ids]
    if not new_docs:
        logger.info("all_chunks_already_indexed", skipped=len(documents))
        return

    texts = [d.content for d in new_docs]
    ids = [d.chunk_id for d in new_docs]
    metadatas = [d.metadata for d in new_docs]

    logger.info("embedding_documents", count=len(new_docs))
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()

    collection.add(
        documents=texts,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )
    logger.info("stored_in_vectordb", count=len(new_docs))


def search(query: str, top_k: int = None) -> list[dict]:
    """
    Search for relevant document chunks.
    Returns list of dicts with keys: content, source, page, score, is_table
    """
    top_k = top_k or settings.top_k_results
    collection = _get_collection()
    embedder = _get_embedder()

    query_embedding = embedder.encode([query], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    formatted = []
    if results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Convert cosine distance to similarity score
            score = max(0.0, 1.0 - dist)
            formatted.append(
                {
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "page": meta.get("page", 0),
                    "is_table": meta.get("type") == "table",
                    "score": round(score, 4),
                }
            )

    return formatted


def get_collection_count() -> int:
    """Return number of chunks in the vector store."""
    return _get_collection().count()


def reset_collection() -> None:
    """Delete and recreate the collection (use in tests only)."""
    global _collection
    client = _get_client()
    try:
        client.delete_collection(settings.collection_name)
    except Exception:
        pass
    _collection = None
    _get_collection()
    logger.info("collection_reset")


def list_sources() -> list[str]:
    """Return list of unique source documents in the vector store."""
    collection = _get_collection()
    result = collection.get(include=["metadatas"])
    sources = list({m.get("source", "unknown") for m in result["metadatas"]})
    return sources
