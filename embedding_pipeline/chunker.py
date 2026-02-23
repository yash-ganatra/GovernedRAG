"""
Chunking Module — Section-aware, overlapping text chunker.

Strategy:
    • Chunk size  : 400–600 tokens (measured via tiktoken cl100k_base)
    • Overlap     : 50–100 tokens
    • Each chunk retains: section heading, source file, chunk_id
"""

import re
import tiktoken
from typing import Any

# ── Tokeniser (same family as OpenAI / many ST models) ──────────────────
_ENC = tiktoken.get_encoding("cl100k_base")

CHUNK_TARGET_TOKENS = 500     # target middle of 400-600 range
CHUNK_MAX_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 75     # middle of 50-100 range


def _count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


def _split_text_into_chunks(
    text: str,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """
    Split *text* into token-bounded chunks with overlap.
    Splits on paragraph boundaries first, then sentences.
    """
    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        ptokens = _count_tokens(para)

        # If a single paragraph exceeds max, split it by sentences
        if ptokens > max_tokens:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                stokens = _count_tokens(sent)
                if current_tokens + stokens > max_tokens and current:
                    chunks.append("\n\n".join(current))
                    # Keep overlap from end of current
                    overlap_text = _get_overlap(current, overlap_tokens)
                    current = [overlap_text] if overlap_text else []
                    current_tokens = _count_tokens(overlap_text) if overlap_text else 0
                current.append(sent)
                current_tokens += stokens
        else:
            if current_tokens + ptokens > max_tokens and current:
                chunks.append("\n\n".join(current))
                overlap_text = _get_overlap(current, overlap_tokens)
                current = [overlap_text] if overlap_text else []
                current_tokens = _count_tokens(overlap_text) if overlap_text else 0
            current.append(para)
            current_tokens += ptokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _get_overlap(parts: list[str], overlap_tokens: int) -> str:
    """Return the tail of *parts* that fits within *overlap_tokens*."""
    result: list[str] = []
    total = 0
    for p in reversed(parts):
        t = _count_tokens(p)
        if total + t > overlap_tokens:
            break
        result.insert(0, p)
        total += t
    return "\n\n".join(result)


def chunk_document(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Chunk a loaded document dict into metadata-rich chunks.

    Returns list of dicts, each with:
        text, source_file, source_type, document_category,
        policy_version, section, chunk_id, date_embedded,
        retrieval_count
    """
    file_stem = doc["file_name"].replace(".md", "").replace(".yaml", "")
    chunks: list[dict[str, Any]] = []
    idx = 0

    sections = doc.get("sections", [])

    if not sections:
        # YAML or headerless doc — chunk the raw text
        sections = [{"heading": "Full Document", "content": doc["raw_text"]}]

    for section in sections:
        heading = section["heading"]
        text_chunks = _split_text_into_chunks(section["content"])

        for text in text_chunks:
            idx += 1
            chunk_id = f"{file_stem}_{idx:03d}"
            chunks.append({
                "text": text,
                "source_file": doc["file_name"],
                "source_type": doc["source_name"],
                "document_category": doc["document_category"],
                "policy_version": doc.get("policy_version", doc.get("document_version", "v1")),
                "section": heading,
                "chunk_id": chunk_id,
                "date_embedded": doc["date_embedded"],
                "retrieval_count": 0,
                "url": doc.get("url", ""),
            })

    return chunks


def chunk_yaml_document(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Chunk a YAML policy document into section-level chunks.
    Each top-level YAML key becomes a section chunk.
    """
    import yaml as _yaml

    file_stem = doc["file_name"].replace(".yaml", "")
    chunks: list[dict[str, Any]] = []
    parsed = doc.get("parsed_data", {})
    idx = 0

    for key, value in parsed.items():
        section_text = f"# {key}\n\n{_yaml.dump({key: value}, default_flow_style=False, allow_unicode=True)}"
        text_chunks = _split_text_into_chunks(section_text)

        for text in text_chunks:
            idx += 1
            chunk_id = f"{file_stem}_{idx:03d}"
            chunks.append({
                "text": text,
                "source_file": doc["file_name"],
                "source_type": doc["source_name"],
                "document_category": "structured_policy",
                "policy_version": doc.get("policy_version", "v1"),
                "section": key,
                "chunk_id": chunk_id,
                "date_embedded": doc["date_embedded"],
                "retrieval_count": 0,
                "url": doc.get("url", ""),
            })

    return chunks
