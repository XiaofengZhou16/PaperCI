from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from paperci.cli import app

runner = CliRunner()


def test_init_add_validate_lint_and_report(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    result = runner.invoke(
        app,
        ["init", str(project_dir), "--id", "demo-study", "--title", "Demo study"],
    )
    assert result.exit_code == 0, result.output
    project_file = project_dir / "paperci.yaml"
    assert project_file.is_file()

    result = runner.invoke(
        app,
        [
            "add",
            str(project_dir),
            "--statement",
            "Outcome was higher in exposed samples.",
            "--source",
            "notes://pilot",
            "--locator",
            "result-1",
            "--unit-of-analysis",
            "sample",
            "--group",
            "control=5",
            "--group",
            "exposed=5",
        ],
    )
    assert result.exit_code == 0, result.output
    project = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    assert project["evidence"][0]["id"] == "E001"
    assert project["evidence"][0]["status"] == "draft"

    result = runner.invoke(app, ["validate", str(project_dir), "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["summary"]["error"] == 0

    result = runner.invoke(app, ["lint", str(project_dir), "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    assert "No findings." in result.output

    report_path = project_dir / "report.md"
    result = runner.invoke(app, ["report", str(project_dir), "-o", str(report_path)])
    assert result.exit_code == 0, result.output
    assert "PaperCI report: Demo study" in report_path.read_text(encoding="utf-8")


def test_init_refuses_to_overwrite(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path), "--id", "one"])
    assert result.exit_code == 0
    original = (tmp_path / "paperci.yaml").read_text(encoding="utf-8")
    result = runner.invoke(app, ["init", str(tmp_path), "--id", "two"])
    assert result.exit_code == 2
    assert "Refusing to overwrite" in result.output
    assert (tmp_path / "paperci.yaml").read_text(encoding="utf-8") == original


def test_lint_exit_thresholds() -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "minimal-project.yaml"
    result = runner.invoke(app, ["lint", str(example)])
    assert result.exit_code == 1
    assert "PCI-MECH-001" in result.output
    result = runner.invoke(app, ["lint", str(example), "--fail-on", "never"])
    assert result.exit_code == 0


def test_doctor_is_offline_and_accepts_project() -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "minimal-project.yaml"
    result = runner.invoke(app, ["doctor", str(example)])
    assert result.exit_code == 0, result.output
    assert "PASS  Offline core" in result.output
