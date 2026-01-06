from __future__ import annotations

import argparse
from pathlib import Path

from src.pipeline.scheduler import build_runner
from src.pipeline.runtime import (
    _prepare_keywords,
    _print_json,
    build_fetch_strategy,
    run_discover,
    run_fetch,
    run_normalize,
    run_pipeline,
    run_report,
    run_summarize,
)
from src.storage.data_store import DataStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Product researcher MVP pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="Discover sources from keywords")
    discover_parser.add_argument("keywords", nargs="*", help="Keywords to search")
    discover_parser.add_argument("--keyword-brief", dest="keyword_brief", help="Optional brief to expand keywords via LLM")
    discover_parser.add_argument("--llm-model", dest="llm_model", help="LLM model name for keyword generation")
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
    summarize_parser.add_argument("--use-llm", action="store_true", help="Use LLM summarizer with fallback to basic")
    summarize_parser.add_argument("--llm-model", dest="llm_model", help="LLM model name for summarization")

    report_parser = subparsers.add_parser("report", help="Generate a Markdown report from collected data")
    report_parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Data directory")
    report_parser.add_argument("--output", type=Path, default=Path("data/report.md"), help="Report output path")
    report_parser.add_argument("--title", type=str, default="Product Research Report", help="Report title")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run discovery, fetch, and summarize")
    pipeline_parser.add_argument("--keywords", nargs="*", help="Keywords for discovery")
    pipeline_parser.add_argument("--keyword-brief", dest="keyword_brief", help="Optional brief to generate keywords via LLM")
    pipeline_parser.add_argument("--urls", nargs="*", help="Seed URLs to fetch")
    pipeline_parser.add_argument("--product-type", dest="product_type", help="Product type (e.g., consumer, software, b2b)")
    pipeline_parser.add_argument("--user-agent", dest="user_agent", help="Custom User-Agent header")
    pipeline_parser.add_argument("--timeout", type=float, help="Request timeout in seconds")
    pipeline_parser.add_argument("--max-retries", type=int, help="Maximum retry attempts")
    pipeline_parser.add_argument("--delay", type=float, help="Delay between retries in seconds")
    pipeline_parser.add_argument("--concurrency", type=int, default=1, help="Parallel fetch worker count")
    pipeline_parser.add_argument("--use-llm", action="store_true", help="Use LLM summarizer with fallback to basic")
    pipeline_parser.add_argument("--llm-model", dest="llm_model", help="LLM model name for keyword generation and summarization")

    schedule_parser = subparsers.add_parser("schedule", help="Run scheduled pipeline tasks from a config file")
    schedule_parser.add_argument("--config", type=Path, default=Path("config/schedule.json"), help="Path to schedule config JSON")
    schedule_parser.add_argument("--run-once", action="store_true", help="Run all tasks once and exit")
    schedule_parser.add_argument("--max-cycles", type=int, help="Maximum scheduling cycles before exit")
    schedule_parser.add_argument("--sleep-seconds", type=int, default=60, help="Sleep between scheduling cycles")
    schedule_parser.add_argument("--log-file", type=Path, help="Custom log file path")

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
        try:
            prepared_keywords = _prepare_keywords(args.keywords, getattr(args, "keyword_brief", None), getattr(args, "llm_model", None))
        except ValueError as exc:  # pragma: no cover - CLI guard
            _print_json({"error": str(exc)})
            return
        run_discover(prepared_keywords, args.product_type)
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
        run_summarize(store, use_llm=args.use_llm, llm_model=getattr(args, "llm_model", None))
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
            keyword_brief=getattr(args, "keyword_brief", None),
            llm_model=getattr(args, "llm_model", None),
            use_llm=args.use_llm,
        )
    elif args.command == "schedule":
        config_path = args.config
        if not config_path.exists():
            _print_json({"error": f"Config file not found: {config_path}"})
            return
        runner = build_runner(config_path, getattr(args, "log_file", None))
        if args.run_once:
            runner.run_once()
        else:
            runner.run(max_cycles=getattr(args, "max_cycles", None), sleep_seconds=getattr(args, "sleep_seconds", 60))


if __name__ == "__main__":
    main()
