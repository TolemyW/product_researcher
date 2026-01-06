from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

from src.analysis.report import build_report
from src.collect.fetch_strategy import FetchStrategy, get_fetch_strategy
from src.collect.channel_fetchers import collect_with_routing
from src.collect.source_discovery import discover_sources
from src.pipeline.normalize import normalize_documents
from src.storage.data_store import DataStore, NormalizedDocument
from src.summarize.basic import summarize_documents


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def run_discover(keywords: List[str], product_type: str | None) -> List[str]:
    sources = discover_sources(keywords, product_type=product_type)
    _print_json({"keywords": keywords, "product_type": product_type, "sources": sources})
    return sources


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


def run_summarize(store: DataStore) -> None:
    docs = store.load_normalized_documents() or store.load_raw_documents()
    summaries = summarize_documents(docs)
    added = store.add_summaries(summaries)
    _print_json({
        "summarized": len(summaries),
        "added": added,
        "source": "normalized" if store.load_normalized_documents() else "raw",
        "file": str(store.data_dir / 'summary.jsonl'),
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
) -> None:
    discovered: List[str] = []
    if keywords:
        discovered = run_discover(keywords, product_type)
    combined_urls = list(dict.fromkeys((urls or []) + discovered))
    if not combined_urls:
        _print_json({"error": "No URLs provided or discovered."})
        return
    run_fetch(combined_urls, store, strategy, product_type=product_type, concurrency=concurrency)
    run_normalize(store)
    run_summarize(store)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Product researcher MVP pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="Discover sources from keywords")
    discover_parser.add_argument("keywords", nargs="+", help="Keywords to search")
    discover_parser.add_argument("--product-type", dest="product_type", help="Product type (e.g., consumer, software, b2b)")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch URLs and store raw documents")
    fetch_parser.add_argument("urls", nargs="+", help="URLs to fetch")
    fetch_parser.add_argument("--product-type", dest="product_type", help="Product type for strategy tuning")
    fetch_parser.add_argument("--user-agent", dest="user_agent", help="Custom User-Agent header")
    fetch_parser.add_argument("--timeout", type=float, help="Request timeout in seconds")
    fetch_parser.add_argument("--max-retries", type=int, help="Maximum retry attempts")
    fetch_parser.add_argument("--delay", type=float, help="Delay between retries in seconds")
    fetch_parser.add_argument("--concurrency", type=int, default=1, help="Parallel fetch worker count")

    normalize_parser = subparsers.add_parser("normalize", help="Normalize stored raw documents")
    normalize_parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Data directory")

    summarize_parser = subparsers.add_parser("summarize", help="Summarize stored documents")
    summarize_parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Data directory")

    report_parser = subparsers.add_parser("report", help="Generate a Markdown report from collected data")
    report_parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Data directory")
    report_parser.add_argument("--output", type=Path, default=Path("data/report.md"), help="Report output path")
    report_parser.add_argument("--title", type=str, default="Product Research Report", help="Report title")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run discovery, fetch, and summarize")
    pipeline_parser.add_argument("--keywords", nargs="*", help="Keywords for discovery")
    pipeline_parser.add_argument("--urls", nargs="*", help="Seed URLs to fetch")
    pipeline_parser.add_argument("--product-type", dest="product_type", help="Product type (e.g., consumer, software, b2b)")
    pipeline_parser.add_argument("--user-agent", dest="user_agent", help="Custom User-Agent header")
    pipeline_parser.add_argument("--timeout", type=float, help="Request timeout in seconds")
    pipeline_parser.add_argument("--max-retries", type=int, help="Maximum retry attempts")
    pipeline_parser.add_argument("--delay", type=float, help="Delay between retries in seconds")
    pipeline_parser.add_argument("--concurrency", type=int, default=1, help="Parallel fetch worker count")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    data_dir = getattr(args, "data_dir", Path("data"))
    store = DataStore(data_dir=data_dir)
    strategy = None
    if hasattr(args, "product_type"):
        strategy = build_fetch_strategy(
            getattr(args, "product_type", None),
            getattr(args, "user_agent", None),
            getattr(args, "timeout", None),
            getattr(args, "max_retries", None),
            getattr(args, "delay", None),
        )

    if args.command == "discover":
        run_discover(args.keywords, args.product_type)
    elif args.command == "fetch":
        fetch_strategy = strategy or FetchStrategy()
        run_fetch(
            args.urls,
            store,
            fetch_strategy,
            product_type=args.product_type,
            concurrency=args.concurrency,
        )
    elif args.command == "normalize":
        run_normalize(store)
    elif args.command == "summarize":
        run_summarize(store)
    elif args.command == "report":
        run_report(store, args.title, args.output)
    elif args.command == "pipeline":
        fetch_strategy = strategy or FetchStrategy()
        run_pipeline(
            args.keywords,
            args.urls,
            args.product_type,
            fetch_strategy,
            store,
            concurrency=args.concurrency,
        )


if __name__ == "__main__":
    main()
