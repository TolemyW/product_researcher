import unittest
from pathlib import Path

from src.analysis.report import ReportResult, build_report
from src.storage.data_store import NormalizedDocument, RawDocument, Summary


def _sample_docs() -> list[NormalizedDocument]:
    return [
        NormalizedDocument(
            url="https://example.com/a",
            title="Example A",
            content="A content",
            fetched_at="2025-02-10T00:00:00Z",
            channel="docs",
            language="en",
            normalized_at="2025-02-10T00:00:00Z",
        ),
        NormalizedDocument(
            url="https://example.com/b",
            title="Example B",
            content="B content",
            fetched_at="2025-02-10T00:00:00Z",
            channel="github",
            language="en",
            normalized_at="2025-02-10T00:00:00Z",
        ),
    ]


def _sample_summaries() -> list[Summary]:
    return [
        Summary(url="https://example.com/a", bullet_points=["Point A", "Point B"], summarized_at="now"),
        Summary(url="https://example.com/b", bullet_points=["Point C"], summarized_at="now"),
    ]


class ReportBuilderTests(unittest.TestCase):
    def test_build_report_generates_markdown_sections(self) -> None:
        docs = _sample_docs()
        summaries = _sample_summaries()

        report: ReportResult = build_report(docs, summaries, title="Sample Report", source_limit=5)

        self.assertEqual(report.title, "Sample Report")
        self.assertEqual(report.total_documents, 2)
        self.assertSetEqual(set(report.channels), {"docs", "github"})
        self.assertTrue(any("Channel Breakdown" in line for line in report.markdown.splitlines()))
        self.assertTrue(any("Key Highlights" in line for line in report.markdown.splitlines()))
        self.assertTrue(report.sources)
        self.assertTrue(report.highlights)

        output_path = Path("/tmp/report.md")
        output_path.write_text(report.markdown, encoding="utf-8")
        self.assertTrue(output_path.exists())

    def test_build_report_falls_back_to_raw_documents_when_needed(self) -> None:
        raw_docs = [
            RawDocument(url="https://example.com/raw", title="Raw Title", content="Raw", fetched_at="2025-02-10Z"),
        ]

        report = build_report(raw_docs, summaries=[], title="Raw Report")

        self.assertEqual(report.total_documents, 1)
        self.assertIn("Raw Title", report.markdown)


if __name__ == "__main__":
    unittest.main()
