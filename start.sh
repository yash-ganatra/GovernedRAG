#!/bin/bash
# start.sh — GovernedRAG startup script for HuggingFace Spaces
# Copies pre-built data to writable /tmp, then starts FastAPI.

set -e

echo "=== GovernedRAG Startup ==="

# HF Spaces mounts repo files as read-only.
# Copy writable data (SQLite DBs, ChromaDB, JSON) to /tmp.
echo "▶ Copying data to writable storage..."

if [ -d "/app/vector_store" ]; then
    cp -r /app/vector_store /tmp/vector_store
    echo "  ✅ Copied vector_store → /tmp/vector_store"
fi

if [ -d "/app/audit" ]; then
    cp -r /app/audit /tmp/audit
    echo "  ✅ Copied audit → /tmp/audit"
else
    mkdir -p /tmp/audit
    echo "  ✅ Created /tmp/audit"
fi

# Set environment variables so Python modules use /tmp paths
export VECTOR_STORE_DIR="/tmp/vector_store"
export AUDIT_DIR="/tmp/audit"

# If vector store wasn't pre-built, run ingestion
if [ ! -f "/tmp/vector_store/chroma.sqlite3" ]; then
    echo "▶ First boot — running ingestion pipeline..."
    python -m scripts.run_pipeline
    echo "✅ Ingestion complete."
else
    echo "✅ Vector store already populated, skipping ingestion."
fi

# Start the FastAPI server on the HF Spaces port (7860)
echo "▶ Starting FastAPI server on port ${PORT:-7860}..."
exec uvicorn api.server:app --host 0.0.0.0 --port "${PORT:-7860}"
