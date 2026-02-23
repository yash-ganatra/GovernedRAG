#!/usr/bin/env python3
"""
compliance_pipeline.py — 5-Step Deterministic Compliance Audit Reasoning Pipeline
==================================================================================

Uses LangChain SequentialChain to enforce strict step ordering:

    Step 1  (LLM)    : Decompose regulatory query → extract compliance elements
    Step 2  (Python)  : Retrieve relevant policy clauses from ChromaDB
    Step 3  (Python)  : Compute evidence metrics from inference_log SQL table
    Step 4  (LLM)    : Gap Analysis — compare clauses vs metrics
    Step 5  (LLM)    : Adjudicate — final compliance status + structured JSON

Key invariants:
    - Steps 2 & 3 are pure Python — the LLM NEVER computes metrics
    - The SequentialChain prevents step-skipping
    - The final output is a structured JSON compliance report
"""

# ── Fix macOS OpenBLAS / SciPy deadlock ──────────────────────────────────
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import sys
import json
import sqlite3
import statistics
from datetime import datetime, timezone
from typing import Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from langchain.chains import SequentialChain, LLMChain, TransformChain
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from embedding_pipeline.vector_store import VectorStoreManager, COLLECTION_HOUSING, COLLECTION_STRUCTURED
from embedding_pipeline.inference_logger import InferenceLogger

# Load environment variables from .env file
load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1 — Decompose Query (LLM)
# ═══════════════════════════════════════════════════════════════════════════

STEP1_PROMPT = PromptTemplate(
    input_variables=["user_query"],
    template="""You are a regulatory compliance analyst. Your task is to decompose a regulatory query into its constituent compliance elements.

Given the following regulatory query, extract and return a JSON object with these fields:
- "regulations": list of regulations mentioned or implied (e.g., "EU AI Act", "GDPR", "NIST AI RMF", "ISO/IEC 42001")
- "articles": list of specific articles, clauses, or sections referenced (e.g., "Article 14", "GV-1.2")
- "obligations": list of specific obligations or requirements being asked about (e.g., "human oversight", "record-keeping", "transparency")
- "system_context": the type of AI system or context mentioned (e.g., "biometric identification", "credit scoring", "chatbot")
- "query_intent": one of "compliance_check", "gap_analysis", "requirement_explanation", "risk_assessment"

IMPORTANT: Return ONLY the JSON object, no other text.

Regulatory query: {user_query}

JSON output:""",
)


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2 — Retrieve Policy Clauses (PURE PYTHON — no LLM)
# ═══════════════════════════════════════════════════════════════════════════

def _step2_retrieve_clauses(inputs: dict[str, Any]) -> dict[str, str]:
    """
    Pure Python step: query ChromaDB for relevant policy clauses.
    Uses the decomposed compliance elements from Step 1 to form search queries.
    """
    decomposition_raw = inputs["step_1_decomposition"]

    # Parse decomposition JSON
    try:
        decomposition = json.loads(decomposition_raw)
    except json.JSONDecodeError:
        # Try to extract JSON from the LLM output
        import re
        match = re.search(r'\{[\s\S]*\}', decomposition_raw)
        if match:
            decomposition = json.loads(match.group())
        else:
            decomposition = {
                "regulations": [],
                "articles": [],
                "obligations": [],
                "system_context": "",
                "query_intent": "compliance_check",
            }

    # Build search queries from decomposition
    search_queries = []
    for obligation in decomposition.get("obligations", []):
        for reg in decomposition.get("regulations", ["AI governance"]):
            search_queries.append(f"{obligation} {reg}")
    for article in decomposition.get("articles", []):
        search_queries.append(article)

    # Fallback: use the original user query
    if not search_queries:
        search_queries = [inputs.get("user_query", "AI governance compliance")]

    # Query ChromaDB
    vs = VectorStoreManager()
    all_clauses = []

    for query in search_queries[:5]:  # Cap at 5 searches
        # Search governance docs collection
        results = vs.query(query, COLLECTION_HOUSING, n_results=3)
        if results["ids"] and results["ids"][0]:
            for doc_text, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                all_clauses.append({
                    "text": doc_text[:500],
                    "source_file": meta.get("source_file", ""),
                    "section": meta.get("section", ""),
                    "document_category": meta.get("document_category", ""),
                    "chunk_id": meta.get("chunk_id", ""),
                    "distance": round(dist, 4),
                })

        # Search structured policy collection
        s_results = vs.query(query, COLLECTION_STRUCTURED, n_results=2)
        if s_results["ids"] and s_results["ids"][0]:
            for doc_text, meta, dist in zip(
                s_results["documents"][0],
                s_results["metadatas"][0],
                s_results["distances"][0],
            ):
                all_clauses.append({
                    "text": doc_text[:500],
                    "source_file": meta.get("source_file", ""),
                    "section": meta.get("section", ""),
                    "document_category": meta.get("document_category", ""),
                    "chunk_id": meta.get("chunk_id", ""),
                    "distance": round(dist, 4),
                })

    # Deduplicate by chunk_id, then apply distance threshold
    DISTANCE_THRESHOLD = 0.85  # Filter out low-relevance results (Fix #1)
    seen = set()
    unique_clauses = []
    for clause in sorted(all_clauses, key=lambda x: x["distance"]):
        if clause["chunk_id"] not in seen:
            seen.add(clause["chunk_id"])
            if clause["distance"] <= DISTANCE_THRESHOLD:
                unique_clauses.append(clause)

    return {"step_2_retrieved_clauses": json.dumps(unique_clauses[:15], indent=2)}


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 3 — Compute Evidence from SQL (PURE PYTHON — NO LLM)
# ═══════════════════════════════════════════════════════════════════════════

def _step3_compute_evidence(inputs: dict[str, Any]) -> dict[str, str]:
    """
    Pure Python step: deterministic metric computation from inference_log.
    The LLM MUST NOT compute these metrics.
    """
    logger = InferenceLogger()
    logs = logger.get_all_logs()

    if not logs:
        metrics = {
            "total_queries": 0,
            "note": "No inference records found in the database.",
        }
        return {"step_3_evidence_metrics": json.dumps(metrics, indent=2)}

    # ── Deterministic computations ───────────────────────────────────────

    total_queries = len(logs)

    # Latency stats
    latencies = [l["latency_ms"] for l in logs if l.get("latency_ms") is not None]
    avg_latency = round(statistics.mean(latencies), 2) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 2)

    # HTTP status breakdown
    status_counts = {}
    for l in logs:
        s = str(l.get("http_status", "unknown"))
        status_counts[s] = status_counts.get(s, 0) + 1
    error_count = sum(v for k, v in status_counts.items() if k.startswith(("4", "5")))
    error_rate = round((error_count / total_queries) * 100, 2) if total_queries else 0

    # Evaluation stats
    eval_statuses = {}
    for l in logs:
        es = l.get("evaluation_status", "unknown")
        eval_statuses[es] = eval_statuses.get(es, 0) + 1
    eval_scores = [l["evaluation_score"] for l in logs
                   if l.get("evaluation_score") is not None and l["evaluation_score"] > 0]
    avg_eval_score = round(statistics.mean(eval_scores), 4) if eval_scores else 0
    min_eval_score = round(min(eval_scores), 4) if eval_scores else 0
    max_eval_score = round(max(eval_scores), 4) if eval_scores else 0

    # Review stats
    review_required_count = sum(1 for l in logs if l.get("review_required"))
    review_outcomes = {}
    for l in logs:
        ro = l.get("review_outcome", "unknown")
        review_outcomes[ro] = review_outcomes.get(ro, 0) + 1

    # Policy category breakdown
    policy_categories = {}
    for l in logs:
        pc = l.get("policy_category", "unknown")
        policy_categories[pc] = policy_categories.get(pc, 0) + 1

    # Model versions in use
    model_versions = list(set(l.get("model_version", "unknown") for l in logs))

    # ── Evidence interpretation guide (Fix #2) ──────────────────────────
    # Provides plain-English semantics to prevent LLM misinterpretation
    pending_reviews = review_outcomes.get("pending", 0)
    evidence_guide = {
        "review_required_meaning": (
            "review_required=True means the system CORRECTLY flagged outputs for human "
            "review — a HIGH rate is a POSITIVE oversight signal, not a compliance failure."
        ),
        "auto_approved_meaning": (
            "auto_approved means low-risk outputs passed automated evaluation (score >= threshold) "
            "and did NOT require human review — this is compliant behaviour."
        ),
        "pending_review_meaning": (
            f"{pending_reviews} reviews are currently PENDING human action "
            "— these represent an ACTUAL oversight gap requiring attention."
        ),
        "error_rate_meaning": (
            "error_rate_percent measures system reliability (HTTP 4xx/5xx), "
            "NOT the presence or absence of human oversight mechanisms."
        ),
        "eval_score_meaning": (
            "evaluation_score measures output quality (0.0–1.0). "
            "Scores below 0.70 should trigger mandatory human review."
        ),
    }

    metrics = {
        "total_queries": total_queries,
        "latency_ms": {
            "avg": avg_latency,
            "min": min_latency,
            "max": max_latency,
            "p95": p95_latency,
        },
        "http_status_breakdown": status_counts,
        "error_rate_percent": error_rate,
        "evaluation": {
            "status_breakdown": eval_statuses,
            "avg_score": avg_eval_score,
            "min_score": min_eval_score,
            "max_score": max_eval_score,
        },
        "review": {
            "review_required_count": review_required_count,
            "review_required_rate_percent": round(
                (review_required_count / total_queries) * 100, 2
            ) if total_queries else 0,
            "outcome_breakdown": review_outcomes,
            "pending_count": pending_reviews,
        },
        "policy_category_breakdown": policy_categories,
        "model_versions": model_versions,
        "evidence_interpretation_guide": evidence_guide,
        "computation_method": "deterministic_python_sql",
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    return {"step_3_evidence_metrics": json.dumps(metrics, indent=2)}


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 4 — Gap Analysis (LLM)
# ═══════════════════════════════════════════════════════════════════════════

STEP4_PROMPT = PromptTemplate(
    input_variables=["step_1_decomposition", "step_2_retrieved_clauses", "step_3_evidence_metrics"],
    template="""You are a regulatory compliance auditor performing a Gap Analysis.

You have THREE inputs. Do NOT invent or modify any numbers — use them exactly as provided.

## CRITICAL METRIC SEMANTICS — READ CAREFULLY BEFORE ANALYSIS:
The Step 3 evidence includes an `evidence_interpretation_guide` field with plain-English
explanations of each metric. You MUST follow these interpretations:
- `review_required=True` is a POSITIVE oversight signal — it means the system correctly
  flagged outputs for human review. A high review_required_rate is GOOD, not a gap.
- `auto_approved` outcomes mean low-risk outputs passed automated checks — this is compliant.
- The ACTUAL oversight gap is `review.pending_count` — outputs awaiting human action.
- `error_rate_percent` measures HTTP reliability, NOT oversight quality — do NOT use it
  as a proxy for oversight compliance.
- `evaluation_score` < 0.70 indicates an output quality gap, not an oversight mechanism gap.

## 1. COMPLIANCE ELEMENTS (from Step 1):
{step_1_decomposition}

## 2. RETRIEVED POLICY CLAUSES (from Step 2):
{step_2_retrieved_clauses}

## 3. COMPUTED EVIDENCE METRICS (from Step 3 — deterministic, DO NOT recalculate):
{step_3_evidence_metrics}

## Instructions:
For each obligation identified in Step 1, assess whether the system evidence satisfies the
policy requirement. Apply the metric semantics above. Be precise:
- Mark `compliant` only if you have affirmative evidence of compliance
- Mark `partial` if evidence exists but is incomplete
- Mark `non_compliant` only if evidence directly contradicts the requirement
- Mark `insufficient_data` if the metrics do not cover this obligation at all

Return a JSON object:
{{
  "gaps": [
    {{
      "obligation": "<obligation name>",
      "policy_requirement": "<what the policy requires>",
      "policy_source": "<source file and section>",
      "current_evidence": "<exact metric name and value from Step 3>",
      "status": "<compliant | partial | non_compliant | insufficient_data>",
      "gap_description": "<specific, concrete description — cite metric values>"
    }}
  ],
  "overall_gap_count": <number>,
  "critical_gaps": <count of non_compliant items only>
}}

IMPORTANT: Return ONLY the JSON object, no other text.

JSON output:""",
)


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 5 — Adjudicate (LLM)
# ═══════════════════════════════════════════════════════════════════════════

STEP5_PROMPT = PromptTemplate(
    input_variables=[
        "user_query",
        "step_1_decomposition",
        "step_2_retrieved_clauses",
        "step_3_evidence_metrics",
        "step_4_gap_analysis",
    ],
    template="""You are the Chief Compliance Officer adjudicating a regulatory compliance audit.

You have the complete audit trail from all steps. Produce the FINAL compliance determination.

## ORIGINAL QUERY:
{user_query}

## STEP 1 — DECOMPOSITION:
{step_1_decomposition}

## STEP 2 — RETRIEVED POLICY CLAUSES:
{step_2_retrieved_clauses}

## STEP 3 — COMPUTED EVIDENCE METRICS (do NOT modify these numbers):
{step_3_evidence_metrics}

## STEP 4 — GAP ANALYSIS:
{step_4_gap_analysis}

## Instructions:
Produce the final adjudication as a JSON object with this exact structure.

RULES:
1. `citations` MUST include ALL unique source documents and articles from Step 2. Do not omit any.
2. Do NOT generate `audit_id` or `timestamp` — leave them as empty strings "" (they will be set by the system).
3. `recommendations` must be specific and actionable, citing the exact metric or gap from Step 4.
4. `overall_status` must be consistent with the gap_analysis — if there are critical_gaps > 0, status cannot be COMPLIANT.

{{
  "audit_id": "",
  "timestamp": "",
  "query": "<original user query>",
  "overall_status": "<COMPLIANT | PARTIALLY_COMPLIANT | NON_COMPLIANT | INSUFFICIENT_DATA>",
  "confidence_score": <0.0 to 1.0>,
  "summary": "<2-3 sentence executive summary citing specific articles and metric values>",
  "citations": [
    {{
      "regulation": "<regulation name>",
      "article": "<article/clause reference>",
      "source_document": "<source file>",
      "relevance": "<how it applies to this query>"
    }}
  ],
  "recommendations": [
    "<specific recommendation citing the gap and the exact metric value>",
    "<specific recommendation with a concrete action and regulatory reference>"
  ],
  "reasoning_trace": {{
    "step_1_completed": true,
    "step_2_clauses_retrieved": <number>,
    "step_3_metrics_computed": true,
    "step_4_gaps_identified": <number>,
    "step_5_adjudication": "complete"
  }}
}}

IMPORTANT: Return ONLY the JSON object, no other text.

JSON output:""",
)


# ═══════════════════════════════════════════════════════════════════════════
#  PIPELINE ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def build_compliance_pipeline(
    model_name: Optional[str] = None,
    temperature: float = 0.1,
) -> SequentialChain:
    """
    Build and return the 5-step compliance audit SequentialChain.

    Steps 1, 4, 5 use the LLM (Groq).
    Steps 2, 3 are pure Python TransformChains.
    """
    # Ensure API key is present
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is missing or not set in the .env file. "
            "Please paste your valid Groq API key into the .env file."
        )

    llm = ChatGroq(
        model_name=model_name or GROQ_MODEL,
        temperature=temperature,
        api_key=api_key,
    )

    # Step 1: Decompose (LLM)
    step1_chain = LLMChain(
        llm=llm,
        prompt=STEP1_PROMPT,
        output_key="step_1_decomposition",
        verbose=False,
    )

    # Step 2: Retrieve clauses (Python)
    step2_chain = TransformChain(
        input_variables=["step_1_decomposition", "user_query"],
        output_variables=["step_2_retrieved_clauses"],
        transform=_step2_retrieve_clauses,
    )

    # Step 3: Compute evidence (Python)
    step3_chain = TransformChain(
        input_variables=["step_2_retrieved_clauses"],
        output_variables=["step_3_evidence_metrics"],
        transform=_step3_compute_evidence,
    )

    # Step 4: Gap analysis (LLM)
    step4_chain = LLMChain(
        llm=llm,
        prompt=STEP4_PROMPT,
        output_key="step_4_gap_analysis",
        verbose=False,
    )

    # Step 5: Adjudicate (LLM)
    step5_chain = LLMChain(
        llm=llm,
        prompt=STEP5_PROMPT,
        output_key="step_5_adjudication",
        verbose=False,
    )

    # Assemble the SequentialChain — enforces strict ordering
    pipeline = SequentialChain(
        chains=[step1_chain, step2_chain, step3_chain, step4_chain, step5_chain],
        input_variables=["user_query"],
        output_variables=[
            "step_1_decomposition",
            "step_2_retrieved_clauses",
            "step_3_evidence_metrics",
            "step_4_gap_analysis",
            "step_5_adjudication",
        ],
        verbose=True,
    )

    return pipeline


def run_compliance_audit(
    query: str,
    model_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Run the full 5-step compliance audit and return the structured report.

    Parameters
    ----------
    query : str
        The regulatory compliance question.
    model_name : str, optional
        Groq model name (default: llama3-8b-8192).

    Returns
    -------
    dict
        Full compliance report with all 5 reasoning steps.
    """
    pipeline = build_compliance_pipeline(model_name=model_name)

    print(f"\n{'='*70}")
    print("  COMPLIANCE AUDIT PIPELINE — 5-Step Deterministic Reasoning")
    print(f"{'='*70}")
    print(f"  Query: \"{query}\"")
    print(f"  Model: {model_name or GROQ_MODEL}")
    print(f"  Time:  {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"{'='*70}\n")

    # Execute the pipeline
    result = pipeline({"user_query": query})

    # ── Fix #5: Generate audit_id and timestamp in Python — never trust the LLM for these
    now_utc = datetime.now(timezone.utc)
    audit_id = f"AUDIT-{now_utc.strftime('%Y%m%d-%H%M%S')}"
    audit_timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Assemble the full report
    adjudication = _safe_parse_json(result.get("step_5_adjudication", "{}"))
    if isinstance(adjudication, dict):
        adjudication["audit_id"] = audit_id
        adjudication["timestamp"] = audit_timestamp

    report = {
        "audit_metadata": {
            "audit_id": audit_id,
            "query": query,
            "model": model_name or GROQ_MODEL,
            "timestamp": audit_timestamp,
            "pipeline_version": "1.1.0",
            "steps_completed": 5,
        },
        "step_1_decomposition": _safe_parse_json(result.get("step_1_decomposition", "{}")),
        "step_2_retrieved_clauses": _safe_parse_json(result.get("step_2_retrieved_clauses", "[]")),
        "step_3_evidence_metrics": _safe_parse_json(result.get("step_3_evidence_metrics", "{}")),
        "step_4_gap_analysis": _safe_parse_json(result.get("step_4_gap_analysis", "{}")),
        "step_5_adjudication": adjudication,
    }

    return report


def _safe_parse_json(text: str) -> Any:
    """Try to parse JSON from text, falling back to raw string."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_output": text}
