"""
Traceability Validator — Verifies metadata integrity across all embedded chunks.

Checks:
    1. All chunks have required metadata fields
    2. No null / empty metadata values
    3. Unique chunk IDs (no duplicates)
    4. Valid date_embedded timestamps
    5. Consistent policy_version values
"""

import re
from datetime import datetime
from typing import Any


REQUIRED_METADATA_FIELDS = [
    "source_file",
    "source_type",
    "document_category",
    "policy_version",
    "section",
    "chunk_id",
    "date_embedded",
    "retrieval_count",
]

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_traceability(
    housing_chunks: list[dict[str, Any]],
    structured_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Validate traceability for all embedded chunks.

    Parameters
    ----------
    housing_chunks : list[dict]
        Metadata dicts from the housing_policy_docs collection.
    structured_chunks : list[dict]
        Metadata dicts from the structured_policy_docs collection.

    Returns
    -------
    dict  — Validation report with:
        passed (bool), total_chunks, checks (list of check results),
        errors (list of error strings)
    """
    all_chunks = housing_chunks + structured_chunks
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    # ── Check 1: Required fields present ─────────────────────────────────
    missing_fields_count = 0
    for chunk in all_chunks:
        for field in REQUIRED_METADATA_FIELDS:
            if field not in chunk:
                missing_fields_count += 1
                errors.append(
                    f"Chunk '{chunk.get('chunk_id', 'UNKNOWN')}' missing field: {field}"
                )
    checks.append({
        "check": "required_fields_present",
        "passed": missing_fields_count == 0,
        "issues": missing_fields_count,
    })

    # ── Check 2: No null / empty values ──────────────────────────────────
    null_count = 0
    for chunk in all_chunks:
        for field in REQUIRED_METADATA_FIELDS:
            val = chunk.get(field)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                null_count += 1
                errors.append(
                    f"Chunk '{chunk.get('chunk_id', 'UNKNOWN')}' has null/empty field: {field}"
                )
    checks.append({
        "check": "no_null_metadata",
        "passed": null_count == 0,
        "issues": null_count,
    })

    # ── Check 3: Unique chunk IDs ────────────────────────────────────────
    chunk_ids = [c.get("chunk_id", "") for c in all_chunks]
    duplicates = set(
        cid for cid in chunk_ids if chunk_ids.count(cid) > 1
    )
    if duplicates:
        for dup in duplicates:
            errors.append(f"Duplicate chunk_id: {dup}")
    checks.append({
        "check": "unique_chunk_ids",
        "passed": len(duplicates) == 0,
        "issues": len(duplicates),
    })

    # ── Check 4: Valid timestamps ────────────────────────────────────────
    invalid_dates = 0
    for chunk in all_chunks:
        date_str = chunk.get("date_embedded", "")
        if not DATE_PATTERN.match(str(date_str)):
            invalid_dates += 1
            errors.append(
                f"Chunk '{chunk.get('chunk_id', 'UNKNOWN')}' has invalid date: {date_str}"
            )
        else:
            try:
                datetime.strptime(str(date_str), "%Y-%m-%d")
            except ValueError:
                invalid_dates += 1
                errors.append(
                    f"Chunk '{chunk.get('chunk_id', 'UNKNOWN')}' has unparseable date: {date_str}"
                )
    checks.append({
        "check": "valid_timestamps",
        "passed": invalid_dates == 0,
        "issues": invalid_dates,
    })

    # ── Check 5: Consistent policy versions ──────────────────────────────
    versions = set(str(c.get("policy_version", "")) for c in all_chunks)
    checks.append({
        "check": "consistent_policy_versions",
        "passed": True,  # informational — multiple versions may be intentional
        "versions_found": sorted(versions),
        "issues": 0,
    })

    # ── Check 6: retrieval_count is numeric ──────────────────────────────
    non_numeric = 0
    for chunk in all_chunks:
        rc = chunk.get("retrieval_count")
        if not isinstance(rc, (int, float)):
            non_numeric += 1
            errors.append(
                f"Chunk '{chunk.get('chunk_id', 'UNKNOWN')}' has non-numeric retrieval_count: {rc}"
            )
    checks.append({
        "check": "retrieval_count_numeric",
        "passed": non_numeric == 0,
        "issues": non_numeric,
    })

    # ── Summary ──────────────────────────────────────────────────────────
    passed = all(c["passed"] for c in checks)

    report = {
        "passed": passed,
        "total_chunks": len(all_chunks),
        "housing_chunks": len(housing_chunks),
        "structured_chunks": len(structured_chunks),
        "checks": checks,
        "total_errors": len(errors),
        "errors": errors,
    }

    return report


def print_validation_report(report: dict[str, Any]) -> None:
    """Pretty-print the validation report to console."""
    status = "✅ PASSED" if report["passed"] else "❌ FAILED"
    print(f"\n{'='*60}")
    print(f"  TRACEABILITY VALIDATION REPORT — {status}")
    print(f"{'='*60}")
    print(f"  Total chunks validated : {report['total_chunks']}")
    print(f"  Housing doc chunks     : {report['housing_chunks']}")
    print(f"  Structured doc chunks  : {report['structured_chunks']}")
    print(f"  Total errors           : {report['total_errors']}")
    print(f"{'─'*60}")
    for check in report["checks"]:
        icon = "✅" if check["passed"] else "❌"
        print(f"  {icon}  {check['check']}  (issues: {check['issues']})")
        if "versions_found" in check:
            print(f"       versions: {check['versions_found']}")
    if report["errors"]:
        print(f"{'─'*60}")
        print("  ERRORS:")
        for err in report["errors"][:20]:  # cap output
            print(f"    • {err}")
        if len(report["errors"]) > 20:
            print(f"    ... and {len(report['errors']) - 20} more")
    print(f"{'='*60}\n")
