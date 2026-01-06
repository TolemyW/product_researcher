from __future__ import annotations

from typing import Iterable, List

from src.llm.client import LLMClient, default_client


SYSTEM_PROMPT = "你是一名产品研究助理，请基于产品简介生成搜索用关键词，输出为每行一个短语。"


def _parse_keywords(text: str, limit: int) -> List[str]:
    keywords: List[str] = []
    for line in text.splitlines():
        cleaned = line.lstrip("-*• ").strip()
        if not cleaned:
            continue
        keywords.append(cleaned)
        if len(keywords) >= limit:
            break
    return keywords


def generate_keywords_from_brief(
    brief: str,
    *,
    client: LLMClient | None = None,
    model: str | None = None,
    max_keywords: int = 8,
    seed_keywords: Iterable[str] | None = None,
) -> List[str]:
    """Use an LLM to propose search keywords for discovery."""

    llm = client or default_client
    prompt = (
        "基于以下产品简介，生成用于搜索的关键词列表，突出产品名称、核心功能、竞品、场景。\n"
        "每行一个短语，控制在 3-6 个词。\n"
        f"产品简介：{brief}\n"
    )
    if seed_keywords:
        seed_text = "、".join(seed_keywords)
        prompt += f"可参考已有关键词：{seed_text}\n"

    response = llm.chat(prompt, system_prompt=SYSTEM_PROMPT, model=model, max_tokens=128)
    parsed = _parse_keywords(response, limit=max_keywords)
    deduped: List[str] = []
    for keyword in parsed:
        if keyword not in deduped:
            deduped.append(keyword)
    return deduped
