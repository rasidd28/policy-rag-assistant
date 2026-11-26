#!/bin/sh
set -e

# Start MCP server in background
python -m uvicorn app.mcp_server.server:app --host 127.0.0.1 --port 8001 &

# Wait briefly for MCP server to bind
sleep 2

# Start main FastAPI app on Render's $PORT (defaults to 8000 locally)
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
