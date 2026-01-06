from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence
from urllib.parse import urlparse

from src.collect.fetch_strategy import FetchStrategy, get_fetch_strategy
from src.collect.web_scraper import fetch_documents
from src.storage.data_store import RawDocument


@dataclass
class ChannelFetcher:
    name: str
    domains: Sequence[str]
    default_strategy: FetchStrategy | None = None
    is_default: bool = False

    def matches(self, url: str) -> bool:
        if not self.domains:
            return False
        netloc = urlparse(url).netloc.lower()
        return any(domain in netloc for domain in self.domains)

    def choose_strategy(self, fallback: FetchStrategy) -> FetchStrategy:
        return self.default_strategy or fallback

    def fetch(
        self,
        urls: Iterable[str],
        fallback_strategy: FetchStrategy,
        concurrency: int = 1,
    ) -> List[RawDocument]:
        strategy = self.choose_strategy(fallback_strategy)
        documents = fetch_documents(urls, strategy=strategy, concurrency=concurrency)
        for doc in documents:
            doc.channel = self.name
        return documents


# Consumer hardware-oriented fetchers
ECOMMERCE_FETCHER = ChannelFetcher(
    name="ecommerce",
    domains=("jd.com", "taobao.com", "tmall.com", "amazon.com"),
    default_strategy=FetchStrategy(timeout=10.0, max_retries=2, per_request_delay=0.5),
)

REVIEW_FETCHER = ChannelFetcher(
    name="reviews",
    domains=("zhihu.com", "weibo.com", "youtube.com", "bilibili.com"),
    default_strategy=FetchStrategy(timeout=10.0, max_retries=1, per_request_delay=0.2),
)


# Software/SaaS oriented fetchers
DOCS_FETCHER = ChannelFetcher(
    name="docs",
    domains=("readthedocs.io", "docs", "manual", "developer"),
    default_strategy=FetchStrategy(timeout=12.0, max_retries=2, per_request_delay=0.3),
)

GITHUB_FETCHER = ChannelFetcher(
    name="github",
    domains=("github.com",),
    default_strategy=FetchStrategy(timeout=12.0, max_retries=1, per_request_delay=0.2),
)


# B2B oriented fetchers
ANALYST_FETCHER = ChannelFetcher(
    name="analyst_reports",
    domains=("gartner.com", "forrester.com", "g2.com", "crunchbase.com"),
    default_strategy=FetchStrategy(timeout=18.0, max_retries=3, per_request_delay=1.0),
)

CASE_STUDY_FETCHER = ChannelFetcher(
    name="case_studies",
    domains=("case-study", "customers", "success-story", "whitepaper"),
    default_strategy=FetchStrategy(timeout=15.0, max_retries=2, per_request_delay=0.8),
)


GENERIC_FETCHER = ChannelFetcher(name="general", domains=(), is_default=True)


def get_fetchers_for_product_type(product_type: str | None) -> List[ChannelFetcher]:
    normalized = (product_type or "").strip().lower()

    if normalized in {"consumer", "hardware", "gadget"}:
        return [ECOMMERCE_FETCHER, REVIEW_FETCHER, GENERIC_FETCHER]

    if normalized in {"software", "saas"}:
        return [DOCS_FETCHER, GITHUB_FETCHER, GENERIC_FETCHER]

    if normalized in {"b2b", "enterprise"}:
        return [ANALYST_FETCHER, CASE_STUDY_FETCHER, GENERIC_FETCHER]

    return [GENERIC_FETCHER]


def route_urls_by_channel(urls: Iterable[str], fetchers: Sequence[ChannelFetcher]) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {fetcher.name: [] for fetcher in fetchers}
    default_fetcher = next((f for f in fetchers if f.is_default), fetchers[-1])

    for url in urls:
        matched = False
        for fetcher in fetchers:
            if fetcher.matches(url):
                mapping[fetcher.name].append(url)
                matched = True
                break
        if not matched:
            mapping[default_fetcher.name].append(url)

    return mapping


def collect_with_routing(
    urls: Iterable[str],
    product_type: str | None,
    base_strategy: FetchStrategy | None = None,
    fetchers: Sequence[ChannelFetcher] | None = None,
    concurrency: int = 1,
) -> List[RawDocument]:
    """Dispatch URLs to channel fetchers and collect documents.

    The function keeps behavior offline-friendly: individual fetch failures are
    handled inside `fetch_documents`, and channel metadata is attached to
    returned documents to aid downstream normalization/analytics.
    """

    strategy = base_strategy or get_fetch_strategy(product_type)
    fetcher_list = list(fetchers or get_fetchers_for_product_type(product_type))
    routing = route_urls_by_channel(urls, fetcher_list)

    collected: list[RawDocument] = []
    for fetcher in fetcher_list:
        channel_urls = routing.get(fetcher.name, [])
        if not channel_urls:
            continue
        collected.extend(fetcher.fetch(channel_urls, strategy, concurrency=concurrency))

    return collected
