import unittest

from src.analysis.insights import build_comparison_rows, extract_insights
from src.storage.data_store import NormalizedDocument, Summary


def _docs() -> list[NormalizedDocument]:
    return [
        NormalizedDocument(
            url="https://example.com/a",
            title="A 优势案例",
            content="fast and stable",
            fetched_at="2025-02-10T00:00:00Z",
            channel="docs",
            language="en",
            normalized_at="2025-02-10T00:00:00Z",
        ),
        NormalizedDocument(
            url="https://example.com/b",
            title="B 缺点提示",
            content="some risk here",
            fetched_at="2025-02-10T00:00:00Z",
            channel="github",
            language="en",
            normalized_at="2025-02-10T00:00:00Z",
        ),
    ]


def _summaries() -> list[Summary]:
    return [
        Summary(url="https://example.com/a", bullet_points=["优势：fast response"], summarized_at="now"),
        Summary(url="https://example.com/b", bullet_points=["存在风险 slow"], summarized_at="now"),
    ]


class InsightTests(unittest.TestCase):
    def test_extracts_strengths_and_weaknesses(self) -> None:
        insights = extract_insights(_summaries(), _docs())

        self.assertTrue(any(item.category == "strength" for item in insights["strength"]))
        self.assertTrue(any(item.category == "weakness" for item in insights["weakness"]))

    def test_builds_comparison_rows(self) -> None:
        rows = build_comparison_rows(_docs(), _summaries())

        self.assertEqual(len(rows), 2)
        self.assertTrue(any("渠道: docs" in row for row in rows))
        self.assertTrue(any("语言: en" in row for row in rows))


if __name__ == "__main__":
    unittest.main()
