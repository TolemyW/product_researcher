from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Iterable, List, Sequence

from src.collect.channels import DiscoveryChannel, get_channels_for_product_type

USER_AGENT = "product-researcher/0.1"
SEARCH_ENGINE = "https://duckduckgo.com/html/?q={query}"


def _http_get(url: str, timeout: float = 10.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def _parse_links(html: str, limit: int = 10) -> List[str]:
    hrefs = re.findall(r'href="(http[^"#]+)"', html)
    filtered = []
    for link in hrefs:
        if any(domain in link for domain in ["duckduckgo.com", "google.com/url", "yahoo.com"]):
            continue
        filtered.append(link)
        if len(filtered) >= limit:
            break
    return filtered


def discover_sources(
    keywords: Sequence[str],
    product_type: str | None = None,
    limit_per_keyword: int = 5,
    limit_per_channel: int = 3,
) -> List[str]:
    discovered: List[str] = []
    channels = get_channels_for_product_type(product_type)
    for keyword in keywords:
        for channel in channels:
            channel_query = channel.build_query(keyword)
            encoded_query = urllib.parse.quote(channel_query)
            url = SEARCH_ENGINE.format(query=encoded_query)
            try:
                html = _http_get(url)
                links = _parse_links(html, limit=min(limit_per_keyword, limit_per_channel))
                discovered.extend(links)
            except Exception:  # pragma: no cover - network failures are handled silently
                continue
    return list(dict.fromkeys(discovered))


def load_seed_list(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith(".json"):
            data = json.load(f)
            if isinstance(data, list):
                return [str(item) for item in data]
        return [line.strip() for line in f if line.strip()]
