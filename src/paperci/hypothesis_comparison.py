from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from paperci.engine import validate_project
from paperci.findings import Severity
from paperci.project import ProjectDocument


@dataclass(frozen=True, slots=True)
class HypothesisComparison:
    hypothesis_id: str
    strategy: str
    evidence_distance: str
    novelty: str
    conceptual_advance: str
    explanatory_breadth: str
    cross_scale_reach: str
    discriminating_power: str
    testability: str
    feasibility: str
    gate_status: str


@dataclass(frozen=True, slots=True)
class HypothesisComparisonResult:
    hypotheses: tuple[HypothesisComparison, ...]
    priority_for_review: str | None
    rationale: str


def compare_hypotheses(document: ProjectDocument) -> HypothesisComparisonResult:
    findings = validate_project(document, scientific=True)
    errors_by_target: dict[str, int] = {}
    for finding in findings:
        if finding.severity == Severity.ERROR:
            errors_by_target[finding.target] = errors_by_target.get(finding.target, 0) + 1
    rows: list[HypothesisComparison] = []
    for item in _dicts(document.data.get("hypotheses")):
        if item.get("status") in {"rejected", "superseded"}:
            continue
        item_id = str(item.get("id", "?"))
        profile = item.get("ambition_profile")
        profile = profile if isinstance(profile, dict) else {}
        novelty = item.get("novelty")
        novelty = novelty if isinstance(novelty, dict) else {}
        rows.append(
            HypothesisComparison(
                hypothesis_id=item_id,
                strategy=str(item.get("strategy", "?")),
                evidence_distance=str(item.get("evidence_distance", "unknown")),
                novelty=str(novelty.get("status", "unchecked")),
                conceptual_advance=_level(profile, "conceptual_advance"),
                explanatory_breadth=_level(profile, "explanatory_breadth"),
                cross_scale_reach=_level(profile, "cross_scale_reach"),
                discriminating_power=_level(profile, "discriminating_power"),
                testability=_level(profile, "testability"),
                feasibility=_level(profile, "feasibility"),
                gate_status="pass" if errors_by_target.get(item_id, 0) == 0 else "fail",
            )
        )
    passing = [row for row in rows if row.gate_status == "pass"]
    if passing:
        priority = min(
            passing,
            key=lambda row: (
                -_rank(row.discriminating_power),
                -_rank(row.testability),
                _distance(row.evidence_distance),
                -_rank(row.feasibility),
                row.hypothesis_id,
            ),
        )
        priority_id = priority.hypothesis_id
        rationale = (
            "Priority is only for the next human review. Ordering uses discriminating power, "
            "testability, evidence distance, feasibility, and a stable ID tie-breaker. It is not "
            "a journal-fit score, impact score, novelty decision, or publication forecast."
        )
    else:
        priority_id = None
        rationale = "No active hypothesis passes structural and hypothesis hard gates."
    return HypothesisComparisonResult(tuple(rows), priority_id, rationale)


def hypothesis_comparison_text(result: HypothesisComparisonResult) -> str:
    if not result.hypotheses:
        return "No active frontier hypotheses to compare."
    header = "Hyp.  Gate  Distance      Novelty    Advance  Breadth  Scale    Discrim.  Testable  Feasible  Strategy"
    lines = [header, "-" * len(header)]
    for row in result.hypotheses:
        lines.append(
            f"{row.hypothesis_id:<6} {row.gate_status:<5} {row.evidence_distance:<13} "
            f"{row.novelty:<10} {row.conceptual_advance:<8} {row.explanatory_breadth:<8} "
            f"{row.cross_scale_reach:<8} {row.discriminating_power:<9} {row.testability:<9} "
            f"{row.feasibility:<9} {row.strategy}"
        )
    lines.extend(
        ["", f"Priority for human review: {result.priority_for_review or 'none'}", result.rationale]
    )
    return "\n".join(lines)


def hypothesis_comparison_json(result: HypothesisComparisonResult) -> str:
    return json.dumps(
        {
            "priority_for_review": result.priority_for_review,
            "rationale": result.rationale,
            "hypotheses": [asdict(row) for row in result.hypotheses],
        },
        indent=2,
        ensure_ascii=False,
    )


def _level(profile: dict[str, Any], key: str) -> str:
    value = profile.get(key)
    return str(value.get("level", "unknown")) if isinstance(value, dict) else "unknown"


def _rank(value: str) -> int:
    return {"unknown": 0, "low": 1, "medium": 2, "high": 3}.get(value, 0)


def _distance(value: str) -> int:
    return {"near": 0, "intermediate": 1, "far": 2, "unknown": 3}.get(value, 3)


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
