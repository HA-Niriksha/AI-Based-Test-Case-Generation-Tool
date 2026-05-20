import re
from typing import List
from models import DocumentChunk
from constants import MODULE_KEYWORDS, FUNCTIONAL_VERBS, NON_FUNCTIONAL_KEYWORDS


def detect_module(text: str) -> str:
    lower = text.lower()
    for module in MODULE_KEYWORDS:
        if module.lower() in lower:
            return module
    return "General"


def classify_requirement(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in NON_FUNCTIONAL_KEYWORDS):
        return "non-functional"
    if any(k in lower for k in FUNCTIONAL_VERBS):
        return "functional"
    return "functional"


def extract_req_ids(text: str) -> List[str]:
    patterns = [
        r'\bREQ[-_]?\d+(?:\.\d+)*\b',
        r'\bFR[-_]?\d+(?:\.\d+)*\b',
        r'\bNFR[-_]?\d+(?:\.\d+)*\b',
        r'\bUC[-_]?\d+(?:\.\d+)*\b',
        r'\bBR[-_]?\d+(?:\.\d+)*\b',
        r'\bSR[-_]?\d+(?:\.\d+)*\b',
    ]
    ids = []
    for pat in patterns:
        found = re.findall(pat, text, re.IGNORECASE)
        ids.extend(found)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for _id in ids:
        upper = _id.upper()
        if upper not in seen:
            seen.add(upper)
            unique.append(upper)
    return unique


def split_into_sentences(text: str) -> List[str]:
    # Split on sentence boundaries; keep headings
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    cleaned = []
    for s in sentences:
        s = s.strip()
        if s and len(s.split()) >= 5:
            cleaned.append(s)
    return cleaned


def chunk_text(text: str, max_words: int = 1500) -> List[str]:
    sentences = split_into_sentences(text)
    chunks, current, current_words = [], [], 0
    for sent in sentences:
        words = len(sent.split())
        if current_words + words > max_words and current:
            chunks.append(" ".join(current))
            current, current_words = [sent], words
        else:
            current.append(sent)
            current_words += words
    if current:
        chunks.append(" ".join(current))
    return chunks if chunks else [text]


def ingest_document(text: str, chunk_size_words: int = 1500) -> List[DocumentChunk]:
    if not text or not text.strip():
        return []

    raw_chunks = chunk_text(text, chunk_size_words)
    result = []
    auto_id_counter = 1

    for i, chunk in enumerate(raw_chunks):
        if not chunk.strip():
            continue
        req_ids = extract_req_ids(chunk)
        if not req_ids:
            req_ids = [f"REQ-{auto_id_counter:03d}"]
            auto_id_counter += 1

        result.append(DocumentChunk(
            chunk_index=i,
            module=detect_module(chunk),
            requirement_type=classify_requirement(chunk),
            requirement_ids=req_ids,
            content=chunk,
        ))

    return result
