"""
app/core/pdf_ingestion.py
--------------------------
Reads PDF files, extracts text AND tables, chunks them,
and returns structured Document objects ready for embedding.
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Document:
    """A single chunk of text from a PDF, with metadata."""

    content: str
    source: str  # filename
    page: int  # 1-indexed page number
    chunk_id: str  # unique hash
    chunk_index: int  # position within the doc
    is_table: bool = False
    metadata: dict = field(default_factory=dict)


def _make_chunk_id(source: str, page: int, index: int, content: str) -> str:
    raw = f"{source}:p{page}:c{index}:{content[:50]}"
    return hashlib.md5(raw.encode()).hexdigest()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks by word boundaries."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        if end == len(words):
            break
        start = end - overlap
    return chunks


def _table_to_text(table: list[list]) -> str:
    """Convert a pdfplumber table (list of rows) to readable text."""
    if not table:
        return ""
    lines = []
    headers = [str(c) if c else "" for c in table[0]]
    lines.append(" | ".join(headers))
    lines.append("-" * (sum(len(h) + 3 for h in headers)))
    for row in table[1:]:
        cells = [str(c) if c else "" for c in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def ingest_pdf(pdf_path: str | Path) -> list[Document]:
    """
    Ingests a PDF file and returns a list of Document chunks.
    Handles both regular text pages and tables.
    """
    pdf_path = Path(pdf_path)
    source_name = pdf_path.name
    documents: list[Document] = []
    chunk_index = 0

    logger.info("ingesting_pdf", source=source_name)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            tables = page.extract_tables() or []

            # Remove table text from page text to avoid duplication
            table_texts = set()
            for table in tables:
                for row in table:
                    for cell in row:
                        if cell:
                            table_texts.add(str(cell).strip())

            # Clean page text
            clean_text = page_text
            for t in table_texts:
                clean_text = clean_text.replace(t, "")
            clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

            # Chunk regular text
            if clean_text:
                chunks = _chunk_text(clean_text, settings.chunk_size, settings.chunk_overlap)
                for chunk in chunks:
                    doc = Document(
                        content=chunk,
                        source=source_name,
                        page=page_num,
                        chunk_id=_make_chunk_id(source_name, page_num, chunk_index, chunk),
                        chunk_index=chunk_index,
                        is_table=False,
                        metadata={"type": "text", "page": page_num, "source": source_name},
                    )
                    documents.append(doc)
                    chunk_index += 1

            # Chunk tables — each table becomes one document
            for table_idx, table in enumerate(tables):
                table_text = _table_to_text(table)
                if table_text.strip():
                    # Prefix to help retrieval
                    prefixed = f"[TABLE from {source_name}, Page {page_num}]\n{table_text}"
                    doc = Document(
                        content=prefixed,
                        source=source_name,
                        page=page_num,
                        chunk_id=_make_chunk_id(source_name, page_num, chunk_index, table_text),
                        chunk_index=chunk_index,
                        is_table=True,
                        metadata={
                            "type": "table",
                            "page": page_num,
                            "source": source_name,
                            "table_index": table_idx,
                        },
                    )
                    documents.append(doc)
                    chunk_index += 1

    logger.info(
        "ingestion_complete",
        source=source_name,
        total_chunks=len(documents),
        table_chunks=sum(1 for d in documents if d.is_table),
    )
    return documents


def ingest_all_pdfs(pdfs_dir: str | Path = None) -> list[Document]:
    """Ingest all PDFs in the given directory."""
    pdfs_dir = Path(pdfs_dir or settings.pdfs_dir)
    all_docs: list[Document] = []
    pdf_files = list(pdfs_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning("no_pdfs_found", directory=str(pdfs_dir))
        return []

    for pdf_file in pdf_files:
        docs = ingest_pdf(pdf_file)
        all_docs.extend(docs)

    logger.info("all_pdfs_ingested", total_chunks=len(all_docs), files=len(pdf_files))
    return all_docs
