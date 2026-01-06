from __future__ import annotations

from typing import Iterable, List

from src.llm.client import LLMClient, default_client
from src.storage.data_store import RawDocument, Summary, utc_now_iso
from src.summarize.basic import _sentence_split

SYSTEM_PROMPT = "你是一名产品研究与市场分析助手，需从网页内容中提炼简洁要点。"


def _truncate(text: str, limit: int = 1600) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _extract_bullets(text: str, limit: int) -> List[str]:
    bullets: List[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.startswith(('- ', '* ')):
            cleaned = cleaned[2:]
        if not cleaned:
            continue
        bullets.append(cleaned)
        if len(bullets) >= limit:
            break
    if bullets:
        return bullets
    return _sentence_split(text, limit=limit)


def summarize_documents_llm(
    documents: Iterable[RawDocument],
    *,
    client: LLMClient | None = None,
    model: str | None = None,
    max_points: int = 5,
    fallback_to_basic: bool = True,
) -> List[Summary]:
    """Summarize documents via LLM, optionally falling back to rule-based splitting."""

    llm = client or default_client
    summaries: List[Summary] = []
    for doc in documents:
        try:
            prompt = (
                "请用要点列出以下网页的核心信息，包括产品亮点、价格/体验、用户痛点或竞品。\n"
                "输出每行一个要点，避免冗长。\n"
                f"标题：{doc.title}\n"
                f"URL：{doc.url}\n"
                f"正文：{_truncate(doc.content)}"
            )
            response = llm.chat(prompt, system_prompt=SYSTEM_PROMPT, model=model, max_tokens=400)
            bullet_points = _extract_bullets(response, limit=max_points)
        except Exception:
            if not fallback_to_basic:
                continue
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
