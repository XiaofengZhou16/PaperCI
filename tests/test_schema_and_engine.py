from __future__ import annotations

import copy
import json
import tomllib
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from paperci.engine import validate_project
from paperci.findings import Severity
from paperci.project import ProjectDocument, load_project, load_schema
from paperci import __version__

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal-project.yaml"


def test_public_schema_and_example_conform() -> None:
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    project = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(project)
    )
    assert errors == []


def test_package_version_has_single_release_value() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == __version__


def test_non_human_actor_cannot_promote() -> None:
    schema = load_schema()
    project = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    project["reviews"] = [
        {
            "id": "R001",
            "target": "E001",
            "actor": {"kind": "model", "id": "model-under-test"},
            "decision": "verify",
            "timestamp": "2026-08-12T12:00:00+08:00",
        }
    ]
    errors = list(Draft202012Validator(schema).iter_errors(project))
    assert any("'review' was expected" in error.message for error in errors)


def test_minimal_example_exposes_mechanism_overclaim() -> None:
    document = load_project(EXAMPLE)
    findings = validate_project(document, scientific=True)
    keyed = {(finding.rule_id, finding.target, finding.severity) for finding in findings}
    assert ("PCI-MECH-001", "C002", Severity.ERROR) in keyed
    assert ("PCI-STAT-002", "C002", Severity.WARNING) in keyed
    assert not any(finding.rule_id == "PCI-MECH-001" and finding.target == "C001" for finding in findings)


def test_mechanism_rule_accepts_explicit_mechanistic_role() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["evidence"][1]["extensions"] = {
        "org.paperci.core.v1": {"evidence_roles": ["perturbation"]}
    }
    document = ProjectDocument(path=EXAMPLE, data=data)
    findings = validate_project(document, scientific=True)
    assert not any(finding.rule_id == "PCI-MECH-001" for finding in findings)


def test_dangling_reference_is_error() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["claims"][0]["supports"] = ["E999"]
    document = ProjectDocument(path=EXAMPLE, data=data)
    findings = validate_project(document, scientific=False)
    assert any(
        finding.rule_id == "PCI-REF-001"
        and finding.target == "C001"
        and finding.severity == Severity.ERROR
        for finding in findings
    )


def test_bad_row_locator_is_error(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("name,value\na,1\n", encoding="utf-8")
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["evidence"] = [copy.deepcopy(data["evidence"][0])]
    data["evidence"][0]["source"] = {"uri": "data.csv", "locator": "row=99"}
    data["claims"] = []
    data["stories"] = []
    document = ProjectDocument(path=tmp_path / "paperci.yaml", data=data)
    findings = validate_project(document, scientific=False)
    assert any(finding.rule_id == "PCI-PROV-005" for finding in findings)


def test_sarif_shape_is_machine_readable() -> None:
    from paperci.render import findings_sarif

    document = load_project(EXAMPLE)
    payload = json.loads(findings_sarif(document, validate_project(document, scientific=True)))
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["tool"]["driver"]["name"] == "PaperCI"
    assert payload["runs"][0]["results"]
