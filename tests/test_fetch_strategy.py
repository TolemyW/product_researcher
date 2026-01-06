import unittest
from unittest import mock

from src.cli import build_fetch_strategy
from src.collect.fetch_strategy import FetchStrategy, get_fetch_strategy
from src.collect.web_scraper import fetch_documents
from src.storage.data_store import RawDocument


class FetchStrategyTests(unittest.TestCase):
    def test_get_fetch_strategy_per_product_type(self) -> None:
        consumer = get_fetch_strategy("consumer")
        software = get_fetch_strategy("software")
        b2b = get_fetch_strategy("b2b")

        self.assertLess(consumer.timeout, software.timeout)
        self.assertGreater(b2b.max_retries, consumer.max_retries)
        self.assertGreaterEqual(b2b.per_request_delay, 1.0)

    def test_build_fetch_strategy_overrides_defaults(self) -> None:
        strategy = build_fetch_strategy("b2b", user_agent="custom", timeout=5.0, max_retries=4, delay=0.2)
        self.assertEqual(strategy.user_agent, "custom")
        self.assertEqual(strategy.timeout, 5.0)
        self.assertEqual(strategy.max_retries, 4)
        self.assertEqual(strategy.per_request_delay, 0.2)

    def test_fetch_documents_retries_and_collects(self) -> None:
        strategy = FetchStrategy(max_retries=1, per_request_delay=0)
        calls = {"count": 0}

        def fake_fetch(url, _strategy):  # noqa: ARG001
            calls["count"] += 1
            if calls["count"] == 1:
                raise ValueError("temporary failure")
            return "<title>ok</title><p>content</p>"

        with mock.patch("src.collect.web_scraper._fetch_html", side_effect=fake_fetch):
            documents = fetch_documents(["http://example.com"], strategy=strategy)

        self.assertEqual(calls["count"], 2)  # retried once
        self.assertEqual(len(documents), 1)
        self.assertIsInstance(documents[0], RawDocument)


if __name__ == "__main__":
    unittest.main()
