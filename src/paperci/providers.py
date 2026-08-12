from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from paperci.findings import Finding, Severity

BUILTIN_PROVIDER_ID = "paperci.builtin.deterministic"
BUILTIN_PROVIDER_VERSION = "2"
DEFAULT_STRATEGIES = (
    "evidence-conservative",
    "high-risk-hypothesis",
    "minimum-gap",
)

CLAIM_BURDEN = {
    "descriptive": 0,
    "difference": 1,
    "null": 1,
    "resource": 1,
    "association": 2,
    "temporal": 3,
    "predictive": 3,
    "generalization": 4,
    "causal_effect": 5,
    "mediation": 6,
    "mechanism": 7,
}


@dataclass(frozen=True, slots=True)
class ProposalContext:
    run_id: str
    story_ids: tuple[str, ...]
    evidence: dict[str, dict[str, Any]]
    claims: tuple[dict[str, Any], ...]
    findings: tuple[Finding, ...]
    strategies: tuple[str, ...]
    central_claim: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderResult:
    stories: tuple[dict[str, Any], ...]
    notes: tuple[str, ...] = ()


class StoryProvider(Protocol):
    provider_id: str
    provider_version: str
    provider_kind: str

    def propose(self, context: ProposalContext) -> ProviderResult: ...


class DeterministicStoryProvider:
    """A safe baseline that reorganizes existing records and never invents evidence."""

    provider_id = BUILTIN_PROVIDER_ID
    provider_version = BUILTIN_PROVIDER_VERSION
    provider_kind = "software"

    def propose(self, context: ProposalContext) -> ProviderResult:
        claims = list(context.claims)
        claim_by_id = {str(claim["id"]): claim for claim in claims}
        claim_ids = set(claim_by_id)
        error_rules = _claim_rules(context.findings, Severity.ERROR, claim_ids)
        warning_rules = _claim_rules(context.findings, Severity.WARNING, claim_ids)
        eligible = [
            claim
            for claim in claims
            if claim.get("status") not in {"prohibited", "superseded"}
            and _string_list(claim.get("supports"))
        ]
        if not eligible:
            return ProviderResult((), ("No supported candidate claims are available.",))
        eligible_ids = {str(claim["id"]) for claim in eligible}

        def path_for(claim: dict[str, Any]) -> list[dict[str, Any]]:
            return _dependency_path(claim, claim_by_id, eligible_ids)

        if context.central_claim:
            requested = claim_by_id.get(context.central_claim)
            if requested is None or requested not in eligible:
                return ProviderResult(
                    (),
                    (
                        f"Requested central claim {context.central_claim} is not an eligible supported claim.",
                    ),
                )
            conservative = requested
        else:
            passing = [
                claim
                for claim in eligible
                if all(str(item["id"]) not in error_rules for item in path_for(claim))
            ]
            conservative = max(
                passing or eligible,
                key=lambda claim: _conservative_key(claim, len(path_for(claim))),
            )

        risky_candidates = [claim for claim in eligible if claim is not conservative]
        risky = max(risky_candidates or eligible, key=lambda claim: _risk_key(claim, error_rules))
        next_candidates = [claim for claim in eligible if claim is not conservative]
        next_claim = (
            min(
                next_candidates,
                key=lambda claim: _gap_key(claim, error_rules, warning_rules),
            )
            if next_candidates
            else None
        )

        selections: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {
            "evidence-conservative": (conservative, path_for(conservative)),
        }
        if risky is not conservative:
            selections["high-risk-hypothesis"] = (
                risky,
                _unique_claims([*path_for(conservative), *path_for(risky)]),
            )
        if next_claim is not None:
            selections["minimum-gap"] = (
                conservative,
                _unique_claims([*path_for(conservative), *path_for(next_claim)]),
            )

        stories: list[dict[str, Any]] = []
        notes: list[str] = []
        for strategy, story_id in zip(context.strategies, context.story_ids, strict=False):
            selection = selections.get(strategy)
            if selection is None:
                notes.append(
                    f"Strategy {strategy} was skipped because it would duplicate another arc."
                )
                continue
            central, path = selection
            stories.append(
                _build_story(
                    story_id=story_id,
                    run_id=context.run_id,
                    provider_id=self.provider_id,
                    provider_version=self.provider_version,
                    strategy=strategy,
                    central=central,
                    path=_unique_claims(path),
                    evidence=context.evidence,
                    error_rules=error_rules,
                    warning_rules=warning_rules,
                    all_eligible=eligible,
                )
            )
        return ProviderResult(tuple(stories), tuple(notes))


def get_provider(provider_id: str) -> StoryProvider:
    aliases = {"builtin", "deterministic", BUILTIN_PROVIDER_ID}
    if provider_id in aliases:
        return DeterministicStoryProvider()
    raise ValueError(
        f"Unknown provider {provider_id!r}. Available provider: {BUILTIN_PROVIDER_ID} (alias: builtin)."
    )


def _claim_rules(
    findings: tuple[Finding, ...],
    severity: Severity,
    claim_ids: set[str],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for finding in findings:
        if finding.severity == severity and finding.target in claim_ids:
            result.setdefault(finding.target, []).append(finding.rule_id)
    return result


def _conservative_key(claim: dict[str, Any], dependency_span: int) -> tuple[int, int, int, str]:
    return (
        dependency_span,
        len(_string_list(claim.get("supports"))),
        -CLAIM_BURDEN.get(str(claim.get("type")), -1),
        str(claim.get("id")),
    )


def _risk_key(
    claim: dict[str, Any],
    error_rules: dict[str, list[str]],
) -> tuple[int, int, int, str]:
    claim_id = str(claim.get("id"))
    return (
        int(bool(error_rules.get(claim_id))),
        CLAIM_BURDEN.get(str(claim.get("type")), -1),
        len(_string_list(claim.get("supports"))),
        claim_id,
    )


def _gap_key(
    claim: dict[str, Any],
    error_rules: dict[str, list[str]],
    warning_rules: dict[str, list[str]],
) -> tuple[int, int, int, str]:
    claim_id = str(claim.get("id"))
    return (
        len(error_rules.get(claim_id, [])),
        len(warning_rules.get(claim_id, [])),
        CLAIM_BURDEN.get(str(claim.get("type")), -1),
        claim_id,
    )


def _build_story(
    *,
    story_id: str,
    run_id: str,
    provider_id: str,
    provider_version: str,
    strategy: str,
    central: dict[str, Any],
    path: list[dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    error_rules: dict[str, list[str]],
    warning_rules: dict[str, list[str]],
    all_eligible: list[dict[str, Any]],
) -> dict[str, Any]:
    central_id = str(central["id"])
    titles = {
        "evidence-conservative": f"Evidence-conservative: {central['text']}",
        "high-risk-hypothesis": f"High-risk hypothesis: {central['text']}",
        "minimum-gap": f"Minimum-gap path anchored on {central_id}",
    }
    questions = {
        "evidence-conservative": "What conclusion survives the current evidence boundaries?",
        "high-risk-hypothesis": f"Could the current results support the higher-burden claim {central_id}?",
        "minimum-gap": "Which smallest unresolved claim boundary would most strengthen the story?",
    }
    claim_path = [str(claim["id"]) for claim in path]
    beats = [
        {"role": _beat_role(str(claim.get("type"))), "claim_ids": [str(claim["id"])]}
        for claim in path
    ]
    boundary_in_path = [
        claim
        for claim in path
        if error_rules.get(str(claim["id"])) or _string_list(claim.get("challenges"))
    ]
    if boundary_in_path:
        beats.append(
            {"role": "boundary", "claim_ids": [str(claim["id"]) for claim in boundary_in_path]}
        )
    figure_plan = []
    for number, claim in enumerate(path, start=1):
        claim_id = str(claim["id"])
        support_ids = [
            evidence_id
            for evidence_id in _string_list(claim.get("supports"))
            if evidence_id in evidence
        ]
        figure_plan.append(
            {
                "figure": number,
                "question": f"What evidence bears on claim {claim_id}?",
                "evidence_ids": support_ids,
                "claim_ids": [claim_id],
            }
        )
    gaps: list[dict[str, Any]] = []
    gap_claims = list(boundary_in_path)
    if strategy == "evidence-conservative":
        excluded = [
            claim
            for claim in all_eligible
            if claim not in path and error_rules.get(str(claim["id"]))
        ]
        if excluded:
            gap_claims.append(max(excluded, key=lambda claim: _risk_key(claim, error_rules)))
    if strategy == "minimum-gap" and len(path) > 1:
        last_id = str(path[-1]["id"])
        if warning_rules.get(last_id):
            gap_claims.append(path[-1])
    for index, claim in enumerate(_unique_claims(gap_claims), start=1):
        claim_id = str(claim["id"])
        rules = sorted(set(error_rules.get(claim_id, []) + warning_rules.get(claim_id, [])))
        suffix = f" Current gates: {', '.join(rules)}." if rules else ""
        gap: dict[str, Any] = {
            "id": f"G-{run_id}-{story_id}-{index:03d}",
            "question": f"What additional evidence would make claim {claim_id} supportable?{suffix}",
            "blocks": [claim_id],
            "severity": "central" if claim_id == central_id else "major",
        }
        alternatives = _string_list(claim.get("alternatives"))
        if alternatives:
            gap["competing_explanations"] = alternatives
        gaps.append(gap)
    return {
        "id": story_id,
        "title": titles[strategy],
        "profile": "general_scientific_story",
        "central_question": questions[strategy],
        "central_claim": central_id,
        "claim_path": claim_path,
        "beats": beats,
        "figure_plan": figure_plan,
        "gaps": gaps,
        "status": "candidate",
        "extensions": {
            "org.paperci.proposal.v1": {
                "generated": True,
                "run_id": run_id,
                "provider_id": provider_id,
                "provider_version": provider_version,
                "strategy": strategy,
            }
        },
    }


def _beat_role(claim_type: str) -> str:
    if claim_type in {"mechanism", "mediation"}:
        return "mechanism"
    if claim_type in {"causal_effect"}:
        return "explanation"
    if claim_type in {"temporal", "predictive", "generalization"}:
        return "implication"
    if claim_type == "null":
        return "boundary"
    return "discovery"


def _unique_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim["id"])
        if claim_id not in seen:
            seen.add(claim_id)
            result.append(claim)
    return result


def _dependency_path(
    claim: dict[str, Any],
    claim_by_id: dict[str, dict[str, Any]],
    eligible_ids: set[str],
) -> list[dict[str, Any]]:
    """Return eligible prerequisites before the selected claim in stable topological order."""
    ordered: list[dict[str, Any]] = []
    visited: set[str] = set()

    def visit(item: dict[str, Any]) -> None:
        item_id = str(item["id"])
        if item_id in visited:
            return
        visited.add(item_id)
        for dependency_id in _string_list(item.get("depends_on")):
            dependency = claim_by_id.get(dependency_id)
            if dependency is not None and dependency_id in eligible_ids:
                visit(dependency)
        ordered.append(item)

    visit(claim)
    return ordered


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
