from __future__ import annotations

import re
from typing import Iterable, List

from src.storage.data_store import NormalizedDocument, RawDocument, utc_now_iso


def detect_language(text: str) -> str:
    """A minimal language detector to separate zh/en content."""

    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    return "en"


def _compact_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _deduplicate_lines(text: str) -> str:
    lines = [_compact_spaces(line) for line in text.splitlines() if _compact_spaces(line)]
    seen = set()
    unique_lines: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        unique_lines.append(line)
    return " \n ".join(unique_lines)


def normalize_documents(documents: Iterable[RawDocument]) -> List[NormalizedDocument]:
    normalized: list[NormalizedDocument] = []
    for doc in documents:
        cleaned_content = _deduplicate_lines(doc.content)
        if not cleaned_content:
            continue
        language = detect_language(cleaned_content)
        normalized.append(
            NormalizedDocument(
                url=doc.url,
                title=_compact_spaces(doc.title) or doc.url,
                content=cleaned_content,
                fetched_at=doc.fetched_at,
                channel=getattr(doc, "channel", None),
                language=language,
                source="normalized",
                normalized_at=utc_now_iso(),
            )
        )
    return normalized


def normalize_and_deduplicate(documents: Iterable[RawDocument]) -> List[NormalizedDocument]:
    return normalize_documents(documents)
