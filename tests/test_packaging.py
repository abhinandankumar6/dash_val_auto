import os
from pathlib import Path

from bi_validator.core.config_loader import load_rule_bundle
from bi_validator.core.runtime import resolve_existing_path
from bi_validator.launcher import configure_standalone_environment


def test_relative_rule_path_resolves_from_project_bundle():
    path = resolve_existing_path("config/rules/default_rules.yaml")

    assert path.exists()
    assert path.name == "default_rules.yaml"
    assert load_rule_bundle("config/rules/default_rules.yaml").execution.max_depth == 4


def test_standalone_launcher_sets_local_runtime_defaults(monkeypatch, tmp_path):
    for key in (
        "APP_ENV",
        "AUTO_CREATE_TABLES",
        "QUEUE_BACKEND",
        "DATABASE_URL",
        "REPORT_ROOT",
        "SCREENSHOT_ROOT",
        "PLAYWRIGHT_HEADLESS",
    ):
        monkeypatch.delenv(key, raising=False)

    configure_standalone_environment(tmp_path, show_automation_browser=True)

    assert Path(tmp_path, "reports").exists()
    assert Path(tmp_path, "screenshots").exists()
    assert Path(tmp_path, "bi_validator.db").name == "bi_validator.db"
    assert "sqlite:///" in os.environ["DATABASE_URL"]
    assert os.environ["QUEUE_BACKEND"] == "inline"
    assert os.environ["PLAYWRIGHT_HEADLESS"] == "false"
