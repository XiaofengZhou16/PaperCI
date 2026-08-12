from __future__ import annotations

import copy
import json
import tomllib
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from paperci import __version__
from paperci.comparison import compare_stories
from paperci.engine import validate_project
from paperci.errors import HypothesisError, ProposalError
from paperci.findings import Severity
from paperci.hypotheses import (
    DeterministicHypothesisProvider,
    HypothesisProviderResult,
    hypothesize,
)
from paperci.hypothesis_comparison import compare_hypotheses
from paperci.project import ProjectDocument, load_project, load_schema
from paperci.proposals import propose_stories
from paperci.providers import DeterministicStoryProvider, ProviderResult

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal-project.yaml"


def test_public_schema_and_example_conform() -> None:
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    project = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(project))
    assert errors == []


def test_previous_spec_version_remains_readable() -> None:
    schema = load_schema()
    project = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    project["spec_version"] = "0.1"
    project.pop("runs")
    project.pop("hypotheses", None)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(project))
    assert errors == []

    project = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    project["spec_version"] = "0.2"
    project.pop("hypotheses", None)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(project))
    assert errors == []

    project = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    project["spec_version"] = "0.3"
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(project))
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
    assert not any(
        finding.rule_id == "PCI-MECH-001" and finding.target == "C001" for finding in findings
    )


def test_mechanism_rule_accepts_explicit_mechanistic_role() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["evidence"][1]["extensions"] = {
        "org.paperci.core.v1": {"evidence_roles": ["perturbation"]}
    }
    document = ProjectDocument(path=EXAMPLE, data=data)
    findings = validate_project(document, scientific=True)
    assert not any(finding.rule_id == "PCI-MECH-001" for finding in findings)


def test_prohibited_claim_is_historical_but_cannot_remain_in_active_story() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["claims"][1]["status"] = "prohibited"
    document = ProjectDocument(path=EXAMPLE, data=data)
    findings = validate_project(document, scientific=True)
    assert not any(
        finding.rule_id == "PCI-MECH-001" and finding.target == "C002" for finding in findings
    )
    assert any(
        finding.rule_id == "PCI-STORY-001" and finding.target == "S001" for finding in findings
    )

    data["stories"][0]["status"] = "rejected"
    findings = validate_project(document, scientific=True)
    assert not any(finding.rule_id == "PCI-STORY-001" for finding in findings)


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


def test_deterministic_proposal_is_bounded_idempotent_and_supersedable() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["spec_version"] = "0.1"
    data["stories"] = []
    data["runs"] = []
    document = ProjectDocument(path=EXAMPLE, data=data)
    provider = DeterministicStoryProvider()

    first = propose_stories(document, provider, arcs=3)
    assert first.document.data["spec_version"] == "0.4"
    assert first.document.data["hypotheses"] == []
    assert len(first.stories) == 3
    assert first.reused is False
    assert first.run["input_manifest"] == {
        "evidence_ids": ["E001", "E002"],
        "claim_ids": ["C001", "C002"],
    }
    all_evidence = {item["id"] for item in data["evidence"]}
    all_claims = {item["id"] for item in data["claims"]}
    gap_ids: list[str] = []
    for story in first.stories:
        assert set(story["claim_path"]) <= all_claims
        for figure in story["figure_plan"]:
            assert set(figure["evidence_ids"]) <= all_evidence
            assert set(figure["claim_ids"]) <= all_claims
        gap_ids.extend(gap["id"] for gap in story["gaps"])
    assert len(gap_ids) == len(set(gap_ids))
    assert not any(
        finding.severity == Severity.ERROR
        and finding.rule_id in {"PCI-SCHEMA-001", "PCI-REF-001", "PCI-AI-001"}
        for finding in validate_project(first.document, scientific=True)
    )

    first.document.data["evidence"].reverse()
    first.document.data["claims"].reverse()
    reused = propose_stories(first.document, provider, arcs=3)
    assert reused.reused is True
    assert reused.run["id"] == first.run["id"]
    assert len(reused.document.data["runs"]) == 1

    first.document.data["claims"][0]["text"] += " Updated."
    changed = propose_stories(first.document, provider, arcs=3)
    assert changed.reused is False
    assert changed.run["id"] == "RUN002"
    assert len(changed.document.data["runs"]) == 2
    old_ids = set(first.run["output_ids"])
    assert all(
        story["status"] == "superseded"
        for story in changed.document.data["stories"]
        if story["id"] in old_ids
    )


def test_generated_story_cannot_escape_run_manifest() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []
    outcome = propose_stories(
        ProjectDocument(path=EXAMPLE, data=data),
        DeterministicStoryProvider(),
        arcs=1,
    )
    outcome.document.data["runs"][0]["input_manifest"]["evidence_ids"] = []
    findings = validate_project(outcome.document, scientific=True)
    assert any(
        finding.rule_id == "PCI-AI-001"
        and finding.target == "S001"
        and finding.severity == Severity.ERROR
        for finding in findings
    )
    outcome.document.data["runs"][0]["input_manifest"]["evidence_ids"] = ["E001", "E002"]
    outcome.document.data["stories"][0].pop("extensions")
    findings = validate_project(outcome.document, scientific=True)
    assert any(finding.rule_id == "PCI-AI-001" and finding.target == "S001" for finding in findings)


def test_comparison_recommends_only_a_gate_passing_story() -> None:
    document = load_project(EXAMPLE)
    outcome = propose_stories(document, DeterministicStoryProvider(), arcs=3)
    comparison = compare_stories(outcome.document)
    rows = {row.story_id: row for row in comparison.stories}
    assert comparison.recommended_for_review == "S002"
    assert rows["S002"].gate_status == "pass"
    assert rows["S003"].gate_status == "fail"
    assert "not a scientific-quality score" in comparison.rationale

    outcome.document.data["evidence"][0]["status"] = "verified"
    comparison = compare_stories(outcome.document)
    rows = {row.story_id: row for row in comparison.stories}
    assert rows["S002"].gate_status == "fail"
    assert comparison.recommended_for_review is None


def test_provider_output_with_invented_reference_is_rejected() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []

    class EscapingProvider(DeterministicStoryProvider):
        provider_id = "test.escaping-provider"

        def propose(self, context):
            result = super().propose(context)
            story = copy.deepcopy(result.stories[0])
            story["figure_plan"][0]["evidence_ids"] = ["E999"]
            return ProviderResult((story,))

    with pytest.raises(ProposalError, match="project boundary"):
        propose_stories(ProjectDocument(path=EXAMPLE, data=data), EscapingProvider(), arcs=1)


def test_provider_rules_do_not_depend_on_claim_id_prefix() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["claims"][1]["id"] = "mechanism-hypothesis"
    data["stories"] = []
    data["runs"] = []
    outcome = propose_stories(
        ProjectDocument(path=EXAMPLE, data=data),
        DeterministicStoryProvider(),
        arcs=2,
    )
    risky = outcome.stories[1]
    assert risky["central_claim"] == "mechanism-hypothesis"
    assert "PCI-MECH-001" in risky["gaps"][0]["question"]


def test_provider_cannot_self_promote_a_story() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []

    class SelfPromotingProvider(DeterministicStoryProvider):
        provider_id = "test.self-promoting-provider"

        def propose(self, context):
            result = super().propose(context)
            story = copy.deepcopy(result.stories[0])
            story["status"] = "selected"
            return ProviderResult((story,))

    outcome = propose_stories(
        ProjectDocument(path=EXAMPLE, data=data),
        SelfPromotingProvider(),
        arcs=1,
    )
    assert outcome.stories[0]["status"] == "candidate"


def test_hypotheses_are_bounded_falsifiable_idempotent_and_supersedable() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []
    document = ProjectDocument(path=EXAMPLE, data=data)

    first = hypothesize(document, count=3)
    assert first.document.data["spec_version"] == "0.4"
    assert len(first.hypotheses) == 3
    assert [item["strategy"] for item in first.hypotheses] == [
        "mechanistic-deepening",
        "cross-scale-bridge",
        "paradigm-challenge",
    ]
    assert all(item["status"] == "speculative" for item in first.hypotheses)
    assert all(item["novelty"]["status"] == "unchecked" for item in first.hypotheses)
    assert all(item["decisive_tests"][0]["falsifier"] for item in first.hypotheses)
    assert all(item["alternatives"] for item in first.hypotheses)
    assert all(
        item["inference_steps"][0]["statement"] != data["claims"][1]["text"]
        for item in first.hypotheses
    )
    assert first.run["input_manifest"] == {
        "evidence_ids": ["E001", "E002"],
        "claim_ids": ["C001", "C002"],
    }
    assert len(first.document.data["claims"]) == len(data["claims"])

    first.document.data["evidence"].reverse()
    first.document.data["claims"].reverse()
    reused = hypothesize(first.document, count=3)
    assert reused.reused is True
    assert reused.run["id"] == first.run["id"]

    first.document.data["claims"][0]["text"] += " Updated."
    changed = hypothesize(first.document, count=3)
    assert changed.reused is False
    assert changed.run["id"] == "RUN002"
    previous_ids = set(first.run["output_ids"])
    assert all(
        item["status"] == "superseded"
        for item in changed.document.data["hypotheses"]
        if item["id"] in previous_ids
    )


def test_generated_hypothesis_cannot_escape_run_manifest() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []
    outcome = hypothesize(ProjectDocument(path=EXAMPLE, data=data), count=1)
    extra = copy.deepcopy(data["evidence"][0])
    extra["id"] = "E003"
    outcome.document.data["evidence"].append(extra)
    outcome.document.data["hypotheses"][0]["evidence_ids"].append("E003")
    findings = validate_project(outcome.document, scientific=True)
    assert any(
        finding.rule_id == "PCI-AI-001"
        and finding.target == "H001"
        and finding.severity == Severity.ERROR
        for finding in findings
    )


def test_hypothesis_comparison_is_multidimensional_not_a_journal_score() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []
    outcome = hypothesize(ProjectDocument(path=EXAMPLE, data=data), count=3)
    comparison = compare_hypotheses(outcome.document)
    assert comparison.priority_for_review == "H001"
    assert all(row.novelty == "unchecked" for row in comparison.hypotheses)
    assert "not a journal-fit score" in comparison.rationale
    assert "publication forecast" in comparison.rationale


def test_checked_novelty_requires_dated_literature_sources() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []
    outcome = hypothesize(ProjectDocument(path=EXAMPLE, data=data), count=1)
    hypothesis = outcome.document.data["hypotheses"][0]
    hypothesis["novelty"] = {
        "status": "potentially_novel",
        "note": "Claimed without a search record.",
        "literature_sources": [],
    }
    errors = list(
        Draft202012Validator(load_schema(), format_checker=FormatChecker()).iter_errors(
            outcome.document.data
        )
    )
    assert any("is a required property" in error.message for error in errors)
    assert any("should be non-empty" in error.message for error in errors)


def test_hypothesis_shortlisting_requires_human_selection() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []
    outcome = hypothesize(ProjectDocument(path=EXAMPLE, data=data), count=1)
    outcome.document.data["hypotheses"][0]["status"] = "shortlisted"
    findings = validate_project(outcome.document, scientific=True)
    assert any(finding.rule_id == "PCI-HYP-004" for finding in findings)

    outcome.document.data["reviews"] = [
        {
            "id": "R001",
            "target": "H001",
            "actor": {"kind": "human", "id": "researcher"},
            "decision": "select",
            "timestamp": "2026-08-13T00:00:00+08:00",
        }
    ]
    findings = validate_project(outcome.document, scientific=True)
    assert not any(finding.rule_id == "PCI-HYP-004" for finding in findings)


def test_hypothesis_provider_cannot_self_promote_or_escape_inputs() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []

    class SelfPromotingProvider(DeterministicHypothesisProvider):
        provider_id = "test.self-promoting-hypothesis-provider"

        def generate(self, context):
            result = super().generate(context)
            item = copy.deepcopy(result.hypotheses[0])
            item["status"] = "shortlisted"
            return HypothesisProviderResult((item,))

    outcome = hypothesize(
        ProjectDocument(path=EXAMPLE, data=copy.deepcopy(data)),
        SelfPromotingProvider(),
        count=1,
    )
    assert outcome.hypotheses[0]["status"] == "speculative"

    class EscapingProvider(DeterministicHypothesisProvider):
        provider_id = "test.escaping-hypothesis-provider"

        def generate(self, context):
            result = super().generate(context)
            item = copy.deepcopy(result.hypotheses[0])
            item["evidence_ids"] = ["E999"]
            return HypothesisProviderResult((item,))

    with pytest.raises(HypothesisError, match="project boundary"):
        hypothesize(
            ProjectDocument(path=EXAMPLE, data=copy.deepcopy(data)),
            EscapingProvider(),
            count=1,
        )


def test_offline_hypothesis_provider_cannot_claim_novelty() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["runs"] = []

    class FalseNoveltyProvider(DeterministicHypothesisProvider):
        provider_id = "test.false-novelty-provider"

        def generate(self, context):
            result = super().generate(context)
            item = copy.deepcopy(result.hypotheses[0])
            item["novelty"] = {
                "status": "potentially_novel",
                "note": "Unverified priority claim.",
                "checked_at": "2026-08-13T00:00:00+08:00",
                "literature_sources": [{"uri": "doi:10.0000/example"}],
            }
            return HypothesisProviderResult((item,))

    with pytest.raises(HypothesisError, match="PCI-HYP-005"):
        hypothesize(
            ProjectDocument(path=EXAMPLE, data=data),
            FalseNoveltyProvider(),
            count=1,
        )
