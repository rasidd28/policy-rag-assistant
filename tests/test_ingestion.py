"""
tests/test_ingestion.py
------------------------
Unit tests for PDF ingestion and vector store operations.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core import vector_store
from app.core.pdf_ingestion import _chunk_text, _table_to_text, ingest_pdf


class TestPDFIngestion:

    def test_ingest_single_pdf(self):
        """PDF file is successfully ingested with chunks."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        assert len(docs) > 0, "Should produce at least one document chunk"

    def test_ingest_produces_text_chunks(self):
        """Ingestion produces text-type chunks."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        text_docs = [d for d in docs if not d.is_table]
        assert len(text_docs) > 0, "Should have text chunks"

    def test_ingest_produces_table_chunks(self):
        """Ingestion detects and extracts table content."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        table_docs = [d for d in docs if d.is_table]
        assert len(table_docs) > 0, "Should extract at least one table chunk"

    def test_chunk_has_required_fields(self):
        """Every chunk has required metadata fields."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        for doc in docs:
            assert doc.content, "Chunk content must not be empty"
            assert doc.source, "Chunk must have a source"
            assert doc.page >= 1, "Chunk must have a valid page number"
            assert doc.chunk_id, "Chunk must have a unique ID"

    def test_chunk_ids_are_unique(self):
        """All chunk IDs are unique."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        ids = [d.chunk_id for d in docs]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_chunk_text_function(self):
        """Text chunking respects chunk size."""
        text = " ".join(["word"] * 200)
        chunks = _chunk_text(text, chunk_size=50, overlap=10)
        assert len(chunks) > 1, "Should split into multiple chunks"
        for chunk in chunks:
            words = chunk.split()
            assert len(words) <= 50, f"Chunk exceeds max size: {len(words)}"

    def test_table_to_text_conversion(self):
        """Table data is correctly converted to text."""
        table = [
            ["Policy Number:", "HRMAN13"],
            ["Approval Authority:", "CEO"],
        ]
        text = _table_to_text(table)
        assert "HRMAN13" in text
        assert "CEO" in text


class TestVectorStore:

    @pytest.fixture(autouse=True)
    def fresh_collection(self):
        """Reset collection before each test."""
        vector_store.reset_collection()
        yield
        vector_store.reset_collection()

    def test_embed_and_store(self):
        """Documents are stored in vector DB."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        vector_store.embed_and_store(docs)
        count = vector_store.get_collection_count()
        assert count == len(docs), f"Expected {len(docs)} chunks, got {count}"

    def test_search_returns_results(self):
        """Search returns relevant results."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        vector_store.embed_and_store(docs)
        results = vector_store.search("domestic flights economy class", top_k=3)
        assert len(results) > 0, "Should return search results"

    def test_search_result_structure(self):
        """Search results have required fields."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        vector_store.embed_and_store(docs)
        results = vector_store.search("travel policy approval", top_k=3)
        for r in results:
            assert "content" in r
            assert "source" in r
            assert "page" in r
            assert "score" in r
            assert 0.0 <= r["score"] <= 1.0

    def test_idempotent_indexing(self):
        """Re-indexing same docs doesn't create duplicates."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        vector_store.embed_and_store(docs)
        count1 = vector_store.get_collection_count()
        vector_store.embed_and_store(docs)  # second time
        count2 = vector_store.get_collection_count()
        assert count1 == count2, "Re-indexing same docs should not add duplicates"

    def test_list_sources(self):
        """List sources returns correct document names."""
        docs = ingest_pdf("data/pdfs/travel_policy.pdf")
        vector_store.embed_and_store(docs)
        sources = vector_store.list_sources()
        assert "travel_policy.pdf" in sources
