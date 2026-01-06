import json
from pathlib import Path

from src.config.settings import AppConfig
from src.monitoring.monitor import PipelineMonitor
from src.pipeline.scheduler import ScheduledRunner


def test_run_once_records_success(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "default_data_dir": str(tmp_path / "data"),
                "tasks": [
                    {
                        "name": "task1",
                        "keywords": ["k1"],
                        "urls": ["https://example.com"],
                        "report_output": str(tmp_path / "report.md"),
                        "interval_minutes": 0,
                    }
                ],
            }
        )
    )
    config = AppConfig.load(config_path)
    log_path = tmp_path / "logs" / "pipeline.log"
    monitor = PipelineMonitor(log_path)

    calls: list[str] = []

    def fake_pipeline(task, app_config):
        calls.append(task.name)
        return {"ran": True}

    def fake_report(task, app_config):
        path = Path(task.report_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok")
        return path

    runner = ScheduledRunner(config, monitor, pipeline_executor=fake_pipeline, report_executor=fake_report)
    runner.run_once()

    log_lines = log_path.read_text().splitlines()
    assert len(log_lines) == 1
    record = json.loads(log_lines[0])
    assert record["status"] == "success"
    assert record["detail"]["ran"] is True
    assert "report_file" in record["detail"]
    assert calls == ["task1"]


def test_run_cycles_respects_max_cycles(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {"name": "repeat", "keywords": ["k"], "urls": ["u"], "interval_minutes": 0}
                ]
            }
        )
    )
    config = AppConfig.load(config_path)
    log_path = tmp_path / "logs" / "pipeline.log"
    monitor = PipelineMonitor(log_path)

    calls: list[str] = []

    def fake_pipeline(task, app_config):
        calls.append(task.name)
        return {}

    runner = ScheduledRunner(config, monitor, pipeline_executor=fake_pipeline)
    runner.run(max_cycles=2, sleep_seconds=0, sleep_fn=lambda _: None)

    assert calls == ["repeat", "repeat"]
    assert len(log_path.read_text().splitlines()) == 2
