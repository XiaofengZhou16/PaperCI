from __future__ import annotations

import hashlib
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
    assert project["spec_version"] == "0.4"
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


def test_mechanistic_biology_profile_starts_empty_and_exposes_workflow(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", str(tmp_path), "--id", "mechanism-study", "--profile", "mechanistic-biology"],
    )
    assert result.exit_code == 0, result.output
    assert "evidence remains empty" in result.output
    project = yaml.safe_load((tmp_path / "paperci.yaml").read_text(encoding="utf-8"))
    assert project["evidence"] == []
    profile = project["extensions"]["org.paperci.profile.v1"]
    assert profile["name"] == "mechanistic-biology"
    assert [item["role"] for item in profile["evidence_workflow"]] == [
        "observation",
        "intervention",
        "target_engagement",
        "rescue",
        "orthogonal",
        "nested_units",
    ]
    validation = runner.invoke(app, ["validate", str(tmp_path), "--format", "json"])
    assert validation.exit_code == 0, validation.output


def test_import_table_is_draft_hashed_mapped_and_idempotent(tmp_path: Path) -> None:
    assert runner.invoke(app, ["init", str(tmp_path), "--id", "table-study"]).exit_code == 0
    table = tmp_path / "results.csv"
    table.write_text(
        "finding,unit,evidence_type\n"
        "Target increased,mouse,quantitative_result\n"
        "Morphology changed,organoid,qualitative_observation\n",
        encoding="utf-8",
    )
    project_file = tmp_path / "paperci.yaml"
    before = project_file.read_text(encoding="utf-8")
    dry_run = runner.invoke(
        app,
        [
            "import-table",
            str(tmp_path),
            str(table),
            "--statement-column",
            "finding",
            "--kind-column",
            "evidence_type",
            "--unit-column",
            "unit",
            "--dry-run",
            "--format",
            "json",
        ],
    )
    assert dry_run.exit_code == 0, dry_run.output
    assert json.loads(dry_run.output)["dry_run"] is True
    assert project_file.read_text(encoding="utf-8") == before

    result = runner.invoke(
        app,
        [
            "import-table",
            str(tmp_path),
            str(table),
            "--statement-column",
            "finding",
            "--kind-column",
            "evidence_type",
            "--unit-column",
            "unit",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "No claims or mechanism inferences were generated" in result.output
    project = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    assert project["claims"] == []
    assert [item["status"] for item in project["evidence"]] == ["draft", "draft"]
    assert [item["source"]["locator"] for item in project["evidence"]] == ["row=2", "row=3"]
    expected_hash = hashlib.sha256(table.read_bytes()).hexdigest()
    assert {item["source"]["sha256"] for item in project["evidence"]} == {expected_hash}
    assert all(
        item["extensions"]["org.paperci.import.v1"]["verification"] == "unverified"
        for item in project["evidence"]
    )
    manifest = project["extensions"]["org.paperci.import.v1"]["runs"][0]
    assert manifest["columns"] == {
        "statement": "finding",
        "kind": "evidence_type",
        "unit_of_analysis": "unit",
    }
    assert manifest["imported_ids"] == ["E001", "E002"]
    validation = runner.invoke(app, ["validate", str(tmp_path), "--format", "json"])
    assert validation.exit_code == 0, validation.output

    duplicate = runner.invoke(
        app,
        [
            "import-table",
            str(tmp_path),
            str(table),
            "--statement-column",
            "finding",
            "--kind-column",
            "evidence_type",
            "--unit-column",
            "unit",
        ],
    )
    assert duplicate.exit_code == 2
    assert "already imported" in duplicate.output


def test_import_table_rejects_missing_statement_without_partial_write(tmp_path: Path) -> None:
    assert runner.invoke(app, ["init", str(tmp_path), "--id", "invalid-table"]).exit_code == 0
    table = tmp_path / "invalid.tsv"
    table.write_text("finding\tunit\n\tmouse\n", encoding="utf-8")
    project_file = tmp_path / "paperci.yaml"
    before = project_file.read_text(encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "import-table",
            str(tmp_path),
            str(table),
            "--statement-column",
            "finding",
            "--unit-column",
            "unit",
        ],
    )
    assert result.exit_code == 2
    assert "is empty at row 2" in result.output
    assert project_file.read_text(encoding="utf-8") == before


def test_explain_mechanism_rule_in_text_and_json() -> None:
    text_result = runner.invoke(app, ["explain", "pci-mech-001"])
    assert text_result.exit_code == 0, text_result.output
    assert "passing the core gate does not prove the complete mechanism" in text_result.output
    assert "Counterexample" in text_result.output
    json_result = runner.invoke(app, ["explain", "PCI-MECH-001", "--format", "json"])
    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output)
    assert payload["rule_id"] == "PCI-MECH-001"
    assert payload["severity"] == "error"


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
    assert project["spec_version"] == "0.4"
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


def test_cli_records_nested_units_and_claim_dependencies(tmp_path: Path) -> None:
    assert runner.invoke(app, ["init", str(tmp_path), "--id", "reasoning-graph"]).exit_code == 0
    result = runner.invoke(
        app,
        [
            "add",
            str(tmp_path),
            "--statement",
            "Tumours were measured within mice.",
            "--source",
            "notes://nested",
            "--unit-of-analysis",
            "tumour_nested_within_mouse",
            "--parent-unit",
            "mouse",
            "--group",
            "control=88",
            "--cluster",
            "control=7",
        ],
    )
    assert result.exit_code == 0, result.output
    first = runner.invoke(
        app,
        [
            "claim",
            str(tmp_path),
            "--text",
            "Tumours showed bounded outgrowth.",
            "--support",
            "E001",
        ],
    )
    assert first.exit_code == 0, first.output
    second = runner.invoke(
        app,
        [
            "claim",
            str(tmp_path),
            "--text",
            "The outgrowth follows the recorded prerequisite.",
            "--support",
            "E001",
            "--depends-on",
            "C001",
        ],
    )
    assert second.exit_code == 0, second.output
    project = yaml.safe_load((tmp_path / "paperci.yaml").read_text(encoding="utf-8"))
    assert project["evidence"][0]["design"]["parent_unit"] == "mouse"
    assert project["evidence"][0]["design"]["groups"][0]["clusters"] == 7
    assert project["claims"][1]["depends_on"] == ["C001"]


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
