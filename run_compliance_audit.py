#!/usr/bin/env python3
"""
run_compliance_audit.py — CLI entrypoint for the Compliance Audit Pipeline.

Usage:
    python run_compliance_audit.py "Your regulatory compliance query here"

Options (via env vars):
    GROQ_MODEL       — Groq model name (default: llama3-8b-8192)
    GROQ_API_KEY     — Your Groq API key (put in .env file)
"""

# ── Fix macOS OpenBLAS / SciPy deadlock ──────────────────────────────────
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from compliance_pipeline import run_compliance_audit


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_compliance_audit.py \"<regulatory query>\"")
        print()
        print("Examples:")
        print('  python run_compliance_audit.py "Is our AI system compliant with EU AI Act Article 14 human oversight requirements?"')
        print('  python run_compliance_audit.py "Does our ML pipeline satisfy GDPR Article 22 automated decision-making safeguards?"')
        print('  python run_compliance_audit.py "Are we meeting NIST AI RMF MEASURE function requirements for risk monitoring?"')
        sys.exit(1)

    query = sys.argv[1]

    # Optional: override model via CLI arg
    model = sys.argv[2] if len(sys.argv) > 2 else None

    report = run_compliance_audit(query, model_name=model)

    # Print the full structured report
    print("\n" + "=" * 70)
    print("  STRUCTURED COMPLIANCE REPORT (JSON)")
    print("=" * 70)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("=" * 70)

    # Save to file
    output_path = os.path.join(PROJECT_ROOT, "audit", "latest_compliance_report.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Report saved to: {output_path}\n")


if __name__ == "__main__":
    main()
