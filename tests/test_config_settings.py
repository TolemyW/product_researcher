from pathlib import Path
import os

from src.config.settings import AppConfig, load_app_config, load_env_file


def test_load_env_file_sets_missing(monkeypatch, tmp_path):
    env_path = tmp_path / "test.env"
    env_path.write_text("OPENAI_API_KEY=abc\n#comment\nEMPTY=\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EMPTY", raising=False)

    load_env_file(env_path)

    assert os.getenv("OPENAI_API_KEY") == "abc"
    assert os.getenv("EMPTY") == ""


def test_load_app_config_with_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
{
  "default_data_dir": "data/base",
  "default_product_type": "software",
  "default_concurrency": 3,
  "tasks": [
    {"name": "t1", "keywords": ["k"], "interval_minutes": 5}
  ]
}
"""
    )

    config = load_app_config(config_path)

    assert isinstance(config.default_data_dir, Path)
    assert config.default_data_dir.name == "base"
    assert config.default_product_type == "software"
    assert config.default_concurrency == 3
    assert len(config.tasks) == 1
    task = config.tasks[0]
    assert task.name == "t1"
    assert task.interval_minutes == 5
    # falls back to defaults when missing
    assert task.product_type == "software"
    assert task.concurrency == 3  # falls back to default_concurrency
