from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FetchStrategy:
    """Configuration for web scraping requests."""

    user_agent: str = "product-researcher/0.1"
    timeout: float = 10.0
    max_retries: int = 1
    per_request_delay: float = 0.0
    headers: Dict[str, str] = field(default_factory=dict)

    def as_headers(self) -> Dict[str, str]:
        merged = {"User-Agent": self.user_agent}
        merged.update(self.headers)
        return merged


def get_fetch_strategy(product_type: str | None = None) -> FetchStrategy:
    """Return a strategy tuned for the given product type."""

    if not product_type:
        return FetchStrategy()

    normalized = product_type.lower()
    if normalized in {"consumer", "hardware", "gadget"}:
        return FetchStrategy(timeout=8.0, max_retries=2, per_request_delay=0.5)
    if normalized in {"software", "saas"}:
        return FetchStrategy(timeout=12.0, max_retries=2, per_request_delay=0.3)
    if normalized in {"b2b", "enterprise"}:
        # B2B sites often throttle aggressively; be patient and polite.
        return FetchStrategy(timeout=15.0, max_retries=3, per_request_delay=1.0)

    return FetchStrategy()
