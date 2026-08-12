from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from paperci import __version__
from paperci.cli import app

runner = CliRunner()


def test_version_option_reports_package_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"paperci {__version__}"


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
    assert project["spec_version"] == "0.3"
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

    result = runner.invoke(
        app,
        [
            "claim",
            str(project_dir),
            "--text",
            "Exposure is associated with a higher outcome in the tested samples.",
            "--support",
            "E001",
            "--scope",
            "system=tested samples",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Added candidate claim C001" in result.output

    result = runner.invoke(
        app,
        ["propose", str(project_dir), "--arcs", "1", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    proposal = json.loads(result.output)
    assert proposal["reused"] is False
    assert proposal["run"]["input_manifest"]["evidence_ids"] == ["E001"]
    assert proposal["stories"][0]["status"] == "candidate"

    unchanged = project_file.read_text(encoding="utf-8")
    result = runner.invoke(
        app,
        ["propose", str(project_dir), "--arcs", "1", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["reused"] is True
    assert project_file.read_text(encoding="utf-8") == unchanged

    result = runner.invoke(app, ["compare", str(project_dir), "--format", "json"])
    assert result.exit_code == 0, result.output
    comparison = json.loads(result.output)
    assert comparison["recommended_for_review"] == "S001"
    assert "scientific_quality_score" not in comparison

    before_hypotheses = project_file.read_text(encoding="utf-8")
    result = runner.invoke(
        app,
        ["hypothesize", str(project_dir), "--format", "json", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["dry_run"] is True
    assert project_file.read_text(encoding="utf-8") == before_hypotheses

    result = runner.invoke(app, ["hypothesize", str(project_dir), "--format", "json"])
    assert result.exit_code == 0, result.output
    hypotheses = json.loads(result.output)
    assert hypotheses["reused"] is False
    assert len(hypotheses["hypotheses"]) == 3
    assert all(item["status"] == "speculative" for item in hypotheses["hypotheses"])
    assert all(item["novelty"]["status"] == "unchecked" for item in hypotheses["hypotheses"])

    result = runner.invoke(app, ["compare-hypotheses", str(project_dir), "--format", "json"])
    assert result.exit_code == 0, result.output
    hypothesis_comparison = json.loads(result.output)
    assert hypothesis_comparison["priority_for_review"] == "H001"
    assert "journal-fit score" in hypothesis_comparison["rationale"]


def test_init_refuses_to_overwrite(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path), "--id", "one"])
    assert result.exit_code == 0
    original = (tmp_path / "paperci.yaml").read_text(encoding="utf-8")
    result = runner.invoke(app, ["init", str(tmp_path), "--id", "two"])
    assert result.exit_code == 2
    assert "Refusing to overwrite" in result.output
    assert (tmp_path / "paperci.yaml").read_text(encoding="utf-8") == original


def test_demo_creates_complete_offline_project_and_refuses_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "paperci-demo"
    result = runner.invoke(app, ["demo", str(destination)])
    assert result.exit_code == 0, result.output
    assert "Expected gate: C002 triggers PCI-MECH-001" in result.output

    project_file = destination / "paperci.yaml"
    report_file = destination / "paperci-report.md"
    assert (destination / "results" / "expression.csv").is_file()
    assert (destination / "results" / "motifs.tsv").is_file()
    assert report_file.is_file()
    project = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    assert project["spec_version"] == "0.3"
    assert [story["id"] for story in project["stories"]] == ["S001", "S002", "S003"]
    assert project["runs"][0]["output_ids"] == ["S001", "S002", "S003"]
    assert [item["id"] for item in project["hypotheses"]] == ["H001", "H002", "H003"]
    assert project["runs"][1]["output_ids"] == ["H001", "H002", "H003"]
    assert "PCI-MECH-001" in report_file.read_text(encoding="utf-8")
    assert "Frontier hypotheses — not current claims" in report_file.read_text(encoding="utf-8")

    validation = runner.invoke(app, ["validate", str(destination), "--format", "json"])
    assert validation.exit_code == 0, validation.output
    assert json.loads(validation.output)["summary"]["error"] == 0

    comparison = runner.invoke(app, ["compare", str(destination), "--format", "json"])
    assert comparison.exit_code == 0, comparison.output
    assert json.loads(comparison.output)["recommended_for_review"] == "S001"

    before = project_file.read_text(encoding="utf-8")
    repeated = runner.invoke(app, ["demo", str(destination)])
    assert repeated.exit_code == 2
    assert "non-empty directory" in repeated.output
    assert project_file.read_text(encoding="utf-8") == before


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


def test_claim_rejects_unknown_evidence(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path), "--id", "unknown-evidence"])
    assert result.exit_code == 0
    result = runner.invoke(
        app,
        ["claim", str(tmp_path), "--text", "A candidate claim.", "--support", "E999"],
    )
    assert result.exit_code == 2
    assert "Unknown evidence ID(s): E999" in result.output


def test_propose_dry_run_does_not_write(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path), "--id", "dry-run"])
    assert result.exit_code == 0
    result = runner.invoke(
        app,
        ["add", str(tmp_path), "--statement", "An observation.", "--source", "notes://one"],
    )
    assert result.exit_code == 0
    result = runner.invoke(
        app,
        ["claim", str(tmp_path), "--text", "A bounded observation.", "--support", "E001"],
    )
    assert result.exit_code == 0
    project_file = tmp_path / "paperci.yaml"
    before = project_file.read_text(encoding="utf-8")
    result = runner.invoke(app, ["propose", str(tmp_path), "--arcs", "1", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert project_file.read_text(encoding="utf-8") == before
    result = runner.invoke(
        app,
        ["propose", str(tmp_path), "--arcs", "1", "--dry-run", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["dry_run"] is True
    assert project_file.read_text(encoding="utf-8") == before
