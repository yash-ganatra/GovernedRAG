#!/usr/bin/env python3
"""
run_pipeline.py — GovernedRAG Embedding Pipeline
=================================================

Production-grade pipeline that:
    1. Loads curated housing documents + structured YAML policy
    2. Chunks with section-aware overlapping strategy
    3. Embeds into ChromaDB (two collections)
    4. Attaches full governance metadata
    5. Validates traceability integrity
    6. Logs all events to SQLite audit table
    7. Runs a test retrieval query
"""

import os
import sys
import json

# Resolve project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from embedding_pipeline.document_loader import load_markdown_documents, load_yaml_policy
from embedding_pipeline.chunker import chunk_document, chunk_yaml_document
from embedding_pipeline.vector_store import (
    VectorStoreManager,
    COLLECTION_HOUSING,
    COLLECTION_STRUCTURED,
)
from embedding_pipeline.traceability import (
    validate_traceability,
    print_validation_report,
)
from embedding_pipeline.audit_logger import AuditLogger


# ── Paths ────────────────────────────────────────────────────────────────
HOUSING_DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "housing_docs")
YAML_POLICY_PATH = os.path.join(
    PROJECT_ROOT, "data", "structured_policy", "housing_policy_structured.yaml"
)


def main() -> None:
    print("\n" + "=" * 64)
    print("  GovernedRAG — Embedding Pipeline")
    print("=" * 64)

    # ── STEP 1: Initialise components ────────────────────────────────────
    print("\n▶ Step 1 — Initialising vector store & audit logger ...")
    vs = VectorStoreManager()
    audit = AuditLogger()

    # ── STEP 2: Load markdown documents ──────────────────────────────────
    print("\n▶ Step 2 — Loading markdown housing documents ...")
    md_docs = load_markdown_documents(HOUSING_DOCS_DIR)
    print(f"  Loaded {len(md_docs)} markdown documents:")
    for d in md_docs:
        print(f"    • {d['file_name']}  ({d['document_category']})  sections={len(d['sections'])}")

    # ── STEP 3: Load YAML policy ─────────────────────────────────────────
    print("\n▶ Step 3 — Loading structured YAML policy ...")
    yaml_doc = load_yaml_policy(YAML_POLICY_PATH)
    print(f"  Loaded: {yaml_doc['file_name']}  (category={yaml_doc['document_category']})")

    # ── STEP 4: Chunk all documents ──────────────────────────────────────
    print("\n▶ Step 4 — Chunking documents ...")
    all_housing_chunks: list[dict] = []
    for doc in md_docs:
        chunks = chunk_document(doc)
        all_housing_chunks.extend(chunks)
        print(f"    {doc['file_name']}: {len(chunks)} chunks")

    yaml_chunks = chunk_yaml_document(yaml_doc)
    print(f"    {yaml_doc['file_name']}: {len(yaml_chunks)} chunks")

    print(f"\n  Total housing chunks    : {len(all_housing_chunks)}")
    print(f"  Total structured chunks : {len(yaml_chunks)}")

    # ── STEP 5: Embed into ChromaDB ──────────────────────────────────────
    print("\n▶ Step 5 — Embedding into ChromaDB ...")
    n_housing = vs.upsert_chunks(all_housing_chunks, COLLECTION_HOUSING)
    n_structured = vs.upsert_chunks(yaml_chunks, COLLECTION_STRUCTURED)

    stats = vs.collection_stats()
    print(f"\n  Collection stats after embedding:")
    for name, count in stats.items():
        print(f"    {name}: {count} chunks")

    # ── STEP 6: Audit logging ────────────────────────────────────────────
    print("\n▶ Step 6 — Logging embedding events to SQLite audit table ...")
    for doc in md_docs:
        doc_chunks = [c for c in all_housing_chunks if c["source_file"] == doc["file_name"]]
        audit.log_embedding(
            document_name=doc["file_name"],
            number_of_chunks=len(doc_chunks),
            policy_version=doc["document_version"],
            embedding_model_used=vs.embedding_model_name,
            collection_name=COLLECTION_HOUSING,
        )

    audit.log_embedding(
        document_name=yaml_doc["file_name"],
        number_of_chunks=len(yaml_chunks),
        policy_version=yaml_doc.get("policy_version", "v1"),
        embedding_model_used=vs.embedding_model_name,
        collection_name=COLLECTION_STRUCTURED,
    )

    audit.print_audit_log()

    # ── STEP 7: Validate traceability ────────────────────────────────────
    print("▶ Step 7 — Validating traceability integrity ...")

    # Gather metadata from ChromaDB
    housing_meta = vs.housing_collection.get(include=["metadatas"])["metadatas"]
    structured_meta = vs.structured_collection.get(include=["metadatas"])["metadatas"]

    report = validate_traceability(housing_meta, structured_meta)
    print_validation_report(report)

    # ── STEP 8: Test retrieval ───────────────────────────────────────────
    print("▶ Step 8 — Test retrieval query ...")
    test_query = "Am I eligible for housing benefit if I have £18,000 in savings?"
    print(f"\n  Query: \"{test_query}\"\n")

    results = vs.query(test_query, COLLECTION_HOUSING, n_results=5)

    print(f"  Retrieved {len(results['ids'][0])} chunks:\n")
    for i, (doc_id, doc_text, meta, dist) in enumerate(
        zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ):
        print(f"  ── Result {i+1} ──────────────────────────────────────")
        print(f"  chunk_id        : {meta['chunk_id']}")
        print(f"  source_file     : {meta['source_file']}")
        print(f"  section         : {meta['section']}")
        print(f"  document_cat    : {meta['document_category']}")
        print(f"  policy_version  : {meta['policy_version']}")
        print(f"  date_embedded   : {meta['date_embedded']}")
        print(f"  retrieval_count : {meta['retrieval_count']}")
        print(f"  distance        : {dist:.4f}")
        print(f"  url             : {meta.get('url', 'N/A')}")
        print(f"  text_preview    : {doc_text[:200]}...")
        print()

    # Also query structured collection
    print("  ── Structured Policy Results ─────────────────────")
    s_results = vs.query(test_query, COLLECTION_STRUCTURED, n_results=3)
    for i, (doc_id, doc_text, meta, dist) in enumerate(
        zip(
            s_results["ids"][0],
            s_results["documents"][0],
            s_results["metadatas"][0],
            s_results["distances"][0],
        )
    ):
        print(f"  chunk_id        : {meta['chunk_id']}")
        print(f"  section         : {meta['section']}")
        print(f"  distance        : {dist:.4f}")
        print(f"  text_preview    : {doc_text[:150]}...")
        print()

    # ── Retrieval counter verification ───────────────────────────────────
    print("▶ Retrieval counter verification ...")
    counts = vs.get_all_retrieval_counts()
    nonzero = {k: v for k, v in counts.items() if v > 0}
    print(f"  Chunks with retrieval_count > 0: {len(nonzero)}")
    for k, v in sorted(nonzero.items(), key=lambda x: -x[1])[:10]:
        print(f"    {k}: {v}")

    # ── Final summary ────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("  ✅  PIPELINE COMPLETE")
    print("=" * 64)
    print(f"  Documents embedded     : {len(md_docs) + 1}")
    print(f"  Housing chunks         : {n_housing}")
    print(f"  Structured chunks      : {n_structured}")
    print(f"  Traceability validated : {'PASS' if report['passed'] else 'FAIL'}")
    print(f"  Audit log entries      : {len(audit.get_all_logs())}")
    print(f"  Vector store path      : {vs.persist_dir}")
    print(f"  Audit DB path          : {audit.db_path}")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    main()
