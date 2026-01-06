import json
from pathlib import Path

from src.analysis.report import build_report
from src.storage.data_store import NormalizedDocument, Summary


def load_normalized_documents(path: Path) -> list[NormalizedDocument]:
    with path.open(encoding="utf-8") as f:
        return [NormalizedDocument(**json.loads(line)) for line in f if line.strip()]


def load_summaries(path: Path) -> list[Summary]:
    with path.open(encoding="utf-8") as f:
        return [Summary(**json.loads(line)) for line in f if line.strip()]


def test_report_matches_chinese_snapshot() -> None:
    base = Path("tests/data")
    docs = load_normalized_documents(base / "sample_normalized.jsonl")
    summaries = load_summaries(base / "sample_summaries.jsonl")

    report = build_report(
        docs,
        summaries,
        title="示例产品研究报告",
        source_limit=5,
        generated_at="2025-02-12T12:00:00Z",
    )

    snapshot = Path("tests/snapshots/report_cn.md").read_text(encoding="utf-8").strip()
    assert report.markdown.strip() == snapshot
