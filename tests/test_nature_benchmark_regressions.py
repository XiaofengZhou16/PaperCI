from __future__ import annotations

import copy
from pathlib import Path

import yaml

from paperci.engine import validate_project
from paperci.findings import Severity
from paperci.hypotheses import hypothesize
from paperci.project import ProjectDocument
from paperci.proposals import propose_stories
from paperci.providers import DeterministicStoryProvider

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal-project.yaml"


def _data() -> dict:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["stories"] = []
    data["hypotheses"] = []
    data["reviews"] = []
    data["runs"] = []
    return data


def _document(data: dict) -> ProjectDocument:
    return ProjectDocument(path=EXAMPLE, data=data)


def _has(findings, rule_id: str, target: str, severity: Severity | None = None) -> bool:
    return any(
        finding.rule_id == rule_id
        and finding.target == target
        and (severity is None or finding.severity == severity)
        for finding in findings
    )


def test_lineage_tracing_satisfies_bounded_mechanism_gate() -> None:
    data = _data()
    data["evidence"][1]["statement"] = (
        "Clone-label permutation identified mitotically inherited AP-1 accessibility."
    )
    data["evidence"][1]["extensions"] = {
        "org.paperci.core.v1": {"evidence_roles": ["lineage_tracing"]}
    }
    data["claims"][1]["text"] = (
        "AP-1 accessibility is inherited through cell divisions in the tested organoids."
    )
    findings = validate_project(_document(data), scientific=True)
    assert not _has(findings, "PCI-MECH-001", "C002")


def test_lineage_tracing_does_not_unlock_an_unrelated_binding_mechanism() -> None:
    data = _data()
    data["evidence"][1]["extensions"] = {
        "org.paperci.core.v1": {"evidence_roles": ["lineage_tracing"]}
    }
    findings = validate_project(_document(data), scientific=True)
    assert _has(findings, "PCI-MECH-001", "C002", Severity.ERROR)


def test_same_evidence_cannot_support_and_challenge_a_claim() -> None:
    data = _data()
    data["claims"][0]["challenges"] = ["E001"]
    findings = validate_project(_document(data), scientific=True)
    assert _has(findings, "PCI-REL-001", "C001", Severity.ERROR)


def test_cell_clone_inheritance_does_not_support_organismal_transmission() -> None:
    data = _data()
    data["evidence"] = [copy.deepcopy(data["evidence"][1])]
    data["evidence"][0]["statement"] = (
        "Clonal labels and AP-1 accessibility were inherited through cell divisions in organoids."
    )
    data["evidence"][0]["extensions"] = {
        "org.paperci.core.v1": {"evidence_roles": ["lineage_tracing"]}
    }
    data["claims"] = [copy.deepcopy(data["claims"][1])]
    data["claims"][0].update(
        {
            "text": "The memory is transmitted between animals and their offspring.",
            "type": "generalization",
            "supports": ["E002"],
            "challenges": [],
        }
    )
    findings = validate_project(_document(data), scientific=True)
    assert _has(findings, "PCI-SEM-001", "C002", Severity.ERROR)


def test_tumour_outgrowth_does_not_support_initiation_frequency() -> None:
    data = _data()
    data["evidence"] = [copy.deepcopy(data["evidence"][0])]
    data["evidence"][0].update(
        {
            "statement": (
                "Recovered mice had larger tumours, but did not have more macroscopic tumours."
            ),
            "extensions": {"org.paperci.core.v1": {"evidence_roles": ["temporal_intervention"]}},
        }
    )
    data["claims"] = [copy.deepcopy(data["claims"][0])]
    data["claims"][0].update(
        {
            "text": "Prior inflammation increases the frequency of tumour-initiation events.",
            "type": "causal_effect",
            "supports": ["E001"],
            "challenges": [],
        }
    )
    findings = validate_project(_document(data), scientific=True)
    assert _has(findings, "PCI-SEM-001", "C001", Severity.ERROR)


def test_nested_units_require_parent_unit_and_cluster_counts() -> None:
    data = _data()
    evidence = data["evidence"][0]
    evidence["design"]["unit_of_analysis"] = "tumour_nested_within_mouse"
    evidence["design"]["groups"] = [
        {"id": "control", "n": 88},
        {"id": "recovered", "n": 256},
    ]
    findings = validate_project(_document(data), scientific=True)
    assert _has(findings, "PCI-STAT-003", "E001", Severity.WARNING)

    evidence["design"]["parent_unit"] = "mouse"
    evidence["design"]["groups"][0]["clusters"] = 7
    evidence["design"]["groups"][1]["clusters"] = 10
    findings = validate_project(_document(data), scientific=True)
    assert not _has(findings, "PCI-STAT-003", "E001")


def test_claim_dependencies_are_references_and_must_be_acyclic() -> None:
    data = _data()
    data["claims"][0]["depends_on"] = ["C999"]
    findings = validate_project(_document(data), scientific=False)
    assert _has(findings, "PCI-REF-001", "C001", Severity.ERROR)

    data["claims"][0]["depends_on"] = ["C002"]
    data["claims"][1]["depends_on"] = ["C001"]
    findings = validate_project(_document(data), scientific=False)
    assert _has(findings, "PCI-CLAIM-001", "C001", Severity.ERROR)
    assert _has(findings, "PCI-CLAIM-001", "C002", Severity.ERROR)


def test_dependency_driven_story_recovers_a_long_reasoning_chain() -> None:
    data = _data()
    data["evidence"][1]["extensions"] = {
        "org.paperci.core.v1": {"evidence_roles": ["functional_perturbation"]}
    }
    claims = data["claims"]
    claims[1]["depends_on"] = ["C001"]
    for number in (3, 4):
        claim = copy.deepcopy(claims[1])
        claim["id"] = f"C00{number}"
        claim["text"] = f"Mechanistic step {number} follows from the preceding step."
        claim["depends_on"] = [f"C00{number - 1}"]
        claims.append(claim)

    outcome = propose_stories(_document(data), DeterministicStoryProvider(), arcs=1)
    story = outcome.stories[0]
    assert story["central_claim"] == "C004"
    assert story["claim_path"] == ["C001", "C002", "C003", "C004"]
    assert len(story["figure_plan"]) == 4


def test_hypothesis_tests_name_the_process_and_use_distinct_alternatives() -> None:
    data = _data()
    data["evidence"][1]["extensions"] = {
        "org.paperci.core.v1": {"evidence_roles": ["perturbation"]}
    }
    data["claims"][1].update(
        {
            "text": "Persistent AP-1 accessibility executes epithelial inflammatory memory.",
            "depends_on": ["C001"],
            "alternatives": [
                "The inhibitor has AP-1-independent toxicity.",
                "AP-1 executes memory but another chromatin layer stores it.",
            ],
        }
    )
    outcome = hypothesize(_document(data), count=3, seed_claim="C002")
    h1, h2, h3 = outcome.hypotheses
    assert "AP-1" in h1["decisive_tests"][0]["design"]
    assert h2["anchor_claims"] == ["C002", "C001"]
    assert "AP-1" in h2["decisive_tests"][0]["design"]
    assert "another chromatin layer stores it" in h3["statement"]
    assert "another chromatin layer stores it" in h3["decisive_tests"][0]["design"]
    assert (
        h3["decisive_tests"][0]["distinguishes"][1].removeprefix("competing explanation: ")
        in h3["alternatives"]
    )
    assert (
        h3["decisive_tests"][0]["distinguishes"][0] != h3["decisive_tests"][0]["distinguishes"][1]
    )
