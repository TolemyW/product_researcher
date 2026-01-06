from __future__ import annotations

import re
from typing import Iterable, List

from src.storage.data_store import RawDocument, Summary, utc_now_iso


def _sentence_split(text: str, limit: int = 5) -> List[str]:
    sentences = re.split(r"(?<=[。.!?])\s+", text)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    return sentences[:limit]


def summarize_documents(documents: Iterable[RawDocument], max_points: int = 5) -> List[Summary]:
    summaries: List[Summary] = []
    for doc in documents:
        bullet_points = _sentence_split(doc.content, limit=max_points)
        if not bullet_points:
            continue
        summaries.append(
            Summary(
                url=doc.url,
                bullet_points=bullet_points,
                summarized_at=utc_now_iso(),
            )
        )
    return summaries
