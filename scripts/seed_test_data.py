#!/usr/bin/env python3
"""
seed_test_data.py — Populate inference_log with realistic sample records.

Seeds ~20 inference records covering various policy categories, latencies,
HTTP statuses, evaluation scores, and review outcomes. Includes:
  - High-risk queries (emergency housing, domestic abuse, etc.) for RECI
  - Repeated/similar queries for UQRR
  - Responses with overcommitment language for OCR
  - Time-spread records across multiple days for BDI
"""

import os, sys, uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.inference_logger import InferenceLogger


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
        "ground_truth": "Article 12 of the EU AI Act requires high-risk AI systems to have automatic logging of events including period of use, reference databases queried, input data for matching, and natural persons identified. Biometric ID systems (Annex III, 1a) must retain logs for a minimum of 6 months.",
        "evaluation_timestamp": "2026-02-21T10:12:02Z",
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
        "ground_truth": "Yes. Under EU AI Act Article 14, high-risk AI systems must support effective human oversight including: understanding capabilities/limitations, anomaly detection, output interpretation, override/reversal capability, and a stop mechanism.",
        "evaluation_timestamp": "2026-02-21T11:30:00Z",
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
        "ground_truth": "Article 13 EU AI Act mandates transparency for high-risk systems: instructions must cover provider identity, capabilities/limitations, accuracy levels, known risks, performance across demographics, and oversight measures.",
        "evaluation_timestamp": "2026-02-21T14:15:00Z",
    },
    # ── GDPR queries ─────────────────────────────────────────────────────
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "Can we use fully automated credit scoring without human review?",
        "llm_output": "Under GDPR Article 22, data subjects have the right not to be subject to decisions based solely on automated processing which produce legal or similarly significant effects. You are eligible for an exemption only if you have explicit consent, contractual necessity, or legal authorisation. When exceptions apply, you must still provide the right to human intervention.",
        "latency_ms": 1350,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.91,
        "review_required": True,
        "review_outcome": "approved",
        "policy_category": "gdpr",
        "ground_truth": "GDPR Article 22 grants data subjects the right to not be subject to solely automated decisions with legal/significant effects. Exceptions: explicit consent, contractual necessity, or legal authorization. Must provide right to human intervention, express views, and contest decisions.",
        "evaluation_timestamp": "2026-02-22T09:45:00Z",
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
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-22T10:00:00Z",
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
        "ground_truth": "GDPR Article 5(2) accountability requires: processing records (Art 30), DPIAs (Art 35), data protection by design (Art 25), documented training data decisions, and audit-ready logs.",
        "evaluation_timestamp": "2026-02-22T15:00:00Z",
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
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-23T08:30:00Z",
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
        "ground_truth": "Yes — NIST AI RMF MS-2.2 mandates adversarial/red-team testing pre-deployment and ongoing to detect failure modes, hidden functionality, and emergent behaviour.",
        "evaluation_timestamp": "2026-02-23T09:00:00Z",
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
        "ground_truth": "ISO 42001 mandatory documentation: AIMS scope (4.3), AI policy (5.2), risk assessment (6.1.2), risk treatment (6.1.3), AI objectives (6.2), lifecycle docs (8.4), monitoring (9.1), internal audit (9.2), management review (9.3), corrective actions (10.1).",
        "evaluation_timestamp": "2026-02-23T14:00:00Z",
    },

    # ══════════════════════════════════════════════════════════════════════
    #  HIGH-RISK QUERIES — for RECI signal
    # ══════════════════════════════════════════════════════════════════════
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "I need emergency housing assistance, my landlord is evicting me tomorrow",
        "llm_output": "You will receive emergency housing support through the council's duty to assist. Contact your local authority immediately as they have a legal obligation under the Housing Act to prevent homelessness. You are eligible for emergency temporary accommodation while your case is assessed.",
        "latency_ms": 1420,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.76,
        "review_required": True,
        "review_outcome": "pending",
        "policy_category": "public_services",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-24T08:00:00Z",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "Where can I find domestic abuse support services in my area?",
        "llm_output": "If you are experiencing domestic abuse, please contact the National Domestic Abuse Helpline at 0808 2000 247 (24-hour, free). Your local council may also provide refuge accommodation and support services. You may be eligible for emergency financial assistance through the Domestic Violence Disclosure Scheme.",
        "latency_ms": 890,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.82,
        "review_required": True,
        "review_outcome": "pending",
        "policy_category": "public_services",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-24T08:15:00Z",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "I'm facing homelessness and need immediate financial relief for my family",
        "llm_output": "We will provide you with a referral to the emergency assistance programme. You are entitled to an emergency payment under the Discretionary Housing Payment scheme. Your application is approved for fast-track processing given the urgent circumstances.",
        "latency_ms": 1100,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.70,
        "review_required": True,
        "review_outcome": "pending",
        "policy_category": "public_services",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-24T08:30:00Z",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "My child is in a crisis situation and I need safeguarding advice urgently",
        "llm_output": "For immediate child protection concerns, contact your local children's services or call the NSPCC helpline at 0808 800 5000. If a child is in immediate danger, call 999. The Children Act 1989 requires local authorities to investigate when there are reasonable grounds.",
        "latency_ms": 780,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.88,
        "review_required": True,
        "review_outcome": "pending",
        "policy_category": "public_services",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-24T09:00:00Z",
    },

    # ══════════════════════════════════════════════════════════════════════
    #  REPEATED/SIMILAR QUERIES — for UQRR signal
    # ══════════════════════════════════════════════════════════════════════
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "How do I apply for emergency housing?",
        "llm_output": "To apply for emergency housing, contact your local council's housing team. You will need to demonstrate that you are homeless or at risk of homelessness within 56 days. The council will assess your priority need and local connection.",
        "latency_ms": 950,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.80,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "public_services",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-24T10:00:00Z",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "What is the process for applying for emergency housing assistance?",
        "llm_output": "The process for emergency housing involves contacting your local authority's housing options team. You will receive a homelessness assessment within a reasonable timeframe. If accepted, you are eligible for temporary accommodation.",
        "latency_ms": 1020,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.78,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "public_services",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-24T10:30:00Z",
    },

    # ══════════════════════════════════════════════════════════════════════
    #  OVERCOMMITMENT RESPONSES — for OCR signal
    # ══════════════════════════════════════════════════════════════════════
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v1",
        "user_input": "Am I eligible for the universal credit top-up?",
        "llm_output": "Based on the information provided, you are eligible for the universal credit top-up. You will receive funding within 5 working days after your claim is processed. We guarantee that your payment will be made on the scheduled date.",
        "latency_ms": 1150,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.65,
        "review_required": True,
        "review_outcome": "rejected",
        "policy_category": "public_services",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-25T08:00:00Z",
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
        "ground_truth": None,
        "evaluation_timestamp": None,
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
        "ground_truth": None,
        "evaluation_timestamp": None,
    },

    # ══════════════════════════════════════════════════════════════════════
    #  MODEL VERSION v2 RECORDS — for VID signal
    # ══════════════════════════════════════════════════════════════════════
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v2",
        "user_input": "What logging requirements apply to our biometric ID system under the EU AI Act?",
        "llm_output": "The EU AI Act (Article 12) mandates comprehensive automatic event logging for high-risk AI systems throughout their operational lifecycle. For biometric identification (Annex III, 1a), logs must capture: usage periods, reference databases queried, input data triggering matches, and identified natural persons. Minimum retention: 6 months. Additionally, Article 61 requires post-market monitoring plans that include logging provisions.",
        "latency_ms": 1150,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.93,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "eu_ai_act",
        "ground_truth": "Article 12 of the EU AI Act requires high-risk AI systems to have automatic logging of events including period of use, reference databases queried, input data for matching, and natural persons identified. Biometric ID systems (Annex III, 1a) must retain logs for a minimum of 6 months.",
        "evaluation_timestamp": "2026-02-25T14:00:00Z",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v2",
        "user_input": "Does our AI system need human oversight capabilities?",
        "llm_output": "Absolutely. Under Article 14 of the EU AI Act, all high-risk AI systems must incorporate effective human oversight mechanisms. Key requirements include: ability for oversight personnel to comprehend system capabilities and limitations, detect anomalies and unexpected outputs, correctly interpret system outputs, override or reverse automated decisions, and immediately halt system operation via a dedicated stop mechanism. Article 14(4) further specifies real-time monitoring capabilities.",
        "latency_ms": 1080,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.90,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "eu_ai_act",
        "ground_truth": "Yes. Under EU AI Act Article 14, high-risk AI systems must support effective human oversight including: understanding capabilities/limitations, anomaly detection, output interpretation, override/reversal capability, and a stop mechanism.",
        "evaluation_timestamp": "2026-02-25T14:30:00Z",
    },
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v2",
        "user_input": "Can we use fully automated credit scoring without human review?",
        "llm_output": "GDPR Article 22(1) establishes a general prohibition on purely automated decision-making that produces legal or similarly significant effects. Exceptions under Article 22(2) are narrow: explicit consent, contractual necessity, or EU/Member State law authorisation. Even when exceptions apply, Article 22(3) mandates safeguards: right to obtain human intervention, right to express a point of view, and right to contest the decision. For credit scoring specifically, a DPIA under Article 35 is likely required.",
        "latency_ms": 1300,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.92,
        "review_required": True,
        "review_outcome": "approved",
        "policy_category": "gdpr",
        "ground_truth": "GDPR Article 22 grants data subjects the right to not be subject to solely automated decisions with legal/significant effects. Exceptions: explicit consent, contractual necessity, or legal authorization. Must provide right to human intervention, express views, and contest decisions.",
        "evaluation_timestamp": "2026-02-25T15:00:00Z",
    },

    # ══════════════════════════════════════════════════════════════════════
    #  HIGH-LATENCY & BREACH RECORDS — for OVI + ETBR signal
    # ══════════════════════════════════════════════════════════════════════
    {
        "query_id": str(uuid.uuid4()),
        "model_version": "llama3-8b-v2",
        "user_input": "What are the full details of NIST AI RMF's GOVERN function?",
        "llm_output": "The GOVERN function in NIST AI RMF encompasses six sub-categories (GV-1 through GV-6). GV-1 establishes risk tolerance and appetite. GV-2 documents roles and responsibilities via RACI matrices. GV-3 addresses workforce diversity and domain expertise. GV-4 fosters organizational culture. GV-5 ensures stakeholder engagement. GV-6 mandates contingency processes including incident response and kill-switch procedures.",
        "latency_ms": 4500,
        "http_status": 200,
        "evaluation_status": "passed",
        "evaluation_score": 0.85,
        "review_required": False,
        "review_outcome": "auto_approved",
        "policy_category": "nist_ai_rmf",
        "ground_truth": None,
        "evaluation_timestamp": "2026-02-25T16:00:00Z",
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
