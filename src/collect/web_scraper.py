from __future__ import annotations

import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from typing import Iterable, List, Optional

from src.collect.fetch_strategy import FetchStrategy
from src.storage.data_store import RawDocument, utc_now_iso


def _fetch_html(url: str, strategy: FetchStrategy) -> str:
    request = urllib.request.Request(url, headers=strategy.as_headers())
    with urllib.request.urlopen(request, timeout=strategy.timeout) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def _strip_tags(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return unescape(text).strip()


def _extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return unescape(match.group(1)).strip()
    return ""


def _fetch_single(url: str, strategy: FetchStrategy) -> Optional[RawDocument]:
    try:
        html = None
        for attempt in range(strategy.max_retries + 1):
            try:
                html = _fetch_html(url, strategy)
                break
            except Exception:
                if attempt >= strategy.max_retries:
                    raise
                time.sleep(strategy.per_request_delay)

        if html is None:
            return None
        title = _extract_title(html) or url
        content = _strip_tags(html)
        return RawDocument(
            url=url,
            title=title,
            content=content,
            fetched_at=utc_now_iso(),
        )
    except Exception:  # pragma: no cover - network failures are handled silently
        return None


def fetch_documents(
    urls: Iterable[str],
    strategy: FetchStrategy | None = None,
    concurrency: int = 1,
) -> List[RawDocument]:
    strategy = strategy or FetchStrategy()
    normalized_concurrency = max(1, concurrency)

    if normalized_concurrency == 1:
        documents = [_fetch_single(url, strategy) for url in urls]
    else:
        with ThreadPoolExecutor(max_workers=normalized_concurrency) as executor:
            documents = list(executor.map(lambda u: _fetch_single(u, strategy), urls))

    return [doc for doc in documents if doc]
