from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from src.storage.data_store import NormalizedDocument, RawDocument, Summary


@dataclass
class ReportResult:
    title: str
    generated_at: str
    total_documents: int
    channels: list[str]
    languages: list[str]
    highlights: list[str]
    sources: list[str]
    markdown: str


def _format_sources(docs: Iterable[NormalizedDocument], limit: int = 10) -> list[str]:
    items: list[str] = []
    for doc in docs:
        label = doc.title or doc.url
        channel = doc.channel or "general"
        items.append(f"- [{label}]({doc.url}) _(channel: {channel})_")
        if len(items) >= limit:
            break
    return items


def _aggregate_highlights(summaries: Iterable[Summary], limit: int = 12) -> list[str]:
    highlights: list[str] = []
    for summary in summaries:
        for bullet in summary.bullet_points:
            highlights.append(f"- {bullet}")
            if len(highlights) >= limit:
                return highlights
    return highlights


def _fallback_highlights(docs: Iterable[NormalizedDocument], limit: int = 8) -> list[str]:
    bullets: list[str] = []
    for doc in docs:
        if doc.title:
            bullets.append(f"- {doc.title}")
        else:
            bullets.append(f"- {doc.url}")
        if len(bullets) >= limit:
            break
    return bullets


def build_report(
    documents: List[NormalizedDocument] | List[RawDocument],
    summaries: List[Summary],
    title: str = "Product Research Report",
    source_limit: int = 10,
) -> ReportResult:
    generated_at = datetime.utcnow().isoformat() + "Z"
    channel_counts = Counter([getattr(doc, "channel", None) or "general" for doc in documents])
    language_counts = Counter([getattr(doc, "language", None) or "unknown" for doc in documents])

    channel_lines = [f"- {name}: {count}" for name, count in sorted(channel_counts.items())]
    language_lines = [f"- {name}: {count}" for name, count in sorted(language_counts.items())]

    highlights = _aggregate_highlights(summaries)
    if not highlights:
        highlights = _fallback_highlights(documents)

    source_lines = _format_sources(documents, limit=source_limit)

    markdown_sections = [
        f"# {title}",
        "",
        f"_Generated at: {generated_at}_",
        "",
        "## Coverage",
        f"- Total documents: {len(documents)}",
        f"- Distinct channels: {len(channel_counts)}",
        f"- Distinct languages: {len(language_counts)}",
        "",
        "## Channel Breakdown",
        *(channel_lines or ["- (none)"]),
        "",
        "## Language Breakdown",
        *(language_lines or ["- (unknown)"]),
        "",
        "## Key Highlights",
        *(highlights or ["- No summaries available"]),
        "",
        "## Sources",
        *(source_lines or ["- No sources available"]),
        "",
    ]

    markdown = "\n".join(markdown_sections)
    return ReportResult(
        title=title,
        generated_at=generated_at,
        total_documents=len(documents),
        channels=list(channel_counts.keys()),
        languages=list(language_counts.keys()),
        highlights=highlights,
        sources=source_lines,
        markdown=markdown,
    )

