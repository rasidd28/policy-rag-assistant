# Dockerfile — Policy RAG Assistant
# ────────────────────────────────────────────────────────────────────────────────
# Multi-stage build for a small, production-ready image.
# Usage:
#   docker build -t policy-rag-assistant .
#   docker run -p 8000:8000 --env-file .env policy-rag-assistant
# ────────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app/ ./app/
COPY data/ ./data/
COPY evaluation/ ./evaluation/
COPY start.sh .

# Create required dirs and make start.sh executable
RUN mkdir -p logs data/vectordb && chmod +x start.sh

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import os, httpx; httpx.get(f'http://localhost:{os.getenv(\"PORT\", \"8000\")}/health')" || exit 1

EXPOSE 8000

# Start both MCP server and main app
CMD ["./start.sh"]
