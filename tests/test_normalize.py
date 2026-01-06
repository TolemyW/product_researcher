import unittest

from src.pipeline.normalize import detect_language, normalize_documents
from src.storage.data_store import RawDocument


class NormalizeTests(unittest.TestCase):
    def test_detect_language_simple(self) -> None:
        self.assertEqual(detect_language("这是一段中文"), "zh")
        self.assertEqual(detect_language("Simple english sentence."), "en")

    def test_normalize_documents_compacts_and_deduplicates(self) -> None:
        raw = RawDocument(
            url="http://example.com",
            title=" Example   Title  ",
            content="Line1\nLine1\nLine2  with   spaces",
            fetched_at="2025-02-01T00:00:00Z",
        )
        normalized = normalize_documents([raw])
        self.assertEqual(len(normalized), 1)
        doc = normalized[0]
        self.assertEqual(doc.title, "Example Title")
        self.assertEqual(doc.language, "en")
        self.assertIn("Line1", doc.content)
        # deduplicated -> only one Line1
        self.assertEqual(doc.content.count("Line1"), 1)


if __name__ == "__main__":
    unittest.main()
