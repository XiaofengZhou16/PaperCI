from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from paperci.engine import validate_project
from paperci.findings import Severity
from paperci.project import ProjectDocument


@dataclass(frozen=True, slots=True)
class StoryComparison:
    story_id: str
    title: str
    strategy: str
    gate_status: str
    errors: int
    warnings: int
    claim_coverage: float
    evidence_count: int
    challenged_claims: int
    challenge_disclosed: bool
    central_gaps: int


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    stories: tuple[StoryComparison, ...]
    recommended_for_review: str | None
    rationale: str


def compare_stories(document: ProjectDocument) -> ComparisonResult:
    claims = _index(document.data.get("claims"))
    findings = validate_project(document, scientific=True)
    by_target: dict[str, list[Any]] = {}
    for finding in findings:
        by_target.setdefault(finding.target, []).append(finding)
    rows: list[StoryComparison] = []
    for story in _dicts(document.data.get("stories")):
        if story.get("status") in {"superseded", "rejected"}:
            continue
        story_id = str(story.get("id", "?"))
        path_ids = list(dict.fromkeys(_strings(story.get("claim_path"))))
        path_claims = [claims[claim_id] for claim_id in path_ids if claim_id in claims]
        evidence_ids = {
            evidence_id for claim in path_claims for evidence_id in _strings(claim.get("supports"))
        }
        evidence_ids.update(
            evidence_id
            for figure in _dicts(story.get("figure_plan"))
            for evidence_id in _strings(figure.get("evidence_ids"))
        )
        related = list(by_target.get(story_id, []))
        for claim_id in path_ids:
            related.extend(by_target.get(claim_id, []))
        for evidence_id in evidence_ids:
            related.extend(by_target.get(evidence_id, []))
        errors = sum(finding.severity == Severity.ERROR for finding in related)
        warnings = sum(finding.severity == Severity.WARNING for finding in related)
        supported = [claim for claim in path_claims if _strings(claim.get("supports"))]
        challenged = [claim for claim in path_claims if _strings(claim.get("challenges"))]
        boundary = any(beat.get("role") == "boundary" for beat in _dicts(story.get("beats")))
        central_gaps = sum(gap.get("severity") == "central" for gap in _dicts(story.get("gaps")))
        extension = _proposal_extension(story)
        rows.append(
            StoryComparison(
                story_id=story_id,
                title=str(story.get("title", story_id)),
                strategy=str(extension.get("strategy", "manual")),
                gate_status="pass" if errors == 0 else "fail",
                errors=errors,
                warnings=warnings,
                claim_coverage=(len(supported) / len(path_claims)) if path_claims else 0.0,
                evidence_count=len(evidence_ids),
                challenged_claims=len(challenged),
                challenge_disclosed=boundary or not challenged,
                central_gaps=central_gaps,
            )
        )
    passing = [row for row in rows if row.gate_status == "pass"]
    if passing:
        recommended = min(
            passing,
            key=lambda row: (
                -row.claim_coverage,
                -int(row.challenge_disclosed),
                row.warnings,
                -row.evidence_count,
                row.story_id,
            ),
        )
        recommended_id = recommended.story_id
        rationale = (
            "Recommended only for the next human review. Among gate-passing arcs, ordering uses "
            "support-link coverage, challenge disclosure, fewer warnings, evidence count, and a "
            "stable ID tie-breaker. This is not a scientific-quality score."
        )
    else:
        recommended_id = None
        rationale = "No active story passes current hard gates; resolve error-level findings first."
    return ComparisonResult(tuple(rows), recommended_id, rationale)


def comparison_text(result: ComparisonResult) -> str:
    if not result.stories:
        return "No active story arcs to compare."
    header = (
        "Story  Gate  Errors  Warnings  Coverage  Evidence  Challenges  Disclosed  C.Gaps  Strategy"
    )
    lines = [header, "-" * len(header)]
    for row in result.stories:
        disclosure = (
            "yes"
            if row.challenged_claims and row.challenge_disclosed
            else "missing"
            if row.challenged_claims
            else "n/a"
        )
        lines.append(
            f"{row.story_id:<6} {row.gate_status:<5} {row.errors:>6} {row.warnings:>9} "
            f"{row.claim_coverage:>8.0%} {row.evidence_count:>9} {row.challenged_claims:>11} "
            f"{disclosure:>9} {row.central_gaps:>5}  {row.strategy}"
        )
    lines.extend(
        ["", f"Recommended for review: {result.recommended_for_review or 'none'}", result.rationale]
    )
    return "\n".join(lines)


def comparison_json(result: ComparisonResult) -> str:
    return json.dumps(
        {
            "recommended_for_review": result.recommended_for_review,
            "rationale": result.rationale,
            "stories": [asdict(row) for row in result.stories],
        },
        indent=2,
        ensure_ascii=False,
    )


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _index(value: Any) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in _dicts(value) if "id" in item}


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _proposal_extension(story: dict[str, Any]) -> dict[str, Any]:
    extensions = story.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    value = extensions.get("org.paperci.proposal.v1")
    return value if isinstance(value, dict) else {}
