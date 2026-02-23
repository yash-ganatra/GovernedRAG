#!/usr/bin/env python3
"""
seed_test_data.py — Populate inference_log with realistic sample records.

Seeds ~15 inference records covering various policy categories, latencies,
HTTP statuses, evaluation scores, and review outcomes so the Compliance
Audit Pipeline's Step 3 (evidence computation) has data to work with.
"""

import os, sys, uuid

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from embedding_pipeline.inference_logger import InferenceLogger


SEED_RECORDS = [
    # ── EU AI Act queries ────────────────────────────────────────────────
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What logging requirements apply to our biometric ID system under the EU AI Act?",
        "llm_output": "Under Article 12 of the EU AI Act, high-risk AI systems must automatically record events (logs) over their lifetime. For biometric identification systems (Annex III, point 1a), the minimum log contents include: period of each use, reference database checked, input data that led to matches, and identification of natural persons involved. Logs must be retained for at least 6 months.",
        "latency_ms": 1245,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.92,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "eu_ai_act",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "Does our AI system need human oversight capabilities?",
        "llm_output": "Yes. Article 14 of the EU AI Act mandates that high-risk AI systems must be designed to allow effective human oversight. Specifically, oversight personnel must be able to: understand system capabilities, detect anomalies, interpret outputs correctly, override or reverse outputs, and halt the system via a stop mechanism.",
        "latency_ms": 980,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.88,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "eu_ai_act",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What transparency requirements apply to our AI hiring tool?",
        "llm_output": "Article 13 of the EU AI Act requires that high-risk AI systems be sufficiently transparent for deployers to interpret outputs. Instructions for use must include: provider identity, system capabilities and limitations, accuracy metrics, known risks, demographic performance data, and human oversight measures.",
        "latency_ms": 1100,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.85,
        "review_required": True,
        "review_outcome": "approved_with_notes",
        "policy_category": "eu_ai_act",
    },
    # ── GDPR queries ─────────────────────────────────────────────────────
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "Can we use fully automated credit scoring without human review?",
        "llm_output": "Under GDPR Article 22, data subjects have the right not to be subject to decisions based solely on automated processing which produce legal or similarly significant effects. Exceptions require explicit consent, contractual necessity, or legal authorisation. When exceptions apply, you must still provide the right to human intervention, express a point of view, and contest the decision.",
        "latency_ms": 1350,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.91,
        "review_required": True,
        "review_outcome": "approved",
        "policy_category": "gdpr",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What must we tell users about how our AI processes their data?",
        "llm_output": "Under GDPR Article 15, data subjects can request: the purposes of processing, categories of data, recipients, retention periods, their rights, and — crucially — meaningful information about the logic involved in any automated decision-making, including the significance and envisaged consequences.",
        "latency_ms": 890,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.87,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "gdpr",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "How do we demonstrate GDPR accountability for our ML pipeline?",
        "llm_output": "Article 5(2) requires you to demonstrate compliance with all six processing principles. For AI systems this means: maintaining processing records (Art 30), conducting DPIAs (Art 35), implementing privacy by design (Art 25), documenting model training data decisions, and keeping audit logs for supervisory authority review.",
        "latency_ms": 1020,
        "http_status": 200,
        "evaluation_status": "failed",
        "evaluation_score": 0.62,
        "review_required": True,
        "review_outcome": "rejected",
        "policy_category": "gdpr",
    },
    # ── NIST AI RMF queries ──────────────────────────────────────────────
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What risk metrics should we track for our deployed AI models?",
        "llm_output": "Under NIST AI RMF MEASURE function (MS-1.1), you should select metrics from the concept phase onwards. Key metrics include: model accuracy/F1, fairness indicators (demographic parity), data quality measures, incident rates, explainability scores, and compliance posture. MS-2.5 requires validation across demographic groups.",
        "latency_ms": 1180,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.83,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "nist_ai_rmf",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "Do we need adversarial testing for our chatbot before deployment?",
        "llm_output": "Yes. NIST AI RMF MS-2.2 requires scientific methods including adversarial testing techniques such as red-teaming to identify failure modes, hidden functionality, or emergent behaviours. This should be conducted pre-deployment and on an ongoing basis.",
        "latency_ms": 750,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.79,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "nist_ai_rmf",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What governance structure does NIST recommend for AI?",
        "llm_output": "The GOVERN function (GV-1 through GV-6) recommends: establishing AI risk tolerance (GV-1.2), documenting roles/responsibilities with a RACI matrix (GV-2.1), fostering a safety-first culture (GV-4.1), creating incident response plans, and implementing contingency processes including kill-switch procedures (GV-6.2).",
        "latency_ms": 1310,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.90,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "nist_ai_rmf",
    },
    # ── ISO/IEC 42001 queries ────────────────────────────────────────────
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What documentation is mandatory under ISO 42001?",
        "llm_output": "ISO/IEC 42001 requires: AIMS scope (4.3), AI policy (5.2), risk assessment results (6.1.2), risk treatment plan (6.1.3), AI objectives (6.2), lifecycle documentation (8.4), monitoring results (9.1), internal audit results (9.2), management review results (9.3), and nonconformity/corrective action records (10.1).",
        "latency_ms": 1050,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.94,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "iso_42001",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What must our AI policy include?",
        "llm_output": "Per ISO/IEC 42001 Clause 5.2, the AI policy must include: commitments to satisfy applicable AI requirements, continual improvement of the AIMS, and responsible AI principles including fairness, transparency, accountability, and human oversight. It must be documented, communicated internally, and available to interested parties.",
        "latency_ms": 920,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.86,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "iso_42001",
    },
    # ── Error / edge-case records ────────────────────────────────────────
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "Explain the compliance requirements for our facial recognition system",
        "llm_output": "Error: context length exceeded. Unable to generate response.",
        "latency_ms": 5200,
        "http_status": 500,
        "evaluation_status": "error",
        "evaluation_score": 0.0,
        "review_required": True,
        "review_outcome": "pending",
        "policy_category": "eu_ai_act",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What are the penalties for non-compliance with the EU AI Act?",
        "llm_output": "The EU AI Act establishes tiered penalties: up to €35 million or 7% of global annual turnover for prohibited AI practices, up to €15 million or 3% for other violations, and up to €7.5 million or 1.5% for providing incorrect information. SMEs and startups benefit from proportionate caps.",
        "latency_ms": 1420,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.76,
        "review_required": True,
        "review_outcome": "pending",
        "policy_category": "eu_ai_act",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "How should we handle a data breach involving our AI training data?",
        "llm_output": "Under GDPR Article 33, you must notify the supervisory authority within 72 hours of becoming aware of a breach. Under ISO 42001 Clause 10.1, you must take corrective action, evaluate root cause, and update your AIMS. The NIST AI RMF GV-6.2 requires contingency processes for harmful outcomes.",
        "latency_ms": 1150,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.81,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "gdpr",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "",
        "llm_output": "Error: empty input received.",
        "latency_ms": 50,
        "http_status": 400,
        "evaluation_status": "error",
        "evaluation_score": 0.0,
        "review_required": False,
        "review_outcome": "auto_rejected",
        "policy_category": "general",
    },
]


def main():
    logger = InferenceLogger()
    print(f"\n{'='*60}")
    print("  Seeding inference_log with sample records")
    print(f"{'='*60}\n")

    for record in SEED_RECORDS:
        try:
            logger.log_inference(**record)
        except Exception as e:
            print(f"  ⚠ Skipping duplicate or error: {e}")

    all_logs = logger.get_all_logs()
    print(f"\n  ✅ Total records in inference_log: {len(all_logs)}")
    print(f"  DB path: {logger.db_path}")

    # Summary stats
    categories = {}
    for log in all_logs:
        cat = log.get("policy_category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    print(f"\n  Records by policy_category:")
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count}")
    print()


if __name__ == "__main__":
    main()
