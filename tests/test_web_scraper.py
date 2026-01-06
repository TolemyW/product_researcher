import unittest
from unittest import mock

from src.collect.web_scraper import fetch_documents


class WebScraperTests(unittest.TestCase):
    def test_fetch_documents_supports_concurrency(self) -> None:
        html = "<html><title>Example</title><body>content</body></html>"
        urls = ["https://example.com/a", "https://example.com/b"]

        with mock.patch("src.collect.web_scraper._fetch_html", return_value=html) as mock_fetch:
            docs = fetch_documents(urls, concurrency=2)

        self.assertEqual(len(docs), 2)
        self.assertTrue(all(doc.title == "Example" for doc in docs))
        self.assertEqual(mock_fetch.call_count, 2)


if __name__ == "__main__":
    unittest.main()
