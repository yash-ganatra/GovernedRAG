#!/bin/bash
# start.sh — GovernedRAG startup script for HuggingFace Spaces
# Runs the ingestion pipeline on first boot (if vector_store is empty),
# then starts the FastAPI server.

set -e

echo "=== GovernedRAG Startup ==="

# Check if vector store has been populated
if [ ! -f "/app/vector_store/chroma.sqlite3" ]; then
    echo "▶ First boot detected — running ingestion pipeline..."
    python -m scripts.run_pipeline
    echo "✅ Ingestion complete."
else
    echo "✅ Vector store already populated, skipping ingestion."
fi

# Start the FastAPI server on the HF Spaces port (7860)
echo "▶ Starting FastAPI server on port ${PORT:-7860}..."
exec uvicorn api.server:app --host 0.0.0.0 --port "${PORT:-7860}"
