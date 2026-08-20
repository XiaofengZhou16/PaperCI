from __future__ import annotations

import copy
from typing import Any

PROFILE_EXTENSION = "org.paperci.profile.v1"

MECHANISTIC_BIOLOGY_PROFILE: dict[str, Any] = {
    "name": "mechanistic-biology",
    "evidence_workflow": [
        {
            "role": "observation",
            "question": "What bounded phenotype or molecular state was observed?",
        },
        {
            "role": "intervention",
            "question": "What perturbation tests necessity, sufficiency, or causal direction?",
        },
        {
            "role": "target_engagement",
            "question": "Was the intended molecular target measurably engaged?",
        },
        {
            "role": "rescue",
            "question": "Does a rescue or reversal distinguish the proposed route from alternatives?",
        },
        {
            "role": "orthogonal",
            "question": "Does an independent assay support the same bounded step?",
        },
        {
            "role": "nested_units",
            "question": "Are cells, wells, organoids, or lesions nested within independent donors or animals?",
        },
    ],
    "claim_boundary": (
        "Record observations first. Treat mechanisms as candidates until linked evidence passes "
        "the applicable causal, mechanistic, scope, and unit-of-analysis checks."
    ),
}


def apply_profile(project: dict[str, Any], profile: str) -> None:
    if profile == "generic":
        return
    if profile != "mechanistic-biology":
        raise ValueError("--profile must be generic or mechanistic-biology.")
    extensions = project.setdefault("extensions", {})
    extensions[PROFILE_EXTENSION] = copy.deepcopy(MECHANISTIC_BIOLOGY_PROFILE)
    metadata = project.get("project")
    if isinstance(metadata, dict):
        metadata["description"] = (
            "Mechanistic-biology workspace with explicit observation, intervention, target-engagement, "
            "rescue, orthogonal-evidence, and nested-unit prompts."
        )
