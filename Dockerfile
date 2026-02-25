FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Pre-download the embedding model at build time (cached in Docker layer)
# This avoids a ~1.7 GB download on every container restart.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3', trust_remote_code=True)"

# HuggingFace Spaces expects port 7860
EXPOSE 7860

# Start: seed data (if needed) then launch the server
CMD ["bash", "start.sh"]
