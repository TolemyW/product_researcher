from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_env_file(path: Path) -> None:
    """Load environment variables from a simple KEY=VALUE file."""

    if not path.exists():
        return

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class TaskConfig:
    name: str
    keywords: List[str] = field(default_factory=list)
    keyword_brief: str | None = None
    urls: List[str] = field(default_factory=list)
    product_type: str | None = None
    concurrency: int = 1
    use_llm: bool = False
    llm_model: str | None = None
    data_dir: Optional[Path] = None
    report_output: Optional[Path] = None
    report_title: Optional[str] = None
    interval_minutes: int = 60

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any], defaults: Dict[str, Any]) -> "TaskConfig":
        return cls(
            name=name,
            keywords=list(data.get("keywords") or []),
            keyword_brief=data.get("keyword_brief"),
            urls=list(data.get("urls") or []),
            product_type=data.get("product_type") or defaults.get("product_type"),
            concurrency=int(data.get("concurrency", defaults.get("concurrency", 1))),
            use_llm=bool(data.get("use_llm", defaults.get("use_llm", False))),
            llm_model=data.get("llm_model") or defaults.get("llm_model"),
            data_dir=Path(data["data_dir"]) if data.get("data_dir") else defaults.get("data_dir"),
            report_output=Path(data["report_output"]) if data.get("report_output") else None,
            report_title=data.get("report_title"),
            interval_minutes=int(data.get("interval_minutes", defaults.get("interval_minutes", 60))),
        )


@dataclass
class AppConfig:
    tasks: List[TaskConfig]
    default_data_dir: Path = Path("data")
    default_llm_model: str | None = None
    default_use_llm: bool = False
    default_product_type: str | None = None
    default_concurrency: int = 1
    default_interval_minutes: int = 60
    log_dir: Path = Path("logs")

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        raw = json.loads(path.read_text())
        env_file = raw.get("env_file")
        if env_file:
            load_env_file(Path(env_file))

        defaults = {
            "data_dir": Path(raw.get("default_data_dir", "data")),
            "llm_model": raw.get("default_llm_model"),
            "use_llm": raw.get("default_use_llm", False),
            "product_type": raw.get("default_product_type"),
            "concurrency": raw.get("default_concurrency", 1),
            "interval_minutes": raw.get("default_interval_minutes", 60),
        }

        tasks: list[TaskConfig] = []
        for idx, task_raw in enumerate(raw.get("tasks", [])):
            name = task_raw.get("name") or f"task_{idx + 1}"
            tasks.append(TaskConfig.from_dict(name, task_raw, defaults))

        log_dir = Path(raw.get("log_dir", "logs"))

        return cls(
            tasks=tasks,
            default_data_dir=defaults["data_dir"],
            default_llm_model=defaults["llm_model"],
            default_use_llm=bool(defaults["use_llm"]),
            default_product_type=defaults["product_type"],
            default_concurrency=int(defaults["concurrency"]),
            default_interval_minutes=int(defaults["interval_minutes"]),
            log_dir=log_dir,
        )


def load_app_config(path: Path) -> AppConfig:
    return AppConfig.load(path)
