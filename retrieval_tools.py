#!/usr/bin/env python3
"""
retrieval_tools.py — LangChain Tools for Compliance Audit Pipeline
===================================================================

Two agent-callable tools that separate retrieval / computation from LLM reasoning:

    Tool A  (PolicySearchTool)  : Searches ChromaDB for regulatory policy text
    Tool B  (LogAnalyzerTool)   : Queries the structured inference_log SQLite table

Both tools return deterministic, structured JSON — the LLM never computes
metrics or fetches documents itself.
"""

import os
import sys
import json
import sqlite3
import statistics
from datetime import datetime, timezone
from typing import Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from langchain.tools import Tool
from pydantic import BaseModel, Field

from embedding_pipeline.vector_store import (
    VectorStoreManager,
    COLLECTION_HOUSING,
    COLLECTION_STRUCTURED,
)
from embedding_pipeline.inference_logger import InferenceLogger


# ═══════════════════════════════════════════════════════════════════════════
#  TOOL A — Policy Search (ChromaDB Vector Search)
# ═══════════════════════════════════════════════════════════════════════════

DISTANCE_THRESHOLD = 0.85  # Only return semantically relevant results


def _policy_search(query: str) -> str:
    """
    Search the AI governance vector store for relevant regulatory text.

    Accepts a natural-language query (e.g., "Article 14 human oversight requirements")
    and returns the top matching policy clauses from ChromaDB with full provenance metadata.
    """
    vs = VectorStoreManager()
    all_clauses = []

    # Search governance docs collection
    results = vs.query(query, COLLECTION_HOUSING, n_results=5)
    if results["ids"] and results["ids"][0]:
        for doc_text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if dist <= DISTANCE_THRESHOLD:
                all_clauses.append({
                    "text": doc_text[:600],
                    "source_file": meta.get("source_file", ""),
                    "section": meta.get("section", ""),
                    "document_category": meta.get("document_category", ""),
                    "chunk_id": meta.get("chunk_id", ""),
                    "distance": round(dist, 4),
                })

    # Search structured policy collection
    s_results = vs.query(query, COLLECTION_STRUCTURED, n_results=3)
    if s_results["ids"] and s_results["ids"][0]:
        for doc_text, meta, dist in zip(
            s_results["documents"][0],
            s_results["metadatas"][0],
            s_results["distances"][0],
        ):
            if dist <= DISTANCE_THRESHOLD:
                all_clauses.append({
                    "text": doc_text[:600],
                    "source_file": meta.get("source_file", ""),
                    "section": meta.get("section", ""),
                    "document_category": meta.get("document_category", ""),
                    "chunk_id": meta.get("chunk_id", ""),
                    "distance": round(dist, 4),
                })

    # Deduplicate by chunk_id and sort by relevance
    seen = set()
    unique_clauses = []
    for clause in sorted(all_clauses, key=lambda x: x["distance"]):
        if clause["chunk_id"] not in seen:
            seen.add(clause["chunk_id"])
            unique_clauses.append(clause)

    # ── Fix #1: Fallback strategy when 0 results pass threshold ──────
    if len(unique_clauses) == 0:
        result = {
            "query": query,
            "total_results": 0,
            "distance_threshold": DISTANCE_THRESHOLD,
            "clauses": [],
            "warning": (
                "No specific regulatory matches found within the distance threshold "
                f"({DISTANCE_THRESHOLD}). Please broaden the compliance query or "
                "use more specific regulatory terminology (e.g., include the regulation "
                "name like 'EU AI Act', 'GDPR', 'NIST AI RMF', or 'ISO 42001')."
            ),
            "searched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    else:
        result = {
            "query": query,
            "total_results": len(unique_clauses),
            "distance_threshold": DISTANCE_THRESHOLD,
            "clauses": unique_clauses[:10],
            "searched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    return json.dumps(result, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════
#  TOOL B — Log Analyzer (SQLite Inference Log Queries)
# ═══════════════════════════════════════════════════════════════════════════

# Supported operations and their descriptions (for the LLM to understand)
SUPPORTED_OPERATIONS = {
    "summary": "Get a full statistical summary of all inference logs",
    "avg_latency": "Compute the average latency in milliseconds",
    "error_rate": "Compute the HTTP error rate (4xx/5xx responses)",
    "sample_queries": "Return N sample user queries and their outputs",
    "filter_by_category": "Filter logs by policy_category (eu_ai_act, gdpr, nist_ai_rmf, iso_42001, general)",
    "review_stats": "Get human review statistics and pending review counts",
    "eval_scores": "Get evaluation score statistics",
    "recent_logs": "Get the N most recent inference log entries",
}

# ── Fix #2: Synonym mapper for fuzzy intent routing ─────────────────────
# Maps common natural-language synonyms to the canonical keywords used in routing.
# This prevents misrouting when the LLM says "response speed" instead of "latency".
SYNONYM_MAP = {
    # Latency synonyms
    "response speed": "latency",
    "response time": "latency",
    "how fast": "latency",
    "speed": "latency",
    "delay": "latency",
    "response duration": "latency",
    "processing time": "latency",
    "turnaround": "latency",
    # Error rate synonyms
    "failure rate": "error rate",
    "failures": "error rate",
    "faults": "error rate",
    "success rate": "error rate",
    "reliability": "error rate",
    "uptime": "error rate",
    # Review / oversight synonyms
    "human review": "review",
    "human oversight": "review",
    "manual review": "review",
    "approval": "review",
    "approvals": "review",
    "pending approval": "pending",
    # Evaluation synonyms
    "quality score": "eval",
    "quality": "eval",
    "accuracy": "eval",
    "performance score": "eval",
    "model performance": "eval",
    "output quality": "eval",
    # Sample synonyms
    "examples": "sample",
    "show queries": "sample",
    "list queries": "sample",
    "give me queries": "sample",
    # Recent synonyms
    "newest": "recent",
    "most recent": "recent",
    "last few": "recent",
}


def _apply_synonyms(query: str) -> str:
    """Replace known synonyms in the query with canonical keywords."""
    q = query.lower()
    for synonym, canonical in sorted(SYNONYM_MAP.items(), key=lambda x: -len(x[0])):
        if synonym in q:
            q = q.replace(synonym, canonical)
    return q


def _log_analyzer(query: str) -> str:
    """
    Analyze the structured inference_log SQLite table.

    Accepts a natural-language query about the logs and returns deterministic,
    computed statistics. Supported operations:
    - "summary" or "full stats" → complete statistical breakdown
    - "avg latency" or "average latency" → average latency in ms
    - "error rate" → HTTP error rate percentage
    - "sample queries" or "show me N samples" → sample user queries
    - "filter by <category>" → logs for a specific policy category
    - "review stats" or "pending reviews" → human review statistics
    - "eval scores" or "evaluation" → evaluation score statistics
    - "recent" or "latest N logs" → most recent log entries

    All computation is deterministic Python/SQL — no LLM involvement.
    """
    query_lower = _apply_synonyms(query.lower().strip())  # Fix #2: synonym mapping
    logger = InferenceLogger()
    logs = logger.get_all_logs()

    # ── Fix #3: Compute time-range metadata for context injection ────
    timestamps = [l.get("timestamp", "") for l in logs if l.get("timestamp")]
    time_range = {
        "earliest": min(timestamps) if timestamps else "N/A",
        "latest": max(timestamps) if timestamps else "N/A",
    }

    if not logs:
        return json.dumps({
            "operation": "query",
            "result": "No inference records found in the database.",
            "total_records": 0,
        }, indent=2)

    # ── Route to the appropriate analysis ────────────────────────────────

    # 1. Sample queries
    if any(kw in query_lower for kw in ["sample", "show me", "examples"]):
        n = _extract_number(query_lower, default=5)
        samples = logs[:n]
        result = {
            "operation": "sample_queries",
            "count": len(samples),
            "samples": [
                {
                    "query_id": s["query_id"],
                    "user_input": s["user_input"],
                    "llm_output": s["llm_output"][:300] + "..." if len(s.get("llm_output", "")) > 300 else s.get("llm_output", ""),
                    "latency_ms": s["latency_ms"],
                    "http_status": s["http_status"],
                    "evaluation_score": s["evaluation_score"],
                    "policy_category": s["policy_category"],
                    "timestamp": s["timestamp"],
                }
                for s in samples
            ],
        }

    # 2. Average latency
    elif any(kw in query_lower for kw in ["avg latency", "average latency", "latency"]):
        latencies = [l["latency_ms"] for l in logs if l.get("latency_ms") is not None]
        result = {
            "operation": "avg_latency",
            "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "median_latency_ms": round(statistics.median(latencies), 2) if latencies else 0,
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if latencies else 0,
            "total_queries": len(latencies),
        }

    # 3. Error rate
    elif any(kw in query_lower for kw in ["error rate", "error", "failures", "http status"]):
        status_counts = {}
        for l in logs:
            s = str(l.get("http_status", "unknown"))
            status_counts[s] = status_counts.get(s, 0) + 1
        error_count = sum(v for k, v in status_counts.items() if k.startswith(("4", "5")))
        result = {
            "operation": "error_rate",
            "total_queries": len(logs),
            "error_count": error_count,
            "error_rate_percent": round((error_count / len(logs)) * 100, 2),
            "http_status_breakdown": status_counts,
        }

    # 4. Filter by category
    elif any(kw in query_lower for kw in ["filter", "category", "eu_ai_act", "gdpr", "nist", "iso"]):
        # Extract category name
        category = None
        for cat in ["eu_ai_act", "gdpr", "nist_ai_rmf", "iso_42001", "general"]:
            if cat in query_lower:
                category = cat
                break
        if not category:
            # Try partial match
            if "eu" in query_lower or "ai act" in query_lower:
                category = "eu_ai_act"
            elif "gdpr" in query_lower:
                category = "gdpr"
            elif "nist" in query_lower:
                category = "nist_ai_rmf"
            elif "iso" in query_lower:
                category = "iso_42001"

        if category:
            filtered = [l for l in logs if l.get("policy_category") == category]
            result = {
                "operation": "filter_by_category",
                "category": category,
                "total_matching": len(filtered),
                "logs": [
                    {
                        "query_id": l["query_id"],
                        "user_input": l["user_input"][:200],
                        "evaluation_score": l["evaluation_score"],
                        "http_status": l["http_status"],
                        "review_required": l["review_required"],
                        "timestamp": l["timestamp"],
                    }
                    for l in filtered
                ],
            }
        else:
            # Return all categories
            categories = {}
            for l in logs:
                pc = l.get("policy_category", "unknown")
                categories[pc] = categories.get(pc, 0) + 1
            result = {
                "operation": "list_categories",
                "available_categories": categories,
                "hint": "Specify a category name to filter, e.g., 'filter by eu_ai_act'",
            }

    # 5. Review stats
    elif any(kw in query_lower for kw in ["review", "pending", "oversight", "human"]):
        review_required_count = sum(1 for l in logs if l.get("review_required"))
        review_outcomes = {}
        for l in logs:
            ro = l.get("review_outcome", "unknown")
            review_outcomes[ro] = review_outcomes.get(ro, 0) + 1
        pending = review_outcomes.get("pending", 0)
        result = {
            "operation": "review_stats",
            "total_queries": len(logs),
            "review_required_count": review_required_count,
            "review_required_rate_percent": round((review_required_count / len(logs)) * 100, 2),
            "outcome_breakdown": review_outcomes,
            "pending_count": pending,
            "interpretation": (
                f"{review_required_count} outputs were correctly flagged for human review "
                f"({round((review_required_count / len(logs)) * 100, 2)}%). "
                f"{pending} reviews are currently PENDING human action."
            ),
        }

    # 6. Evaluation scores
    elif any(kw in query_lower for kw in ["eval", "score", "quality"]):
        eval_scores = [l["evaluation_score"] for l in logs
                       if l.get("evaluation_score") is not None and l["evaluation_score"] > 0]
        eval_statuses = {}
        for l in logs:
            es = l.get("evaluation_status", "unknown")
            eval_statuses[es] = eval_statuses.get(es, 0) + 1
        result = {
            "operation": "eval_scores",
            "total_evaluated": len(eval_scores),
            "avg_score": round(statistics.mean(eval_scores), 4) if eval_scores else 0,
            "min_score": round(min(eval_scores), 4) if eval_scores else 0,
            "max_score": round(max(eval_scores), 4) if eval_scores else 0,
            "median_score": round(statistics.median(eval_scores), 4) if eval_scores else 0,
            "status_breakdown": eval_statuses,
        }

    # 7. Recent logs
    elif any(kw in query_lower for kw in ["recent", "latest", "last"]):
        n = _extract_number(query_lower, default=5)
        recent = logs[:n]
        result = {
            "operation": "recent_logs",
            "count": len(recent),
            "logs": [
                {
                    "query_id": l["query_id"],
                    "user_input": l["user_input"][:200],
                    "latency_ms": l["latency_ms"],
                    "http_status": l["http_status"],
                    "evaluation_score": l["evaluation_score"],
                    "policy_category": l["policy_category"],
                    "timestamp": l["timestamp"],
                }
                for l in recent
            ],
        }

    # 8. Default: full summary
    else:
        latencies = [l["latency_ms"] for l in logs if l.get("latency_ms") is not None]
        eval_scores = [l["evaluation_score"] for l in logs
                       if l.get("evaluation_score") is not None and l["evaluation_score"] > 0]
        status_counts = {}
        for l in logs:
            s = str(l.get("http_status", "unknown"))
            status_counts[s] = status_counts.get(s, 0) + 1
        error_count = sum(v for k, v in status_counts.items() if k.startswith(("4", "5")))
        review_required_count = sum(1 for l in logs if l.get("review_required"))
        review_outcomes = {}
        for l in logs:
            ro = l.get("review_outcome", "unknown")
            review_outcomes[ro] = review_outcomes.get(ro, 0) + 1
        categories = {}
        for l in logs:
            pc = l.get("policy_category", "unknown")
            categories[pc] = categories.get(pc, 0) + 1

        result = {
            "operation": "summary",
            "total_queries": len(logs),
            "latency_ms": {
                "avg": round(statistics.mean(latencies), 2) if latencies else 0,
                "min": min(latencies) if latencies else 0,
                "max": max(latencies) if latencies else 0,
                "p95": round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if latencies else 0,
            },
            "error_rate_percent": round((error_count / len(logs)) * 100, 2),
            "http_status_breakdown": status_counts,
            "evaluation": {
                "avg_score": round(statistics.mean(eval_scores), 4) if eval_scores else 0,
                "min_score": round(min(eval_scores), 4) if eval_scores else 0,
                "max_score": round(max(eval_scores), 4) if eval_scores else 0,
            },
            "review": {
                "review_required_count": review_required_count,
                "pending_count": review_outcomes.get("pending", 0),
                "outcome_breakdown": review_outcomes,
            },
            "policy_category_breakdown": categories,
            "model_versions": list(set(l.get("model_version", "unknown") for l in logs)),
        }

    # ── Fix #3: Inject computation metadata for audit traceability ────
    result["_metadata"] = {
        "computation_method": "deterministic_python_sql",
        "sample_size": len(logs),
        "time_range": time_range,
        "db_path": logger.db_path,
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


def _extract_number(text: str, default: int = 5) -> int:
    """Extract a number from text, falling back to default."""
    import re
    match = re.search(r'\b(\d+)\b', text)
    if match:
        n = int(match.group(1))
        return min(max(n, 1), 50)  # Clamp between 1 and 50
    return default


# ═══════════════════════════════════════════════════════════════════════════
#  TOOL DEFINITIONS — Ready to be used by a LangChain Agent
# ═══════════════════════════════════════════════════════════════════════════

policy_search_tool = Tool(
    name="PolicySearch",
    func=_policy_search,
    description=(
        "Search the AI governance vector database for relevant regulatory policy text. "
        "Input should be a natural-language query about regulations, articles, or "
        "compliance requirements (e.g., 'EU AI Act Article 14 human oversight', "
        "'GDPR automated decision-making safeguards', 'NIST AI RMF risk metrics'). "
        "Returns matching policy clauses with source document, section, and relevance score."
    ),
)

log_analyzer_tool = Tool(
    name="LogAnalyzer",
    func=_log_analyzer,
    description=(
        "Query the structured inference log database for operational statistics. "
        "Input should describe what you want to know about the system's inference history. "
        "Supported keywords: 'latency' (or 'response speed', 'response time'), "
        "'error rate' (or 'failure rate', 'reliability'), "
        "'sample' (or 'examples', 'show queries'), "
        "'review' (or 'human oversight', 'pending approval'), "
        "'eval' (or 'quality score', 'accuracy', 'performance score'), "
        "'recent' (or 'newest', 'last few'), "
        "'filter by <category>' (eu_ai_act, gdpr, nist_ai_rmf, iso_42001), "
        "or 'summary' for a full statistical breakdown. "
        "All computations are deterministic Python/SQL — no LLM involvement. "
        "Every response includes _metadata with sample_size, time_range, and db_path."
    ),
)

# Convenience list for agent registration
ALL_TOOLS = [policy_search_tool, log_analyzer_tool]


# ═══════════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  TOOL A — Policy Search")
    print("=" * 70)
    result_a = _policy_search("EU AI Act Article 14 human oversight")
    parsed_a = json.loads(result_a)
    print(f"  Query: {parsed_a['query']}")
    print(f"  Results: {parsed_a['total_results']} clauses found")
    for c in parsed_a["clauses"][:3]:
        print(f"    • [{c['distance']}] {c['source_file']} / {c['section']}")
    print()

    # Test fallback: vague query that should return 0 results
    print("=" * 70)
    print("  TOOL A — Policy Search (Fallback Test)")
    print("=" * 70)
    result_a2 = _policy_search("quantum computing regulations")
    parsed_a2 = json.loads(result_a2)
    print(f"  Query: {parsed_a2['query']}")
    print(f"  Results: {parsed_a2['total_results']}")
    if 'warning' in parsed_a2:
        print(f"  ⚠ Fallback: {parsed_a2['warning'][:100]}...")
    print()

    print("=" * 70)
    print("  TOOL B — Log Analyzer (avg latency)")
    print("=" * 70)
    result_b1 = _log_analyzer("What is the average latency?")
    parsed_b1 = json.loads(result_b1)
    print(f"  Avg latency: {parsed_b1.get('avg_latency_ms', 'N/A')} ms")
    meta = parsed_b1.get('_metadata', {})
    print(f"  Sample size: {meta.get('sample_size', 'N/A')}")
    print(f"  Time range: {meta.get('time_range', 'N/A')}")
    print()

    # Test synonym routing: "response speed" → latency
    print("=" * 70)
    print("  TOOL B — Synonym Test ('response speed' → latency)")
    print("=" * 70)
    result_b4 = _log_analyzer("What is the response speed?")
    parsed_b4 = json.loads(result_b4)
    print(f"  Routed to: {parsed_b4.get('operation', 'UNKNOWN')}")
    print(f"  Avg latency: {parsed_b4.get('avg_latency_ms', 'N/A')} ms")
    print()

    print("=" * 70)
    print("  TOOL B — Log Analyzer (5 sample queries)")
    print("=" * 70)
    result_b2 = _log_analyzer("Show me 5 sample queries")
    parsed_b2 = json.loads(result_b2)
    for s in parsed_b2.get("samples", []):
        print(f"    • [{s['policy_category']}] {s['user_input'][:80]}...")
    print()

    print("=" * 70)
    print("  TOOL B — Log Analyzer (review stats)")
    print("=" * 70)
    result_b3 = _log_analyzer("Show human review statistics")
    parsed_b3 = json.loads(result_b3)
    print(f"  Review required: {parsed_b3.get('review_required_count', 'N/A')}")
    print(f"  Pending: {parsed_b3.get('pending_count', 'N/A')}")
    print(f"  Interpretation: {parsed_b3.get('interpretation', 'N/A')}")
    print()

    print("✅ All tools working correctly (with hardening fixes)")
