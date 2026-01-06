import unittest
from unittest import mock

from src.collect.channel_fetchers import (
    ChannelFetcher,
    collect_with_routing,
    get_fetchers_for_product_type,
    route_urls_by_channel,
)
from src.collect.fetch_strategy import FetchStrategy
from src.storage.data_store import RawDocument


class ChannelFetcherTests(unittest.TestCase):
    def test_route_urls_maps_to_specialized_fetchers(self) -> None:
        fetchers = get_fetchers_for_product_type("consumer")
        routing = route_urls_by_channel(
            [
                "https://item.jd.com/123.html",
                "https://www.bilibili.com/video/abc",
                "https://unknown.example.com/page",
            ],
            fetchers,
        )

        self.assertEqual(routing["ecommerce"], ["https://item.jd.com/123.html"])
        self.assertEqual(routing["reviews"], ["https://www.bilibili.com/video/abc"])
        self.assertEqual(routing["general"], ["https://unknown.example.com/page"])

    def test_collect_with_routing_attaches_channel_and_strategy_overrides(self) -> None:
        special_fetcher = ChannelFetcher(
            name="special",
            domains=("example.com",),
            default_strategy=FetchStrategy(timeout=99.0, max_retries=0),
        )

        base_strategy = FetchStrategy(timeout=1.0, max_retries=1)

        with mock.patch("src.collect.channel_fetchers.fetch_documents") as mock_fetch:
            mock_fetch.return_value = [
                RawDocument(url="https://example.com/page", title="t", content="c", fetched_at="now"),
            ]
            documents = collect_with_routing(
                ["https://example.com/page"],
                product_type=None,
                base_strategy=base_strategy,
                fetchers=[special_fetcher, ChannelFetcher(name="general", domains=(), is_default=True)],
                concurrency=4,
            )

        mock_fetch.assert_called_once()
        self.assertEqual(mock_fetch.call_args.kwargs["concurrency"], 4)
        called_strategy = mock_fetch.call_args.kwargs["strategy"]
        self.assertEqual(called_strategy.timeout, 99.0)
        self.assertEqual(documents[0].channel, "special")


if __name__ == "__main__":
    unittest.main()
