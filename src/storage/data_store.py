from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


DEFAULT_DATA_DIR = Path("data")


@dataclass
class RawDocument:
    url: str
    title: str
    content: str
    fetched_at: str
    channel: str | None = None


@dataclass
class NormalizedDocument(RawDocument):
    language: str | None = None
    source: str | None = None
    normalized_at: str = ""


@dataclass
class Summary:
    url: str
    bullet_points: List[str]
    summarized_at: str


class DataStore:
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def raw_file(self) -> Path:
        return self.data_dir / "raw.jsonl"

    @property
    def summary_file(self) -> Path:
        return self.data_dir / "summary.jsonl"

    @property
    def normalized_file(self) -> Path:
        return self.data_dir / "normalized.jsonl"

    def _load_jsonl(self, path: Path) -> List[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def _append_jsonl(self, path: Path, rows: Iterable[dict]) -> None:
        with path.open("a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def load_raw_documents(self) -> List[RawDocument]:
        documents: list[RawDocument] = []
        for item in self._load_jsonl(self.raw_file):
            documents.append(
                RawDocument(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    fetched_at=item.get("fetched_at", ""),
                    channel=item.get("channel"),
                )
            )
        return documents

    def load_summaries(self) -> List[Summary]:
        return [Summary(**item) for item in self._load_jsonl(self.summary_file)]

    def load_normalized_documents(self) -> List[NormalizedDocument]:
        documents: list[NormalizedDocument] = []
        for item in self._load_jsonl(self.normalized_file):
            documents.append(
                NormalizedDocument(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    fetched_at=item.get("fetched_at", ""),
                    channel=item.get("channel"),
                    language=item.get("language"),
                    source=item.get("source"),
                    normalized_at=item.get("normalized_at", ""),
                )
            )
        return documents

    def _existing_urls(self, path: Path) -> set[str]:
        if not path.exists():
            return set()
        return {json.loads(line).get("url") for line in path.read_text().splitlines() if line.strip()}

    def add_raw_documents(self, docs: Iterable[RawDocument]) -> int:
        existing = self._existing_urls(self.raw_file)
        new_docs = [doc for doc in docs if doc.url not in existing]
        if not new_docs:
            return 0
        self._append_jsonl(self.raw_file, (asdict(doc) for doc in new_docs))
        return len(new_docs)

    def add_normalized_documents(self, docs: Iterable[NormalizedDocument]) -> int:
        existing = self._existing_urls(self.normalized_file)
        new_docs = [doc for doc in docs if doc.url not in existing]
        if not new_docs:
            return 0
        self._append_jsonl(self.normalized_file, (asdict(doc) for doc in new_docs))
        return len(new_docs)

    def add_summaries(self, summaries: Iterable[Summary]) -> int:
        existing = self._existing_urls(self.summary_file)
        new_summaries = [summary for summary in summaries if summary.url not in existing]
        if not new_summaries:
            return 0
        self._append_jsonl(self.summary_file, (asdict(summary) for summary in new_summaries))
        return len(new_summaries)


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
