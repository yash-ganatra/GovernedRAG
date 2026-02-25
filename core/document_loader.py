"""
Document Loader — Extracts documents with governance metadata.

Loads .md files from data/ai_governance_docs/ and .yaml from data/structured_policy/.
Each document is enriched with provenance metadata for traceability.
"""

import os
import re
import yaml
from datetime import datetime, timezone
from typing import Any, Optional


# ── Metadata map: filename → known provenance ───────────────────────────
DOCUMENT_METADATA_MAP: dict[str, dict[str, str]] = {
    "eu_ai_act.md": {
        "source_name": "European Parliament and Council of the EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
        "document_category": "eu_regulation",
    },
    "gdpr.md": {
        "source_name": "European Parliament and Council of the EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",
        "document_category": "eu_regulation",
    },
    "nist_ai_rmf.md": {
        "source_name": "National Institute of Standards and Technology",
        "url": "https://airc.nist.gov/RMF",
        "document_category": "us_framework",
    },
    "iso_iec_42001.md": {
        "source_name": "International Organization for Standardization",
        "url": "https://www.iso.org/standard/81230.html",
        "document_category": "international_standard",
    },
}


def _extract_url_from_frontmatter(text: str) -> Optional[str]:
    """Try to pull a URL from the markdown blockquote header."""
    match = re.search(r"\*\*URL:\*\*\s*(https?://\S+)", text)
    return match.group(1) if match else None


def _extract_sections(text: str) -> list[dict[str, str]]:
    """Split a markdown document into sections keyed by heading."""
    sections: list[dict[str, str]] = []
    # Split on ## headings (level 2+)
    parts = re.split(r"(?=^#{2,}\s)", text, flags=re.MULTILINE)

    for part in parts:
        heading_match = re.match(r"^(#{2,})\s+(.+)", part)
        heading = heading_match.group(2).strip() if heading_match else "Preamble"
        body = part[heading_match.end():].strip() if heading_match else part.strip()
        if body:
            sections.append({"heading": heading, "content": body})

    return sections


def load_markdown_documents(docs_dir: str) -> list[dict[str, Any]]:
    """
    Load all .md files from *docs_dir* and return a list of document dicts.

    Each dict contains:
        file_name, source_name, url, date_embedded,
        document_version, document_category, sections, raw_text
    """
    documents: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".md"):
            continue

        fpath = os.path.join(docs_dir, fname)
        with open(fpath, "r", encoding="utf-8") as fh:
            raw = fh.read()

        known = DOCUMENT_METADATA_MAP.get(fname, {})
        url = known.get("url") or _extract_url_from_frontmatter(raw) or ""

        doc = {
            "file_name": fname,
            "source_name": known.get("source_name", "unknown"),
            "url": url,
            "date_embedded": now,
            "document_version": "v1",
            "document_category": known.get("document_category", "unknown"),
            "sections": _extract_sections(raw),
            "raw_text": raw,
        }
        documents.append(doc)

    return documents


def load_yaml_policy(yaml_path: str) -> dict[str, Any]:
    """
    Load the structured policy YAML and return a document dict
    with category = 'structured_policy'.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with open(yaml_path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    data = yaml.safe_load(raw)

    return {
        "file_name": os.path.basename(yaml_path),
        "source_name": "ISO / EU / NIST",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
        "date_embedded": now,
        "document_version": "v1",
        "document_category": "structured_policy",
        "policy_version": "v1",
        "parsed_data": data,
        "raw_text": raw,
    }
