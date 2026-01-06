from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from src.analysis.report import build_report
from src.collect.channel_fetchers import collect_with_routing
from src.collect.fetch_strategy import FetchStrategy, get_fetch_strategy
from src.collect.keyword_generator import generate_keywords_from_brief
from src.collect.source_discovery import discover_sources
from src.pipeline.normalize import normalize_documents
from src.storage.data_store import DataStore, NormalizedDocument
from src.summarize.basic import summarize_documents
from src.summarize.llm import summarize_documents_llm


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def run_discover(keywords: List[str], product_type: str | None) -> List[str]:
    sources = discover_sources(keywords, product_type=product_type)
    _print_json({"keywords": keywords, "product_type": product_type, "sources": sources})
    return sources


def _prepare_keywords(
    seed_keywords: List[str] | None,
    keyword_brief: str | None,
    llm_model: str | None,
) -> List[str]:
    keywords = list(seed_keywords or [])
    if keyword_brief:
        generated = generate_keywords_from_brief(keyword_brief, model=llm_model, seed_keywords=keywords)
        keywords.extend(generated)
    if not keywords:
        raise ValueError("No keywords provided for discovery")
    # de-duplicate while preserving order
    return list(dict.fromkeys(keywords))


def build_fetch_strategy(
    product_type: str | None,
    user_agent: str | None,
    timeout: float | None,
    max_retries: int | None,
    delay: float | None,
) -> FetchStrategy:
    base = get_fetch_strategy(product_type)
    if user_agent:
        base.user_agent = user_agent
    if timeout is not None:
        base.timeout = timeout
    if max_retries is not None:
        base.max_retries = max_retries
    if delay is not None:
        base.per_request_delay = delay
    return base


def run_fetch(
    urls: Iterable[str],
    store: DataStore,
    strategy: FetchStrategy,
    product_type: str | None = None,
    concurrency: int = 1,
) -> None:
    documents = collect_with_routing(
        urls,
        product_type=product_type,
        base_strategy=strategy,
        concurrency=concurrency,
    )
    added = store.add_raw_documents(documents)
    _print_json(
        {
            "fetched": len(documents),
            "added": added,
            "file": str(store.data_dir / "raw.jsonl"),
            "channels": sorted({doc.channel or "general" for doc in documents}),
            "concurrency": concurrency,
        }
    )


def run_normalize(store: DataStore) -> None:
    raw_docs = store.load_raw_documents()
    normalized = normalize_documents(raw_docs)
    added = store.add_normalized_documents(normalized)
    _print_json({"normalized": len(normalized), "added": added, "file": str(store.data_dir / 'normalized.jsonl')})


def run_summarize(store: DataStore, *, use_llm: bool = False, llm_model: str | None = None) -> None:
    docs = store.load_normalized_documents() or store.load_raw_documents()
    if use_llm:
        summaries = summarize_documents_llm(docs, model=llm_model, fallback_to_basic=True)
    else:
        summaries = summarize_documents(docs)
    added = store.add_summaries(summaries)
    _print_json({
        "summarized": len(summaries),
        "added": added,
        "source": "normalized" if store.load_normalized_documents() else "raw",
        "file": str(store.data_dir / 'summary.jsonl'),
        "summarizer": "llm" if use_llm else "basic",
    })


def _raw_to_normalized(raw_docs: List) -> List[NormalizedDocument]:
    normalized_docs: list[NormalizedDocument] = []
    for doc in raw_docs:
        normalized_docs.append(
            NormalizedDocument(
                url=getattr(doc, "url", ""),
                title=getattr(doc, "title", ""),
                content=getattr(doc, "content", ""),
                fetched_at=getattr(doc, "fetched_at", ""),
                channel=getattr(doc, "channel", None),
                language=getattr(doc, "language", None),
                source=getattr(doc, "source", None),
                normalized_at=getattr(doc, "normalized_at", ""),
            )
        )
    return normalized_docs


def run_report(store: DataStore, title: str, output: Path) -> None:
    normalized_docs = store.load_normalized_documents()
    raw_docs = store.load_raw_documents()
    docs_for_report = normalized_docs or _raw_to_normalized(raw_docs)
    summaries = store.load_summaries()

    if not docs_for_report:
        _print_json({"error": "No documents available to build a report."})
        return

    report = build_report(docs_for_report, summaries, title=title)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.markdown, encoding="utf-8")
    _print_json(
        {
            "report_file": str(output),
            "documents": len(docs_for_report),
            "summaries": len(summaries),
            "title": title,
        }
    )


def run_pipeline(
    keywords: List[str] | None,
    urls: List[str] | None,
    product_type: str | None,
    strategy: FetchStrategy,
    store: DataStore,
    concurrency: int = 1,
    keyword_brief: str | None = None,
    llm_model: str | None = None,
    use_llm: bool = False,
) -> None:
    discovered: List[str] = []
    if keywords or keyword_brief:
        prepared_keywords = _prepare_keywords(keywords, keyword_brief, llm_model)
        discovered = run_discover(prepared_keywords, product_type)
    combined_urls = list(dict.fromkeys((urls or []) + discovered))
    if not combined_urls:
        _print_json({"error": "No URLs provided or discovered."})
        return
    run_fetch(combined_urls, store, strategy, product_type=product_type, concurrency=concurrency)
    run_normalize(store)
    run_summarize(store, use_llm=use_llm, llm_model=llm_model)
