"""
Vector Store Manager — ChromaDB collections with SentenceTransformer embeddings.

Two collections:
    • housing_policy_docs      — markdown housing documents
    • structured_policy_docs   — YAML structured policy extractions

Supports:
    • Upsert with full metadata
    • Metadata-aware retrieval
    • Retrieval count persistence
"""

import os
import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import Any

# ── Configuration ────────────────────────────────────────────────────────
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vector_store",
)
COLLECTION_HOUSING = "housing_policy_docs"
COLLECTION_STRUCTURED = "structured_policy_docs"

# ── Retrieval counter persistence file ───────────────────────────────────
RETRIEVAL_COUNTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vector_store",
    "retrieval_counts.json",
)


class VectorStoreManager:
    """Manages ChromaDB collections for the GovernedRAG pipeline."""

    def __init__(self, persist_dir: str | None = None):
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        os.makedirs(self.persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        # Load embedding model once
        print(f"[VectorStore] Loading embedding model: {EMBEDDING_MODEL_NAME}")
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.embedding_model_name = EMBEDDING_MODEL_NAME

        # Get or create both collections
        self.housing_collection = self.client.get_or_create_collection(
            name=COLLECTION_HOUSING,
            metadata={"description": "Housing policy markdown documents"},
        )
        self.structured_collection = self.client.get_or_create_collection(
            name=COLLECTION_STRUCTURED,
            metadata={"description": "Structured YAML policy extractions"},
        )

        # Load persisted retrieval counts
        self._retrieval_counts = self._load_retrieval_counts()

    # ── Embedding ────────────────────────────────────────────────────────

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Produce embeddings for a list of texts."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    # ── Upsert ───────────────────────────────────────────────────────────

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        collection_name: str = COLLECTION_HOUSING,
    ) -> int:
        """
        Upsert a list of chunk dicts into the specified collection.
        Returns the number of chunks upserted.
        """
        collection = (
            self.housing_collection
            if collection_name == COLLECTION_HOUSING
            else self.structured_collection
        )

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        embeddings: list[list[float]] = []

        texts = [c["text"] for c in chunks]
        embs = self.embed_texts(texts)

        for chunk, emb in zip(chunks, embs):
            ids.append(chunk["chunk_id"])
            documents.append(chunk["text"])
            metadatas.append({
                "source_file": chunk["source_file"],
                "source_type": chunk["source_type"],
                "document_category": chunk["document_category"],
                "policy_version": chunk["policy_version"],
                "section": chunk["section"],
                "chunk_id": chunk["chunk_id"],
                "date_embedded": chunk["date_embedded"],
                "retrieval_count": chunk.get("retrieval_count", 0),
                "url": chunk.get("url", ""),
            })
            embeddings.append(emb)

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        print(
            f"[VectorStore] Upserted {len(ids)} chunks into '{collection_name}'"
        )
        return len(ids)

    # ── Query / Retrieval ────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        collection_name: str = COLLECTION_HOUSING,
        n_results: int = 5,
        where_filter: dict | None = None,
    ) -> dict[str, Any]:
        """
        Query a collection. Returns dict with keys:
            ids, documents, metadatas, distances
        Increments retrieval_count for each returned chunk.
        """
        collection = (
            self.housing_collection
            if collection_name == COLLECTION_HOUSING
            else self.structured_collection
        )

        query_embedding = self.embed_texts([query_text])[0]

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = collection.query(**kwargs)

        # Increment retrieval counts
        if results["ids"] and results["ids"][0]:
            for chunk_id in results["ids"][0]:
                self._increment_retrieval_count(chunk_id, collection_name, collection)

        return results

    def query_all_collections(
        self,
        query_text: str,
        n_results: int = 5,
    ) -> dict[str, dict[str, Any]]:
        """Query both collections and return combined results."""
        return {
            COLLECTION_HOUSING: self.query(
                query_text, COLLECTION_HOUSING, n_results
            ),
            COLLECTION_STRUCTURED: self.query(
                query_text, COLLECTION_STRUCTURED, n_results
            ),
        }

    # ── Retrieval Counter ────────────────────────────────────────────────

    def _increment_retrieval_count(
        self,
        chunk_id: str,
        collection_name: str,
        collection: Any,
    ) -> None:
        """Increment retrieval_count for a chunk in both Chroma and persistence."""
        key = f"{collection_name}::{chunk_id}"
        self._retrieval_counts[key] = self._retrieval_counts.get(key, 0) + 1

        # Update Chroma metadata
        try:
            existing = collection.get(ids=[chunk_id], include=["metadatas"])
            if existing["metadatas"]:
                meta = existing["metadatas"][0]
                meta["retrieval_count"] = self._retrieval_counts[key]
                collection.update(ids=[chunk_id], metadatas=[meta])
        except Exception:
            pass  # Non-critical — persisted counts remain authoritative

        self._save_retrieval_counts()

    def get_retrieval_count(self, chunk_id: str, collection_name: str = COLLECTION_HOUSING) -> int:
        key = f"{collection_name}::{chunk_id}"
        return self._retrieval_counts.get(key, 0)

    def get_all_retrieval_counts(self) -> dict[str, int]:
        return dict(self._retrieval_counts)

    def _load_retrieval_counts(self) -> dict[str, int]:
        path = os.path.join(self.persist_dir, "retrieval_counts.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def _save_retrieval_counts(self) -> None:
        path = os.path.join(self.persist_dir, "retrieval_counts.json")
        with open(path, "w") as f:
            json.dump(self._retrieval_counts, f, indent=2)

    # ── Introspection ────────────────────────────────────────────────────

    def collection_stats(self) -> dict[str, int]:
        return {
            COLLECTION_HOUSING: self.housing_collection.count(),
            COLLECTION_STRUCTURED: self.structured_collection.count(),
        }
