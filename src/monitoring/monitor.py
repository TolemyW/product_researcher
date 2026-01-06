from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class RunResult:
    task: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    detail: Dict[str, Any]
    error: Optional[str] = None


class PipelineMonitor:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, result: RunResult) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

    def start(self) -> datetime:
        return datetime.utcnow()

    def finish(self, start: datetime) -> tuple[str, float]:
        finished = datetime.utcnow()
        duration = (finished - start).total_seconds()
        return finished.isoformat() + "Z", duration
