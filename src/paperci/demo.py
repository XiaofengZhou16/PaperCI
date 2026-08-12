from __future__ import annotations

from pathlib import Path
from typing import Any

from paperci.project import ProjectDocument, empty_project

DEMO_ARTIFACTS = {
    "results/expression.csv": (
        "contrast,n_control,n_exposed,log2_fold_change,ci95_lower,ci95_upper,p_value\n"
        "exposed_minus_control,5,5,1.1,0.3,1.9,0.02\n"
    ),
    "results/motifs.tsv": (
        "motif\tenrichment_score\tadjusted_p_value\n"
        "candidate_transcription_factor\t2.4\t0.04\n"
    ),
}


def demo_document(path: Path) -> ProjectDocument:
    """Build a synthetic project that demonstrates a deliberate scientific gate failure."""
    data = empty_project("paperci-demo", "PaperCI synthetic demo")
    data["evidence"] = [_expression_evidence(), _motif_evidence()]
    data["claims"] = [_association_claim(), _mechanism_claim()]
    return ProjectDocument(path=path.resolve(), data=data)


def _expression_evidence() -> dict[str, Any]:
    return {
        "id": "E001",
        "kind": "quantitative_result",
        "statement": "Target expression was higher after exposure than in control cells.",
        "status": "draft",
        "source": {"uri": "results/expression.csv", "locator": "row=2"},
        "design": {
            "family": "experiment",
            "unit_of_analysis": "biological_sample",
            "groups": [{"id": "control", "n": 5}, {"id": "exposed", "n": 5}],
            "randomized": "unknown",
            "blinded": "unknown",
        },
        "result": {
            "outcome": "target expression",
            "contrast": "exposed minus control",
            "direction": "increase",
            "effect": {"value": 1.1, "unit": "log2_fold_change"},
            "uncertainty": {
                "kind": "confidence_interval",
                "level": 0.95,
                "lower": 0.3,
                "upper": 1.9,
            },
            "p_value": 0.02,
            "multiplicity": "not_reported",
        },
        "scope": {
            "system": "cultured primary cells",
            "context": "tested exposure protocol",
        },
    }


def _motif_evidence() -> dict[str, Any]:
    return {
        "id": "E002",
        "kind": "analysis_output",
        "statement": (
            "A candidate transcription-factor motif was enriched in accessible regions."
        ),
        "status": "draft",
        "source": {"uri": "results/motifs.tsv", "locator": "row=2"},
        "scope": {
            "system": "cultured primary cells",
            "context": "tested exposure protocol",
        },
    }


def _association_claim() -> dict[str, Any]:
    return {
        "id": "C001",
        "text": "Exposure is associated with higher target expression in the tested system.",
        "type": "association",
        "strength": "supports",
        "status": "candidate",
        "supports": ["E001"],
        "challenges": [],
        "assumptions": [],
        "alternatives": ["A technical or composition difference explains the result."],
        "scope": {
            "system": "cultured primary cells",
            "context": "tested exposure protocol",
        },
    }


def _mechanism_claim() -> dict[str, Any]:
    return {
        "id": "C002",
        "text": "The candidate transcription factor directly drives target expression.",
        "type": "mechanism",
        "strength": "demonstrates",
        "status": "candidate",
        "supports": ["E002"],
        "challenges": [],
        "assumptions": ["Motif enrichment reflects direct occupancy and functional regulation."],
        "alternatives": [
            "The motif marks a correlated chromatin state without direct regulation."
        ],
        "scope": {
            "system": "cultured primary cells",
            "context": "tested exposure protocol",
        },
    }
