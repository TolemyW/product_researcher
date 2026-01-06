from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from src.storage.data_store import NormalizedDocument, RawDocument, Summary


POSITIVE_KEYWORDS = {
    "advantage",
    "benefit",
    "fast",
    "improve",
    "robust",
    "strength",
    "优势",
    "优点",
    "亮点",
    "稳定",
    "提升",
}

NEGATIVE_KEYWORDS = {
    "risk",
    "concern",
    "slow",
    "缺点",
    "不足",
    "劣势",
    "风险",
    "延迟",
    "瓶颈",
}


@dataclass
class Insight:
    category: str
    text: str
    source: str


def _classify_text(text: str) -> str | None:
    lower_text = text.lower()
    if any(keyword in lower_text for keyword in POSITIVE_KEYWORDS):
        return "strength"
    if any(keyword in lower_text for keyword in NEGATIVE_KEYWORDS):
        return "weakness"
    return None


def extract_insights(
    summaries: Iterable[Summary],
    documents: Iterable[NormalizedDocument] | Iterable[RawDocument],
    limit_per_category: int = 5,
) -> dict[str, List[Insight]]:
    insights: dict[str, list[Insight]] = {"strength": [], "weakness": []}
    title_by_url = {getattr(doc, "url", ""): getattr(doc, "title", "") or getattr(doc, "url", "") for doc in documents}

    for summary in summaries:
        source_title = title_by_url.get(summary.url, summary.url)
        for bullet in summary.bullet_points:
            category = _classify_text(bullet)
            if not category:
                continue
            if len(insights[category]) >= limit_per_category:
                continue
            insights[category].append(Insight(category=category, text=bullet, source=source_title))

    for category in ("strength", "weakness"):
        if insights[category]:
            continue
        # Provide a neutral fallback using document titles to avoid empty sections
        for url, title in title_by_url.items():
            if len(insights[category]) >= max(1, limit_per_category // 2):
                break
            insights[category].append(
                Insight(category=category, text=title or url, source=title or url)
            )

    return insights


def build_comparison_rows(
    documents: Sequence[NormalizedDocument] | Sequence[RawDocument],
    summaries: Sequence[Summary],
    limit: int = 5,
) -> List[str]:
    rows: list[str] = []
    summary_by_url = {summary.url: summary for summary in summaries}

    for doc in documents[:limit]:
        first_point = "".join(summary_by_url.get(doc.url, Summary(doc.url, [], "")).bullet_points[:1])
        label_parts = [doc.title or doc.url]
        channel = getattr(doc, "channel", None)
        if channel:
            label_parts.append(f"渠道: {channel}")
        language = getattr(doc, "language", None)
        if language:
            label_parts.append(f"语言: {language}")
        descriptor = " | ".join(label_parts)
        if first_point:
            rows.append(f"- {descriptor} —— 关键信息: {first_point}")
        else:
            rows.append(f"- {descriptor}")

    return rows
