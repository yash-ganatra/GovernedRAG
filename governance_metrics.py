#!/usr/bin/env python3
"""
governance_metrics.py — 4 Dashboard-Ready Compliance Governance Metrics
========================================================================

All metrics are computed DETERMINISTICALLY in Python — no LLM involvement.

Two monitoring layers:

  Layer 1 — User Query Monitoring (data source: user queries)
      1. RECI  — Risk Exposure Concentration Index
      2. UQRR  — Unresolved Query Recurrence Rate

  Layer 2 — LLM Behaviour Monitoring (data source: LLM responses)
      3. BDI   — Behavioural Drift Index
      4. OCR   — Overcommitment Ratio

Metrics 2, 3 require embedding computation (BGE-M3 model).
"""

import os
import sys
import json
import math
import statistics
from datetime import datetime, timezone
from typing import Any, Optional
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from embedding_pipeline.inference_logger import InferenceLogger


# ── Risk keywords for RECI classification ────────────────────────────
# Queries containing any of these terms are flagged as high-risk.
RISK_KEYWORDS = [
    "emergency housing", "domestic abuse", "domestic violence",
    "immediate relief", "financial relief", "crisis",
    "eviction", "homelessness", "homeless",
    "urgent assistance", "emergency aid", "emergency benefit",
    "child protection", "safeguarding", "vulnerable",
    "mental health crisis", "suicide", "self-harm",
    "food bank", "destitution", "rough sleeping",
    "immediate financial", "emergency payment",
]

# ── Deterministic / overcommitment phrases for OCR ───────────────────
# Phrases that constitute legally binding or definitive language.
OVERCOMMITMENT_PHRASES = [
    "you will receive", "you are eligible", "you are entitled",
    "we will provide", "you are guaranteed", "guaranteed to",
    "we guarantee", "you qualify for", "you have been approved",
    "your application is approved", "we confirm that you",
    "you will be given", "you shall receive",
    "your entitlement is", "we will grant",
    "you are approved for", "funding has been approved",
    "benefit will be paid", "payment will be made",
    "you are confirmed for",
]


def _get_embedder():
    """Lazy-load the BGE-M3 embedding model (shared with VectorStoreManager)."""
    from sentence_transformers import SentenceTransformer
    print("[Metrics] Loading embedding model: BAAI/bge-m3")
    return SentenceTransformer("BAAI/bge-m3")


def _cosine_similarity(vec_a, vec_b) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _centroid(vectors):
    """Compute the mean centroid of a list of vectors."""
    if not vectors:
        return None
    dim = len(vectors[0])
    centroid = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            centroid[i] += float(v[i])
    n = len(vectors)
    return [c / n for c in centroid]


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 1 — User Query Monitoring
# ═══════════════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 1 — Risk Exposure Concentration Index (RECI)
# ───────────────────────────────────────────────────────────────────────────

def _is_high_risk(query: str, risk_keywords: list[str] = None) -> bool:
    """Classifier function f_risk(q): returns True if query matches any risk keyword."""
    keywords = risk_keywords or RISK_KEYWORDS
    q_lower = query.lower()
    return any(kw in q_lower for kw in keywords)


def compute_reci(logs: list[dict], risk_keywords: list[str] = None) -> dict:
    """
    RECI = Σ f_risk(q) / |Q_t|

    Density metric quantifying the volume of incoming queries related to
    highly sensitive or critical public policy domains within a timeframe.
    """
    if not logs:
        return {"metric": "RECI", "value": 0.0, "total": 0, "high_risk": 0}

    valid = [l for l in logs if l.get("user_input") and l["user_input"].strip()]
    if not valid:
        return {"metric": "RECI", "value": 0.0, "total": len(logs), "high_risk": 0}

    high_risk_entries = []
    for log in valid:
        if _is_high_risk(log["user_input"], risk_keywords):
            high_risk_entries.append({
                "query_id": log.get("query_id", ""),
                "user_input_preview": log["user_input"][:100],
                "timestamp": log.get("timestamp", ""),
            })

    reci = round(len(high_risk_entries) / len(valid), 4)

    # Detect clustering by date
    daily_risk = defaultdict(int)
    daily_total = defaultdict(int)
    for log in valid:
        date = log.get("timestamp", "")[:10]
        if date:
            daily_total[date] += 1
            if _is_high_risk(log["user_input"], risk_keywords):
                daily_risk[date] += 1

    daily_reci = {}
    for date in sorted(daily_total.keys()):
        daily_reci[date] = round(daily_risk[date] / daily_total[date], 4) if daily_total[date] else 0.0

    return {
        "metric": "RECI",
        "name": "Risk Exposure Concentration Index",
        "layer": "Layer 1: User Query Monitoring",
        "value": reci,
        "value_percent": round(reci * 100, 2),
        "total_queries": len(valid),
        "high_risk_queries": len(high_risk_entries),
        "high_risk_entries": high_risk_entries[:20],  # Cap detail to 20
        "daily_reci": daily_reci,
        "risk_keywords_used": len(risk_keywords or RISK_KEYWORDS),
        "interpretation": (
            f"{round(reci * 100, 2)}% of queries ({len(high_risk_entries)}/{len(valid)}) "
            f"are flagged as high-risk (sensitive policy domains). "
            + (f"Risk concentration detected across {len(daily_reci)} day(s)."
               if daily_reci else "No timestamped data for daily breakdown.")
        ),
    }


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 2 — Unresolved Query Recurrence Rate (UQRR)
# ───────────────────────────────────────────────────────────────────────────

def compute_uqrr(logs: list[dict], similarity_threshold: float = 0.90,
                 embedder=None) -> dict:
    """
    UQRR = |{(q_i, q_j) : CosineSim(E(q_i), E(q_j)) ≥ θ, i ≠ j}| / |Q|

    Measures the frequency with which semantically identical queries recur,
    indicating the AI's initial response failed to resolve the issue.
    """
    if not logs:
        return {"metric": "UQRR", "value": None, "total": 0}

    valid = [l for l in logs if l.get("user_input") and l["user_input"].strip()]

    if len(valid) < 2:
        return {
            "metric": "UQRR",
            "name": "Unresolved Query Recurrence Rate",
            "layer": "Layer 1: User Query Monitoring",
            "value": None,
            "valid_entries": len(valid),
            "interpretation": "Need at least 2 valid queries to measure recurrence.",
        }

    if embedder is None:
        embedder = _get_embedder()

    queries = [l["user_input"] for l in valid]
    q_embeddings = embedder.encode(queries, normalize_embeddings=True)

    # Find recurring query pairs
    recurring_indices = set()
    recurring_pairs = []

    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            sim = float(_cosine_similarity(q_embeddings[i], q_embeddings[j]))
            if sim >= similarity_threshold:
                recurring_indices.add(i)
                recurring_indices.add(j)
                if len(recurring_pairs) < 15:  # Cap detail
                    recurring_pairs.append({
                        "query_a": queries[i][:80],
                        "query_b": queries[j][:80],
                        "similarity": round(sim, 4),
                    })

    uqrr = round(len(recurring_indices) / len(valid), 4)

    return {
        "metric": "UQRR",
        "name": "Unresolved Query Recurrence Rate",
        "layer": "Layer 1: User Query Monitoring",
        "value": uqrr,
        "value_percent": round(uqrr * 100, 2),
        "total_queries": len(valid),
        "recurring_query_count": len(recurring_indices),
        "recurring_pairs_found": len(recurring_pairs),
        "recurring_pairs": recurring_pairs,
        "similarity_threshold": similarity_threshold,
        "interpretation": (
            f"{round(uqrr * 100, 2)}% of queries ({len(recurring_indices)}/{len(valid)}) "
            f"are semantically recurring (similarity ≥ {similarity_threshold}). "
            + ("High UQRR indicates citizens are caught in a frustration loop — "
               "the AI's guidance may be inadequate for these topics."
               if uqrr > 0.2 else
               "UQRR is within acceptable range — most queries are unique or resolved.")
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 2 — LLM Behaviour Monitoring
# ═══════════════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 3 — Behavioural Drift Index (BDI)
# ───────────────────────────────────────────────────────────────────────────

def compute_bdi(logs: list[dict], baseline_fraction: float = 0.5,
                embedder=None) -> dict:
    """
    BDI = 1 - CosineSim(C_t, C_base)

    Temporal metric calculating the semantic divergence of model responses
    over time compared to a historically approved baseline.

    The first `baseline_fraction` of chronologically sorted responses form
    the baseline; the remainder form the current window.
    """
    if not logs:
        return {"metric": "BDI", "value": None, "total": 0}

    valid = [l for l in logs if l.get("llm_output") and l["llm_output"].strip()
             and l.get("timestamp")]

    if len(valid) < 4:
        return {
            "metric": "BDI",
            "name": "Behavioural Drift Index",
            "layer": "Layer 2: LLM Behaviour Monitoring",
            "value": None,
            "valid_entries": len(valid),
            "interpretation": "Need at least 4 timestamped responses to compute drift.",
        }

    # Sort chronologically
    valid.sort(key=lambda l: l["timestamp"])

    if embedder is None:
        embedder = _get_embedder()

    responses = [l["llm_output"] for l in valid]
    r_embeddings = embedder.encode(responses, normalize_embeddings=True)

    # Split into baseline and current
    split_idx = max(2, int(len(valid) * baseline_fraction))
    baseline_embeds = [list(r_embeddings[i]) for i in range(split_idx)]
    current_embeds = [list(r_embeddings[i]) for i in range(split_idx, len(valid))]

    if not current_embeds:
        return {
            "metric": "BDI",
            "name": "Behavioural Drift Index",
            "layer": "Layer 2: LLM Behaviour Monitoring",
            "value": None,
            "interpretation": "Not enough current-window data to compute drift.",
        }

    c_base = _centroid(baseline_embeds)
    c_current = _centroid(current_embeds)
    similarity = _cosine_similarity(c_base, c_current)
    bdi = round(1.0 - similarity, 4)

    # Time range info
    baseline_start = valid[0].get("timestamp", "")[:10]
    baseline_end = valid[split_idx - 1].get("timestamp", "")[:10]
    current_start = valid[split_idx].get("timestamp", "")[:10]
    current_end = valid[-1].get("timestamp", "")[:10]

    return {
        "metric": "BDI",
        "name": "Behavioural Drift Index",
        "layer": "Layer 2: LLM Behaviour Monitoring",
        "value": bdi,
        "centroid_similarity": round(similarity, 4),
        "baseline_size": split_idx,
        "current_size": len(valid) - split_idx,
        "baseline_period": f"{baseline_start} → {baseline_end}",
        "current_period": f"{current_start} → {current_end}",
        "total_entries": len(valid),
        "interpretation": (
            f"Behavioural Drift Index: {bdi} (0.0 = no drift, 1.0 = total divergence). "
            f"Centroid similarity between baseline ({split_idx} responses, {baseline_start}→{baseline_end}) "
            f"and current ({len(valid) - split_idx} responses, {current_start}→{current_end}): "
            f"{round(similarity, 4)}. "
            + ("⚠️ Significant drift detected — model behaviour is diverging from baseline."
               if bdi > 0.15 else
               "Drift is within acceptable range — model behaviour is stable.")
        ),
    }


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 4 — Overcommitment Ratio (OCR)
# ───────────────────────────────────────────────────────────────────────────

def compute_ocr(logs: list[dict],
                deterministic_phrases: list[str] = None) -> dict:
    """
    OCR = Σ 1(R_i ∈ D) / N

    Frequency at which the LLM generates definitive, legally binding
    language rather than appropriate probabilistic language.
    """
    if not logs:
        return {"metric": "OCR", "value": 0.0, "total": 0, "overcommitted": 0}

    phrases = deterministic_phrases or OVERCOMMITMENT_PHRASES

    valid = [l for l in logs if l.get("llm_output") and l["llm_output"].strip()]
    if not valid:
        return {"metric": "OCR", "value": 0.0, "total": len(logs), "overcommitted": 0}

    overcommitted_entries = []
    for log in valid:
        output_lower = log["llm_output"].lower()
        matched_phrases = [p for p in phrases if p in output_lower]
        if matched_phrases:
            overcommitted_entries.append({
                "query_id": log.get("query_id", ""),
                "llm_output_preview": log["llm_output"][:120],
                "matched_phrases": matched_phrases,
            })

    ocr = round(len(overcommitted_entries) / len(valid), 4)

    # Phrase frequency breakdown
    phrase_hits = defaultdict(int)
    for entry in overcommitted_entries:
        for p in entry["matched_phrases"]:
            phrase_hits[p] += 1

    return {
        "metric": "OCR",
        "name": "Overcommitment Ratio",
        "layer": "Layer 2: LLM Behaviour Monitoring",
        "value": ocr,
        "value_percent": round(ocr * 100, 2),
        "total_responses": len(valid),
        "overcommitted_responses": len(overcommitted_entries),
        "overcommitted_entries": overcommitted_entries[:20],
        "phrase_frequency": dict(sorted(phrase_hits.items(),
                                         key=lambda x: x[1], reverse=True)),
        "phrases_checked": len(phrases),
        "interpretation": (
            f"{round(ocr * 100, 2)}% of responses ({len(overcommitted_entries)}/{len(valid)}) "
            f"contain legally binding or definitive language. "
            + ("⚠️ High overcommitment detected — risk of legal exposure. "
               "Responses should use probabilistic language (e.g., 'you may be eligible')."
               if ocr > 0.1 else
               "Overcommitment is within acceptable range.")
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 3 — Model Version & Inference Monitoring
# ═══════════════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 5 — Version Impact Deviation (VID)
# ───────────────────────────────────────────────────────────────────────────

def compute_vid(logs: list[dict], embedder=None) -> dict:
    """
    VID ≈ 1 − CosineSim(C_old, C_new)

    Quantifies the behavioral shift in model outputs following a version
    update, holding semantic intent constant. Groups responses by
    model_version, computes response centroids, and measures divergence
    between the two most recent versions.
    """
    if not logs:
        return {"metric": "VID", "value": None, "total": 0}

    valid = [l for l in logs if l.get("llm_output") and l["llm_output"].strip()
             and l.get("model_version") and l["model_version"].strip()]

    # Group by model version
    version_groups = defaultdict(list)
    for log in valid:
        version_groups[log["model_version"]].append(log)

    if len(version_groups) < 2:
        return {
            "metric": "VID",
            "name": "Version Impact Deviation",
            "layer": "Layer 3: Model Version & Inference Monitoring",
            "value": None,
            "versions_found": list(version_groups.keys()),
            "interpretation": (
                f"Only {len(version_groups)} model version(s) found "
                f"({', '.join(version_groups.keys()) or 'none'}). "
                f"Need at least 2 versions to compute deviation."
            ),
        }

    if embedder is None:
        embedder = _get_embedder()

    # Sort versions by earliest timestamp to determine old vs new
    version_timestamps = {}
    for version, vlogs in version_groups.items():
        timestamps = [l.get("timestamp", "") for l in vlogs if l.get("timestamp")]
        version_timestamps[version] = min(timestamps) if timestamps else ""

    sorted_versions = sorted(version_timestamps.keys(),
                             key=lambda v: version_timestamps[v])

    # Compare the two most recent versions
    old_version = sorted_versions[-2]
    new_version = sorted_versions[-1]

    old_responses = [l["llm_output"] for l in version_groups[old_version]]
    new_responses = [l["llm_output"] for l in version_groups[new_version]]

    old_embeddings = embedder.encode(old_responses, normalize_embeddings=True)
    new_embeddings = embedder.encode(new_responses, normalize_embeddings=True)

    old_centroid = _centroid([list(e) for e in old_embeddings])
    new_centroid = _centroid([list(e) for e in new_embeddings])

    similarity = _cosine_similarity(old_centroid, new_centroid)
    vid = round(1.0 - similarity, 4)

    return {
        "metric": "VID",
        "name": "Version Impact Deviation",
        "layer": "Layer 3: Model Version & Inference Monitoring",
        "value": vid,
        "centroid_similarity": round(similarity, 4),
        "old_version": old_version,
        "new_version": new_version,
        "old_version_count": len(old_responses),
        "new_version_count": len(new_responses),
        "all_versions": {v: len(g) for v, g in version_groups.items()},
        "interpretation": (
            f"Version Impact Deviation: {vid} (0.0 = identical behaviour, 1.0 = total divergence). "
            f"Comparing {old_version} ({len(old_responses)} responses) → "
            f"{new_version} ({len(new_responses)} responses). "
            f"Centroid similarity: {round(similarity, 4)}. "
            + ("⚠️ Significant version shift detected — verify the new version maintains "
               "ethical standards before full deployment."
               if vid > 0.15 else
               "Version update shows minimal behavioural impact.")
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 4 — Human Evaluation Monitoring
# ═══════════════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 6 — Monitoring Depth Ratio (MDR)
# ───────────────────────────────────────────────────────────────────────────

def compute_mdr(logs: list[dict]) -> dict:
    """
    MDR = N_reviewed / N_total

    The exact proportion of AI-generated responses that have been sampled,
    reviewed, and validated by a human domain expert.

    A response is considered 'reviewed' if review_outcome is not 'pending'
    and not empty — i.e., a human has actively approved, rejected, or
    annotated the response.
    """
    if not logs:
        return {"metric": "MDR", "value": 0.0, "total": 0, "reviewed": 0}

    reviewed_outcomes = {"approved", "rejected", "approved_with_notes", "auto_approved"}
    reviewed = 0
    pending = 0
    outcome_breakdown = defaultdict(int)

    for log in logs:
        outcome = (log.get("review_outcome") or "").strip().lower()
        outcome_breakdown[outcome or "none"] += 1
        if outcome in reviewed_outcomes:
            reviewed += 1
        elif outcome == "pending":
            pending += 1

    mdr = round(reviewed / len(logs), 4)

    return {
        "metric": "MDR",
        "name": "Monitoring Depth Ratio",
        "layer": "Layer 4: Human Evaluation Monitoring",
        "value": mdr,
        "value_percent": round(mdr * 100, 2),
        "total_responses": len(logs),
        "reviewed_responses": reviewed,
        "pending_responses": pending,
        "unreviewed_responses": len(logs) - reviewed - pending,
        "outcome_breakdown": dict(outcome_breakdown),
        "interpretation": (
            f"{round(mdr * 100, 2)}% of responses ({reviewed}/{len(logs)}) have been "
            f"reviewed by a human domain expert. "
            f"{pending} responses are still pending review. "
            + ("⚠️ Low human oversight coverage — increase sampling rate to meet "
               "EU AI Act HITL requirements."
               if mdr < 0.5 else
               "Human oversight coverage is adequate for regulatory compliance.")
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 5 — Operational Reliability Monitoring
# ═══════════════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 7 — Operational Volatility Index (OVI)
# ───────────────────────────────────────────────────────────────────────────

def compute_ovi(logs: list[dict]) -> dict:
    """
    OVI = σ_L / μ_L  (Coefficient of Variation of latency)

    Measures the instability and variance in system performance metrics,
    specifically latency, over a given time window.
    """
    if not logs:
        return {"metric": "OVI", "value": None, "total": 0}

    latencies = [l["latency_ms"] for l in logs
                 if l.get("latency_ms") is not None and l["latency_ms"] > 0]

    if len(latencies) < 2:
        return {
            "metric": "OVI",
            "name": "Operational Volatility Index",
            "layer": "Layer 5: Operational Reliability Monitoring",
            "value": None,
            "valid_entries": len(latencies),
            "interpretation": "Need at least 2 latency measurements to compute volatility.",
        }

    mean_lat = statistics.mean(latencies)
    stddev_lat = statistics.stdev(latencies)
    ovi = round(stddev_lat / mean_lat, 4) if mean_lat > 0 else 0.0

    # Compute percentiles
    sorted_lat = sorted(latencies)
    p50 = sorted_lat[len(sorted_lat) // 2]
    p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
    p95 = sorted_lat[p95_idx]

    return {
        "metric": "OVI",
        "name": "Operational Volatility Index",
        "layer": "Layer 5: Operational Reliability Monitoring",
        "value": ovi,
        "mean_latency_ms": round(mean_lat, 1),
        "stddev_latency_ms": round(stddev_lat, 1),
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "total_measurements": len(latencies),
        "interpretation": (
            f"Operational Volatility Index: {ovi} (CV = σ/μ). "
            f"Mean latency: {round(mean_lat, 1)}ms, StdDev: {round(stddev_lat, 1)}ms. "
            f"P50: {p50}ms, P95: {p95}ms. "
            + ("⚠️ High operational volatility — system is struggling to process "
               "queries consistently. Investigate infrastructure instability."
               if ovi > 0.5 else
               "Latency variance is within acceptable bounds — system is operationally stable.")
        ),
    }


# ───────────────────────────────────────────────────────────────────────────
#  METRIC 8 — Escalation Threshold Breach Rate (ETBR)
# ───────────────────────────────────────────────────────────────────────────

# Predefined operational and safety guardrails
SAFETY_THRESHOLDS = {
    "latency_max_ms": 3000,       # Max acceptable response time
    "http_error_codes": [400, 500, 502, 503, 504],  # Failure status codes
    "eval_score_min": 0.5,        # Minimum acceptable quality score
}


def compute_etbr(logs: list[dict], thresholds: dict = None) -> dict:
    """
    ETBR = Σ 1(E_t > τ) / N_total

    Frequency with which the system violates predefined hard-coded
    operational and safety guardrails.
    """
    if not logs:
        return {"metric": "ETBR", "value": 0.0, "total": 0, "breaches": 0}

    th = thresholds or SAFETY_THRESHOLDS

    breaching_entries = []
    for log in logs:
        breach_reasons = []

        # Latency breach
        lat = log.get("latency_ms")
        if lat is not None and lat > th["latency_max_ms"]:
            breach_reasons.append(f"latency={lat}ms > {th['latency_max_ms']}ms")

        # HTTP error code breach
        status = log.get("http_status")
        if status is not None and status in th["http_error_codes"]:
            breach_reasons.append(f"http_status={status}")

        # Evaluation score below minimum
        score = log.get("evaluation_score")
        if score is not None and score > 0 and score < th["eval_score_min"]:
            breach_reasons.append(f"eval_score={score} < {th['eval_score_min']}")

        if breach_reasons:
            breaching_entries.append({
                "query_id": log.get("query_id", "")[:12],
                "reasons": breach_reasons,
            })

    etbr = round(len(breaching_entries) / len(logs), 4)

    # Breach type breakdown
    breach_type_counts = defaultdict(int)
    for entry in breaching_entries:
        for reason in entry["reasons"]:
            category = reason.split("=")[0]
            breach_type_counts[category] += 1

    return {
        "metric": "ETBR",
        "name": "Escalation Threshold Breach Rate",
        "layer": "Layer 5: Operational Reliability Monitoring",
        "value": etbr,
        "value_percent": round(etbr * 100, 2),
        "total_events": len(logs),
        "breaching_events": len(breaching_entries),
        "breach_type_breakdown": dict(breach_type_counts),
        "breaching_entries": breaching_entries[:20],  # Cap detail
        "thresholds_used": th,
        "interpretation": (
            f"{round(etbr * 100, 2)}% of events ({len(breaching_entries)}/{len(logs)}) "
            f"breached operational safety guardrails. "
            + (f"Breach types: {', '.join(f'{k}({v})' for k, v in breach_type_counts.items())}. " if breach_type_counts else "")
            + ("🚨 CRITICAL: Escalating ETBR — immediate investigation and potential "
               "system rollback required."
               if etbr > 0.1 else
               "Breach rate is within acceptable limits.")
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  COMPUTE ALL METRICS
# ═══════════════════════════════════════════════════════════════════════════

def compute_all_metrics(
    logs: Optional[list[dict]] = None,
    include_embeddings: bool = True,
) -> dict:
    """
    Compute all 8 governance metrics at once.

    Parameters
    ----------
    logs : list[dict], optional
        Inference log entries. If None, fetches from the database.
    include_embeddings : bool
        If True, computes UQRR, BDI, and VID (requires BGE-M3 model).
        If False, skips those 3 metrics for faster execution.
    """
    if logs is None:
        logger = InferenceLogger()
        logs = logger.get_all_logs()

    embedder = None
    if include_embeddings and logs:
        embedder = _get_embedder()

    results = {
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_log_entries": len(logs),
        "computation_method": "deterministic_python",
        "metrics": {},
    }

    # Layer 1: User Query Monitoring
    # 1. RECI
    results["metrics"]["RECI"] = compute_reci(logs)

    # 2. UQRR (requires embeddings)
    if include_embeddings:
        results["metrics"]["UQRR"] = compute_uqrr(logs, embedder=embedder)
    else:
        results["metrics"]["UQRR"] = {"metric": "UQRR", "skipped": True, "reason": "Embeddings disabled"}

    # Layer 2: LLM Behaviour Monitoring
    # 3. BDI (requires embeddings)
    if include_embeddings:
        results["metrics"]["BDI"] = compute_bdi(logs, embedder=embedder)
    else:
        results["metrics"]["BDI"] = {"metric": "BDI", "skipped": True, "reason": "Embeddings disabled"}

    # 4. OCR
    results["metrics"]["OCR"] = compute_ocr(logs)

    # Layer 3: Model Version & Inference Monitoring
    # 5. VID (requires embeddings)
    if include_embeddings:
        results["metrics"]["VID"] = compute_vid(logs, embedder=embedder)
    else:
        results["metrics"]["VID"] = {"metric": "VID", "skipped": True, "reason": "Embeddings disabled"}

    # Layer 4: Human Evaluation Monitoring
    # 6. MDR
    results["metrics"]["MDR"] = compute_mdr(logs)

    # Layer 5: Operational Reliability Monitoring
    # 7. OVI
    results["metrics"]["OVI"] = compute_ovi(logs)

    # 8. ETBR
    results["metrics"]["ETBR"] = compute_etbr(logs)

    # Dashboard summary
    results["dashboard_summary"] = {
        "RECI": results["metrics"]["RECI"].get("value_percent"),
        "UQRR": results["metrics"]["UQRR"].get("value_percent"),
        "BDI": results["metrics"]["BDI"].get("value"),
        "OCR": results["metrics"]["OCR"].get("value_percent"),
        "VID": results["metrics"]["VID"].get("value"),
        "MDR": results["metrics"]["MDR"].get("value_percent"),
        "OVI": results["metrics"]["OVI"].get("value"),
        "ETBR": results["metrics"]["ETBR"].get("value_percent"),
    }

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compute governance metrics")
    parser.add_argument("--no-embeddings", action="store_true",
                        help="Skip embedding-based metrics (UQRR, BDI, VID)")
    parser.add_argument("--save", action="store_true",
                        help="Save results to audit/governance_metrics.json")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  GOVERNANCE METRICS — 8 Dashboard-Ready Compliance Metrics")
    print("  Layers 1–5: Query | LLM | Version | Human | Operational")
    print("=" * 70 + "\n")

    results = compute_all_metrics(include_embeddings=not args.no_embeddings)

    # Print dashboard summary
    print("  📊 DASHBOARD SUMMARY")
    print("  " + "-" * 50)
    for key, value in results["dashboard_summary"].items():
        val_str = f"{value}" if value is not None else "N/A"
        print(f"    {key:12s} : {val_str}")
    print()

    # Print each metric's interpretation
    for name, metric in results["metrics"].items():
        interp = metric.get("interpretation", metric.get("reason", ""))
        print(f"  [{name}] {interp}")
    print()

    if args.save:
        output_path = os.path.join(PROJECT_ROOT, "audit", "governance_metrics.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  📄 Saved to: {output_path}")

    print(f"\n  ✅ All metrics computed ({results['total_log_entries']} log entries)")

