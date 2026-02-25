#!/usr/bin/env python3
"""
api.py — FastAPI Backend for GovernedRAG Compliance Dashboard
==============================================================

Endpoints:
    GET  /api/metrics          — All 8 governance metrics (with embeddings)
    GET  /api/metrics/fast     — Metrics without embedding computation (RECI, OCR, MDR, OVI, ETBR)
    GET  /api/logs             — Inference log entries
    POST /api/query            — PolicySearch on vector DB
    POST /api/chat             — Compliance chatbot (ReAct agent)

Frontend:
    Serves static files from ./frontend/ at root path
"""

# ── Fix macOS OpenBLAS / SciPy deadlock ──────────────────────────────────
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import sys
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

# ── FastAPI App ──────────────────────────────────────────────────────────

app = FastAPI(
    title="GovernedRAG — Compliance Dashboard API",
    description="API endpoints for AI governance metrics, inference logs, policy search, and compliance chatbot.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ── Request/Response Models ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5

class ChatRequest(BaseModel):
    query: str
    model: Optional[str] = None


# ── Lazy Loaders (avoid startup overhead) ────────────────────────────────

_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        print("[API] Loading embedding model: BAAI/bge-m3")
        _embedder = SentenceTransformer("BAAI/bge-m3")
    return _embedder


# ═══════════════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/metrics")
def get_metrics():
    """Compute all 8 governance metrics (includes embedding-based metrics UQRR, BDI, VID)."""
    from metrics.governance_metrics import compute_all_metrics
    try:
        results = compute_all_metrics(include_embeddings=True)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/fast")
def get_metrics_fast():
    """Compute non-embedding metrics only (RECI, OCR, MDR, OVI, ETBR)."""
    from metrics.governance_metrics import compute_all_metrics
    try:
        results = compute_all_metrics(include_embeddings=False)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
def get_logs():
    """Return all inference log entries."""
    from core.inference_logger import InferenceLogger
    try:
        logger = InferenceLogger()
        logs = logger.get_all_logs()
        return {
            "total": len(logs),
            "logs": logs,
            "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
def policy_search(req: QueryRequest):
    """Search the vector DB for relevant policy clauses."""
    from agents.retrieval_tools import _policy_search
    from core.inference_logger import InferenceLogger
    start = time.time()
    try:
        result_str = _policy_search(req.query)
        result = json.loads(result_str)
        latency = int((time.time() - start) * 1000)
        http_status = 200
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        # Log the error too
        try:
            InferenceLogger().log_inference(
                query_id=str(uuid.uuid4()),
                model_version="policy_search_bge-m3",
                user_input=req.query,
                llm_output=f"Error: {str(e)}",
                latency_ms=latency,
                http_status=500,
                evaluation_status="error",
                policy_category="policy_search",
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

    # Log successful query
    try:
        total = result.get("total_results", 0)
        output_summary = f"Found {total} policy clauses (threshold: {result.get('distance_threshold', 'N/A')})"
        InferenceLogger().log_inference(
            query_id=str(uuid.uuid4()),
            model_version="policy_search_bge-m3",
            user_input=req.query,
            llm_output=output_summary,
            latency_ms=latency,
            http_status=200,
            evaluation_status="passed" if total > 0 else "no_results",
            evaluation_score=round(1.0 - result["clauses"][0]["distance"], 4) if result.get("clauses") else 0.0,
            policy_category="policy_search",
        )
    except Exception as log_err:
        print(f"[API] Warning: failed to log query: {log_err}")

    return result


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Chat with the compliance agent (ReAct loop)."""
    from agents.compliance_agent import run_agent_audit
    from core.inference_logger import InferenceLogger
    start = time.time()
    try:
        report = run_agent_audit(
            query=req.query,
            model_name=req.model,
            verbose=False,
        )
        latency = int((time.time() - start) * 1000)
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        try:
            InferenceLogger().log_inference(
                query_id=str(uuid.uuid4()),
                model_version=req.model or "llama-3.3-70b-versatile",
                user_input=req.query,
                llm_output=f"Error: {str(e)}",
                latency_ms=latency,
                http_status=500,
                evaluation_status="error",
                policy_category="compliance_audit",
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

    # Log the audit result
    try:
        compliance = report.get("compliance_report", {})
        adjudication = compliance.get("step_5_adjudication", {})
        status = adjudication.get("overall_status", "UNKNOWN")
        confidence = adjudication.get("confidence_score", 0.0)
        summary = adjudication.get("summary", str(compliance)[:500])

        InferenceLogger().log_inference(
            query_id=report.get("audit_metadata", {}).get("audit_id", str(uuid.uuid4())),
            model_version=req.model or "llama-3.3-70b-versatile",
            user_input=req.query,
            llm_output=summary,
            latency_ms=latency,
            http_status=200,
            evaluation_status=status.lower(),
            evaluation_score=float(confidence) if confidence else 0.0,
            review_required=status != "COMPLIANT",
            review_outcome="pending" if status != "COMPLIANT" else "auto_approved",
            policy_category="compliance_audit",
        )
    except Exception as log_err:
        print(f"[API] Warning: failed to log audit: {log_err}")

    return report


@app.get("/api/report")
def generate_report(fast: bool = False):
    """Generate a structured compliance report combining metrics + logs."""
    from metrics.governance_metrics import compute_all_metrics
    from core.inference_logger import InferenceLogger

    try:
        metrics = compute_all_metrics(include_embeddings=not fast)
        logger = InferenceLogger()
        logs = logger.get_all_logs()

        # Compute summary stats from logs
        total_logs = len(logs)
        error_logs = sum(1 for l in logs if l.get("http_status", 200) != 200)
        review_flagged = sum(1 for l in logs if l.get("review_required"))
        categories = {}
        for l in logs:
            cat = l.get("policy_category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        avg_latency = sum(l.get("latency_ms", 0) for l in logs) / max(total_logs, 1)

        # Threshold assessments for all 8 metrics
        # Lower is better: RECI, UQRR, BDI, OCR, VID, OVI, ETBR
        # Higher is better: MDR
        summary = metrics.get("dashboard_summary", {})
        thresholds = {
            "RECI": {"value": summary.get("RECI"), "green": 10, "amber": 25, "unit": "%", "lower_is_better": True},
            "UQRR": {"value": summary.get("UQRR"), "green": 10, "amber": 25, "unit": "%", "lower_is_better": True},
            "BDI": {"value": summary.get("BDI"), "green": 0.10, "amber": 0.20, "unit": "score", "lower_is_better": True},
            "OCR": {"value": summary.get("OCR"), "green": 5, "amber": 15, "unit": "%", "lower_is_better": True},
            "VID": {"value": summary.get("VID"), "green": 0.10, "amber": 0.20, "unit": "score", "lower_is_better": True},
            "MDR": {"value": summary.get("MDR"), "green": 70, "amber": 50, "unit": "%"},
            "OVI": {"value": summary.get("OVI"), "green": 0.30, "amber": 0.50, "unit": "CV", "lower_is_better": True},
            "ETBR": {"value": summary.get("ETBR"), "green": 5, "amber": 10, "unit": "%", "lower_is_better": True},
        }

        assessments = {}
        for key, t in thresholds.items():
            val = t["value"]
            if val is None:
                assessments[key] = {"status": "N/A", "value": None}
                continue
            if t.get("lower_is_better"):
                if val <= t["green"]:
                    status = "GREEN"
                elif val <= t["amber"]:
                    status = "AMBER"
                else:
                    status = "RED"
            else:
                if val >= t["green"]:
                    status = "GREEN"
                elif val >= t["amber"]:
                    status = "AMBER"
                else:
                    status = "RED"
            assessments[key] = {"status": status, "value": val, "unit": t["unit"]}

        # Overall compliance score
        scores = []
        # Lower-is-better metrics (invert)
        for key in ["RECI", "UQRR", "OCR", "ETBR"]:
            if summary.get(key) is not None:
                scores.append(1.0 - min(summary[key] / 100, 1.0))
        for key in ["BDI", "VID", "OVI"]:
            if summary.get(key) is not None:
                scores.append(1.0 - min(summary[key], 1.0))
        # Higher-is-better metric (MDR)
        if summary.get("MDR") is not None:
            scores.append(min(summary["MDR"] / 100, 1.0))
        overall_score = round(sum(scores) / max(len(scores), 1), 4)

        green_count = sum(1 for a in assessments.values() if a["status"] == "GREEN")
        amber_count = sum(1 for a in assessments.values() if a["status"] == "AMBER")
        red_count = sum(1 for a in assessments.values() if a["status"] == "RED")

        if red_count >= 2:
            overall_status = "NON_COMPLIANT"
        elif red_count >= 1 or amber_count >= 2:
            overall_status = "PARTIALLY_COMPLIANT"
        else:
            overall_status = "COMPLIANT"

        report = {
            "report_metadata": {
                "title": "GovernedRAG — AI Governance Compliance Report",
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "report_type": "quick" if fast else "full",
                "frameworks": ["EU AI Act", "GDPR", "NIST AI RMF", "ISO/IEC 42001"],
            },
            "overall_assessment": {
                "status": overall_status,
                "score": overall_score,
                "green_metrics": green_count,
                "amber_metrics": amber_count,
                "red_metrics": red_count,
            },
            "metric_assessments": assessments,
            "metrics_detail": metrics.get("metrics", {}),
            "interpretations": {k: v.get("interpretation", v.get("reason", ""))
                                for k, v in metrics.get("metrics", {}).items()},
            "log_summary": {
                "total_interactions": total_logs,
                "error_count": error_logs,
                "error_rate_pct": round(error_logs / max(total_logs, 1) * 100, 2),
                "review_flagged": review_flagged,
                "avg_latency_ms": round(avg_latency, 1),
                "by_category": categories,
            },
            "recommendations": [],
        }

        # Generate recommendations based on assessments
        if assessments.get("RECI", {}).get("status") == "RED":
            report["recommendations"].append("CRITICAL: High concentration of risk-sensitive queries. Investigate potential real-world crisis or policy confusion.")
        elif assessments.get("RECI", {}).get("status") == "AMBER":
            report["recommendations"].append("Elevated risk query concentration. Monitor sensitive policy domains for emerging trends.")
        if assessments.get("UQRR", {}).get("status") in ("RED", "AMBER"):
            report["recommendations"].append("High query recurrence detected. Citizens may be stuck in frustration loops — update knowledge base for recurring topics.")
        if assessments.get("BDI", {}).get("status") in ("RED", "AMBER"):
            report["recommendations"].append("Behavioural drift detected. Model responses are diverging from approved baseline — review for tone or policy stance changes.")
        if assessments.get("OCR", {}).get("status") == "RED":
            report["recommendations"].append("CRITICAL: High overcommitment ratio. Model is using legally binding language — immediate prompt refinement required.")
        elif assessments.get("OCR", {}).get("status") == "AMBER":
            report["recommendations"].append("Overcommitment phrases detected. Review responses for definitive language and enforce probabilistic phrasing.")
        if assessments.get("VID", {}).get("status") in ("RED", "AMBER"):
            report["recommendations"].append("Version impact deviation detected. New model version shows significant behavioural shift — verify ethical standards before deployment.")
        if assessments.get("MDR", {}).get("status") == "RED":
            report["recommendations"].append("CRITICAL: Human oversight coverage is dangerously low. Increase review sampling rate to meet EU AI Act HITL requirements.")
        elif assessments.get("MDR", {}).get("status") == "AMBER":
            report["recommendations"].append("Human oversight coverage below target. Consider increasing review sampling to improve compliance posture.")
        if assessments.get("OVI", {}).get("status") in ("RED", "AMBER"):
            report["recommendations"].append("High operational volatility detected. System latency is inconsistent — investigate infrastructure instability.")
        if assessments.get("ETBR", {}).get("status") == "RED":
            report["recommendations"].append("🚨 CRITICAL: High escalation threshold breach rate. Immediate system investigation and potential rollback required.")
        elif assessments.get("ETBR", {}).get("status") == "AMBER":
            report["recommendations"].append("Escalation threshold breaches detected. Review safety guardrail configuration and address root causes.")
        if error_logs > 0:
            report["recommendations"].append(f"{error_logs} error responses detected. Investigate HTTP 4xx/5xx failures.")
        if not report["recommendations"]:
            report["recommendations"].append("All metrics within acceptable thresholds. Continue current monitoring cadence.")

        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Serve Frontend ───────────────────────────────────────────────────────

frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))


# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=True)
