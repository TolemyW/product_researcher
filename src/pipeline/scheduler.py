from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Optional

from src.pipeline.runtime import build_fetch_strategy, run_pipeline, run_report
from src.config.settings import AppConfig, TaskConfig
from src.monitoring.monitor import PipelineMonitor, RunResult
from src.storage.data_store import DataStore

PipelineExecutor = Callable[[TaskConfig, AppConfig], Dict]
ReportExecutor = Callable[[TaskConfig, AppConfig], Optional[Path]]


class ScheduledRunner:
    def __init__(
        self,
        config: AppConfig,
        monitor: PipelineMonitor,
        pipeline_executor: PipelineExecutor | None = None,
        report_executor: ReportExecutor | None = None,
    ) -> None:
        self.config = config
        self.monitor = monitor
        self.pipeline_executor = pipeline_executor or self._run_pipeline_task
        self.report_executor = report_executor or self._run_report

    def run_once(self) -> None:
        for task in self.config.tasks:
            self._execute(task)

    def run(
        self,
        *,
        max_cycles: int | None = None,
        sleep_seconds: int = 60,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        next_run: Dict[str, datetime] = {task.name: datetime.utcnow() for task in self.config.tasks}
        cycles = 0
        while True:
            now = datetime.utcnow()
            for task in self.config.tasks:
                if now >= next_run[task.name]:
                    self._execute(task)
                    next_run[task.name] = now + timedelta(minutes=task.interval_minutes)
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            sleep_fn(sleep_seconds)

    def _execute(self, task: TaskConfig) -> None:
        started = self.monitor.start()
        detail: Dict[str, object] = {}
        error: str | None = None
        try:
            detail = self.pipeline_executor(task, self.config) or {}
            if task.report_output:
                report_path = self.report_executor(task, self.config)
                if report_path:
                    detail["report_file"] = str(report_path)
            status = "success"
        except Exception as exc:  # pragma: no cover - tested via monitor output
            status = "failed"
            error = str(exc)
        finished_at, duration = self.monitor.finish(started)
        self.monitor.record(
            RunResult(
                task=task.name,
                status=status,
                started_at=started.isoformat() + "Z",
                finished_at=finished_at,
                duration_seconds=duration,
                detail=detail,
                error=error,
            )
        )

    def _run_pipeline_task(self, task: TaskConfig, config: AppConfig) -> Dict:
        data_dir = task.data_dir or config.default_data_dir
        store = DataStore(data_dir=data_dir)
        strategy = build_fetch_strategy(task.product_type or config.default_product_type, None, None, None, None)
        run_pipeline(
            task.keywords,
            task.urls,
            task.product_type or config.default_product_type,
            strategy,
            store,
            concurrency=task.concurrency or config.default_concurrency,
            keyword_brief=task.keyword_brief,
            llm_model=task.llm_model or config.default_llm_model,
            use_llm=task.use_llm or config.default_use_llm,
        )
        return {
            "data_dir": str(data_dir),
            "keywords": task.keywords,
            "urls": task.urls,
            "product_type": task.product_type or config.default_product_type,
        }

    def _run_report(self, task: TaskConfig, config: AppConfig) -> Optional[Path]:
        if not task.report_output:
            return None
        data_dir = task.data_dir or config.default_data_dir
        store = DataStore(data_dir=data_dir)
        title = task.report_title or "产品研究报告"
        output = task.report_output
        output.parent.mkdir(parents=True, exist_ok=True)
        run_report(store, title, output)
        return output


def build_runner(config_path: Path, log_path: Optional[Path] = None) -> ScheduledRunner:
    config = AppConfig.load(config_path)
    log_dir = log_path.parent if log_path else config.log_dir
    log_file = log_path or (log_dir / "pipeline.log")
    monitor = PipelineMonitor(log_file)
    return ScheduledRunner(config, monitor)
