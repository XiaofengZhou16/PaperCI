from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from paperci.engine import validate_project
from paperci.errors import HypothesisError
from paperci.findings import Severity
from paperci.project import ProjectDocument, next_identifier

HYPOTHESIS_PROVIDER_ID = "paperci.builtin.frontier-hypothesis"
HYPOTHESIS_PROVIDER_VERSION = "2"
HYPOTHESIS_STRATEGIES = (
    "mechanistic-deepening",
    "cross-scale-bridge",
    "paradigm-challenge",
)


@dataclass(frozen=True, slots=True)
class HypothesisContext:
    run_id: str
    hypothesis_ids: tuple[str, ...]
    evidence: dict[str, dict[str, Any]]
    eligible_claims: tuple[dict[str, Any], ...]
    seed_claim: dict[str, Any]
    strategies: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HypothesisProviderResult:
    hypotheses: tuple[dict[str, Any], ...]
    notes: tuple[str, ...] = ()


class HypothesisProvider(Protocol):
    provider_id: str
    provider_version: str
    provider_kind: str

    def generate(self, context: HypothesisContext) -> HypothesisProviderResult: ...


class DeterministicHypothesisProvider:
    """Build transparent scaffolds and never claim literature novelty."""

    provider_id = HYPOTHESIS_PROVIDER_ID
    provider_version = HYPOTHESIS_PROVIDER_VERSION
    provider_kind = "software"

    def generate(self, context: HypothesisContext) -> HypothesisProviderResult:
        hypotheses = tuple(
            _build_hypothesis(
                hypothesis_id=hypothesis_id,
                strategy=strategy,
                seed=context.seed_claim,
                eligible=list(context.eligible_claims),
                evidence=context.evidence,
            )
            for hypothesis_id, strategy in zip(
                context.hypothesis_ids, context.strategies, strict=True
            )
        )
        return HypothesisProviderResult(hypotheses)


def get_hypothesis_provider(provider_id: str) -> HypothesisProvider:
    aliases = {"builtin", "deterministic", HYPOTHESIS_PROVIDER_ID}
    if provider_id in aliases:
        return DeterministicHypothesisProvider()
    raise ValueError(
        f"Unknown hypothesis provider {provider_id!r}. Available provider: "
        f"{HYPOTHESIS_PROVIDER_ID} (alias: builtin)."
    )


@dataclass(slots=True)
class HypothesisOutcome:
    document: ProjectDocument
    run: dict[str, Any]
    hypotheses: list[dict[str, Any]]
    notes: list[str]
    reused: bool = False


def hypothesize(
    document: ProjectDocument,
    provider: HypothesisProvider | None = None,
    *,
    count: int = 3,
    seed_claim: str | None = None,
    force: bool = False,
) -> HypothesisOutcome:
    """Generate deterministic hypothesis scaffolds without claiming novelty or mechanism proof."""
    if not 1 <= count <= len(HYPOTHESIS_STRATEGIES):
        raise HypothesisError(f"--count must be between 1 and {len(HYPOTHESIS_STRATEGIES)}.")
    provider = provider or DeterministicHypothesisProvider()
    structural = validate_project(document, scientific=False)
    errors = [finding for finding in structural if finding.severity == Severity.ERROR]
    if errors:
        rules = ", ".join(sorted({finding.rule_id for finding in errors}))
        raise HypothesisError(
            f"Project has structural errors ({rules}); run paperci validate first."
        )

    working = ProjectDocument(path=document.path, data=copy.deepcopy(document.data))
    working.data["spec_version"] = "0.4"
    hypotheses = working.data.setdefault("hypotheses", [])
    runs = working.data.setdefault("runs", [])
    if not isinstance(hypotheses, list) or not isinstance(runs, list):
        raise HypothesisError("Project fields 'hypotheses' and 'runs' must be lists.")
    evidence = _index(working.data.get("evidence"))
    claims = _index(working.data.get("claims"))
    eligible = [
        claim
        for claim in claims.values()
        if claim.get("status") not in {"prohibited", "superseded"}
        and _strings(claim.get("supports"))
    ]
    if not eligible:
        raise HypothesisError(
            "No supported active claims exist. Add evidence and a supported candidate claim first."
        )
    if seed_claim is not None:
        seed = claims.get(seed_claim)
        if seed not in eligible:
            raise HypothesisError(f"Seed claim is not an eligible supported claim: {seed_claim}")
    else:
        seed = max(eligible, key=_seed_key)

    strategies = HYPOTHESIS_STRATEGIES[:count]
    parameters = {
        "count": count,
        "strategies": list(strategies),
        "seed_claim": str(seed["id"]),
        "literature_mode": "offline",
    }
    input_manifest = {
        "evidence_ids": sorted(evidence),
        "claim_ids": sorted(claims),
    }
    input_hash = hypothesis_input_hash(working, provider, parameters)
    if not force:
        reusable = _find_reusable_run(
            runs,
            hypotheses,
            provider.provider_id,
            provider.provider_version,
            input_hash,
        )
        if reusable is not None:
            output_ids = set(_strings(reusable.get("output_ids")))
            stored = [item for item in _dicts(hypotheses) if str(item.get("id")) in output_ids]
            return HypothesisOutcome(working, reusable, stored, [], reused=True)

    for item in _dicts(hypotheses):
        extension = _hypothesis_extension(item)
        if extension.get("generated") is True and item.get("status") == "speculative":
            item["status"] = "superseded"

    run_id = next_identifier(runs, "RUN")
    hypothesis_ids = _next_identifiers(hypotheses, "H", count)
    context = HypothesisContext(
        run_id=run_id,
        hypothesis_ids=tuple(hypothesis_ids),
        evidence=copy.deepcopy(evidence),
        eligible_claims=tuple(copy.deepcopy(eligible)),
        seed_claim=copy.deepcopy(seed),
        strategies=tuple(strategies),
    )
    result = provider.generate(context)
    if not result.hypotheses:
        detail = (
            " ".join(str(note) for note in result.notes) or "The provider returned no hypotheses."
        )
        raise HypothesisError(detail)
    if any(not isinstance(item, dict) for item in result.hypotheses):
        raise HypothesisError("The provider returned a non-object hypothesis.")
    generated = [copy.deepcopy(item) for item in result.hypotheses]
    output_ids = [str(item.get("id")) for item in generated]
    if (
        len(output_ids) != len(set(output_ids))
        or set(output_ids) != set(hypothesis_ids)
        or any(item.get("id") is None for item in generated)
    ):
        raise HypothesisError(
            "The provider returned duplicate, missing, or unallocated hypothesis IDs."
        )
    for item in generated:
        item["status"] = "speculative"
        extensions = item.setdefault("extensions", {})
        if not isinstance(extensions, dict):
            raise HypothesisError("The provider returned invalid hypothesis extensions.")
        extensions["org.paperci.hypothesis.v1"] = {
            "generated": True,
            "run_id": run_id,
            "provider_id": provider.provider_id,
            "provider_version": provider.provider_version,
        }
    hypotheses.extend(generated)
    run = {
        "id": run_id,
        "kind": "hypothesis_generation",
        "provider": {
            "id": provider.provider_id,
            "version": provider.provider_version,
            "kind": provider.provider_kind,
        },
        "input_hash": input_hash,
        "input_manifest": input_manifest,
        "parameters": parameters,
        "output_ids": output_ids,
        "status": "completed",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    runs.append(run)
    boundary_errors = [
        finding
        for finding in validate_project(working, scientific=True)
        if finding.severity == Severity.ERROR
        and finding.rule_id in {"PCI-SCHEMA-001", "PCI-REF-001", "PCI-AI-001", "PCI-HYP-005"}
    ]
    if boundary_errors:
        rules = ", ".join(sorted({finding.rule_id for finding in boundary_errors}))
        detail = "; ".join(
            f"{finding.target}: {finding.message}" for finding in boundary_errors[:3]
        )
        raise HypothesisError(
            f"Hypothesis output violates the project boundary ({rules}): {detail}"
        )
    notes = list(result.notes) + [
        "Novelty is unchecked because this run records literature_mode=offline.",
        "Generated records are speculative hypotheses, not supported claims or publication forecasts.",
    ]
    return HypothesisOutcome(working, run, generated, notes)


def hypothesis_text(outcome: HypothesisOutcome) -> str:
    state = "reused existing" if outcome.reused else "generated new"
    provider = outcome.run.get("provider")
    provider = provider if isinstance(provider, dict) else {}
    lines = [
        f"Hypothesis run {outcome.run.get('id', '?')} ({state})",
        f"Provider: {provider.get('id', '?')}@{provider.get('version', '?')}",
        f"Input hash: {outcome.run.get('input_hash', '?')}",
        "",
    ]
    for item in outcome.hypotheses:
        profile = item.get("ambition_profile")
        profile = profile if isinstance(profile, dict) else {}
        levels = ", ".join(
            f"{name}={value.get('level', '?')}"
            for name, value in profile.items()
            if isinstance(value, dict)
        )
        lines.extend(
            [
                f"{item.get('id', '?')}  {item.get('statement', '?')}",
                f"  Strategy: {item.get('strategy', '?')}",
                f"  Evidence distance: {item.get('evidence_distance', '?')}",
                f"  Novelty: {_nested(item, 'novelty', 'status')}",
                f"  Ambition profile: {levels}",
                f"  Decisive tests: {len(_dicts(item.get('decisive_tests')))}",
            ]
        )
    if outcome.notes:
        lines.extend(["", "Boundaries:"])
        lines.extend(f"- {note}" for note in outcome.notes)
    lines.extend(
        [
            "",
            "These are research directions for human review, not claims supported by current evidence.",
        ]
    )
    return "\n".join(lines)


def hypothesis_json(outcome: HypothesisOutcome, *, dry_run: bool = False) -> str:
    return json.dumps(
        {
            "dry_run": dry_run,
            "reused": outcome.reused,
            "run": outcome.run,
            "hypotheses": outcome.hypotheses,
            "notes": outcome.notes,
        },
        indent=2,
        ensure_ascii=False,
    )


def hypothesis_input_hash(
    document: ProjectDocument,
    provider: HypothesisProvider,
    parameters: dict[str, Any],
) -> str:
    payload = {
        "spec_version": document.data.get("spec_version"),
        "project_id": document.project_id,
        "evidence": _sorted_records(document.data.get("evidence")),
        "claims": _sorted_records(document.data.get("claims")),
        "provider": {"id": provider.provider_id, "version": provider.provider_version},
        "parameters": parameters,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_hypothesis(
    *,
    hypothesis_id: str,
    strategy: str,
    seed: dict[str, Any],
    eligible: list[dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    seed_id = str(seed["id"])
    anchor_claims = [seed_id]
    eligible_by_id = {str(item["id"]): item for item in eligible}
    related = _claim_dependencies(seed, eligible_by_id)
    companion = _strategy_companion(strategy, seed, related, eligible, evidence)
    if strategy in {"cross-scale-bridge", "paradigm-challenge"} and companion is not None:
        anchor_claims.append(str(companion["id"]))
    evidence_ids = list(
        dict.fromkeys(
            evidence_id
            for claim_id in anchor_claims
            for evidence_id in _strings(_claim_by_id(eligible, claim_id).get("supports"))
            if evidence_id in evidence
        )
    )
    alternatives = list(dict.fromkeys(_strings(seed.get("alternatives"))))
    if not alternatives:
        alternatives = ["The observed pattern reflects a technical or compositional difference."]
    seed_text = str(seed.get("text", seed_id))
    companion_text = (
        str(companion.get("text", companion.get("id"))) if companion is not None else ""
    )
    alternative = _strategy_alternative(
        strategy, alternatives, companion, evidence, fallback=alternatives[0]
    )
    alternatives = list(dict.fromkeys([*alternatives, alternative]))
    focus_id = (
        str(companion.get("id"))
        if strategy == "paradigm-challenge" and companion is not None
        else seed_id
    )
    focus_text = (
        companion_text if strategy == "paradigm-challenge" and companion is not None else seed_text
    )
    statements = {
        "mechanistic-deepening": (
            f"The mechanism proposed in {seed_id} ('{seed_text}') is a testable candidate: "
            "target-engaged perturbation and rescue should change the anchored outcome, although "
            "the current evidence does not establish that mechanism."
        ),
        "cross-scale-bridge": (
            f"The candidate process in {seed_id} ('{seed_text}') may connect to "
            f"{str(companion.get('id')) if companion is not None else 'another scale'} "
            f"('{companion_text}') and thereby explain a broader phenotype."
        ),
        "paradigm-challenge": (
            f"The competing explanation ('{alternative}') may account for the evidence anchored "
            f"by {focus_id} better than its current leading interpretation ('{focus_text}')."
        ),
    }
    leading_model = f"leading interpretation: {focus_text}"
    competing_model = f"competing explanation: {alternative}"
    proposed = statements[strategy]
    decisive_test = {
        "design": _test_design(
            strategy,
            seed_id,
            seed_text,
            str(companion.get("id")) if companion is not None else None,
            companion_text,
            alternative,
            focus_id,
            focus_text,
        ),
        "distinguishes": [leading_model, competing_model],
        "expected_outcomes": [
            {
                "model": leading_model,
                "expected": (
                    f"Target-engaged perturbation of '{focus_text}' changes the anchored outcome "
                    "in the predicted direction and an orthogonal rescue restores it."
                ),
            },
            {
                "model": competing_model,
                "expected": (
                    f"The anchored outcome follows '{alternative}' and is not selectively restored "
                    f"by rescue of the process described in {seed_id}."
                ),
            },
        ],
        "falsifier": (
            f"A well-powered, target-engaged perturbation of the process in {seed_id} leaves the "
            f"anchored outcome unchanged while '{alternative}' remains viable."
        ),
        "feasibility": "medium" if strategy == "mechanistic-deepening" else "unknown",
        "expected_information_gain": "high",
        "dependencies": [
            "validated perturbation or intervention",
            "matched negative and rescue controls",
            "pre-specified quantitative readout",
        ],
    }
    profile = _ambition_profile(strategy, len(anchor_claims))
    return {
        "id": hypothesis_id,
        "statement": proposed,
        "strategy": strategy,
        "status": "speculative",
        "seed_claim": seed_id,
        "anchor_claims": anchor_claims,
        "evidence_ids": evidence_ids,
        "inference_steps": [
            {
                "kind": "observed",
                "statement": " ".join(
                    str(evidence[evidence_id].get("statement", evidence_id))
                    for evidence_id in evidence_ids
                ),
                "grounded_in": evidence_ids,
            },
            {
                "kind": "inferred",
                "statement": f"The claim register proposes: {seed_text}",
                "grounded_in": anchor_claims,
            },
            {
                "kind": "speculative",
                "statement": proposed,
                "grounded_in": anchor_claims,
            },
        ],
        "alternatives": alternatives,
        "predictions": [
            f"Perturbing the process '{focus_text}' should alter the anchored outcome with target engagement.",
            f"A rescue specific to '{focus_text}' should reverse the perturbation-associated change.",
        ],
        "decisive_tests": [decisive_test],
        "evidence_upgrade_path": [
            "Replicate the anchored observation with explicit provenance and uncertainty.",
            "Demonstrate temporal ordering and direct or intervention-based engagement.",
            "Use rescue and orthogonal validation to distinguish the leading alternative.",
            "Test scope in an independent biological context before generalization.",
        ],
        "evidence_distance": {
            "mechanistic-deepening": "near",
            "cross-scale-bridge": "far",
            "paradigm-challenge": "intermediate",
        }[strategy],
        "ambition_profile": profile,
        "novelty": {
            "status": "unchecked",
            "note": (
                "No literature search was performed. This record must not be described as novel, "
                "first, unprecedented, or journal-ready."
            ),
            "literature_sources": [],
        },
        "figure_plan": [
            {
                "figure": 1,
                "role": "evidence_anchor",
                "question": "Which observed results anchor this hypothesis?",
                "evidence_ids": evidence_ids,
            },
            {
                "figure": 2,
                "role": "mechanism_model",
                "question": "Which unverified links connect the evidence to the proposed mechanism?",
                "evidence_ids": [],
            },
            {
                "figure": 3,
                "role": "discriminating_test",
                "question": "Which result would distinguish the proposed and competing mechanisms?",
                "evidence_ids": [],
            },
        ],
    }


def _ambition_profile(strategy: str, anchor_count: int) -> dict[str, dict[str, str]]:
    breadth = "medium" if anchor_count > 1 else "low"
    cross_scale = "high" if strategy == "cross-scale-bridge" else "low"
    conceptual = "high" if strategy == "paradigm-challenge" else "medium"
    return {
        "conceptual_advance": {
            "level": conceptual,
            "basis": "Potential advance follows from the chosen strategy; novelty remains unchecked.",
        },
        "explanatory_breadth": {
            "level": breadth,
            "basis": f"The scaffold links {anchor_count} supported claim anchor(s).",
        },
        "cross_scale_reach": {
            "level": cross_scale,
            "basis": "Only the cross-scale strategy explicitly proposes a level-to-level bridge.",
        },
        "discriminating_power": {
            "level": "high",
            "basis": "The card requires competing models, expected outcomes, and a falsifier.",
        },
        "testability": {
            "level": "high",
            "basis": "The card specifies an intervention, rescue logic, and pre-specified readout.",
        },
        "feasibility": {
            "level": "medium" if strategy == "mechanistic-deepening" else "unknown",
            "basis": "Feasibility cannot be established without domain, model, resource, and timeline data.",
        },
    }


def _test_design(
    strategy: str,
    seed_id: str,
    seed_text: str,
    companion_id: str | None,
    companion_text: str,
    alternative: str,
    focus_id: str,
    focus_text: str,
) -> str:
    if strategy == "mechanistic-deepening":
        return (
            f"Perturb the process described by {seed_id} ('{seed_text}') with measured target "
            "engagement; perform an orthogonal rescue and quantify the pre-specified anchored outcome."
        )
    if strategy == "cross-scale-bridge":
        bridge = (
            f"{companion_id} ('{companion_text}')"
            if companion_id is not None
            else "a matched scale"
        )
        return (
            f"Test whether {seed_id} ('{seed_text}') depends on or propagates from {bridge}; "
            f"perturb each level separately and distinguish this bridge from '{alternative}' "
            "using matched readouts at both levels."
        )
    return (
        f"Intervene separately on the leading process in {focus_id} ('{focus_text}') and on the "
        f"competing process ('{alternative}'); include target engagement, rescue, and the same "
        f"pre-specified outcome for both arms while retaining {seed_id} as the upstream anchor."
    )


def _claim_dependencies(
    seed: dict[str, Any],
    claims: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    visited: set[str] = set()

    def visit(item: dict[str, Any]) -> None:
        for dependency_id in _strings(item.get("depends_on")):
            if dependency_id in visited or dependency_id not in claims:
                continue
            visited.add(dependency_id)
            dependency = claims[dependency_id]
            visit(dependency)
            ordered.append(dependency)

    visit(seed)
    return ordered


def _strategy_companion(
    strategy: str,
    seed: dict[str, Any],
    related: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if strategy == "cross-scale-bridge":
        persistent = next(
            (
                item
                for item in related
                if any(
                    marker in str(item.get("text", "")).casefold()
                    for marker in ("persist", "memory state", "chromatin state")
                )
            ),
            None,
        )
        if persistent is not None:
            return persistent
    if strategy == "paradigm-challenge":
        bounded = next(
            (item for item in reversed(related) if _outgrowth_boundary(item, evidence)),
            None,
        )
        if bounded is not None:
            return bounded
    direct = next(
        (
            item
            for dependency_id in _strings(seed.get("depends_on"))
            if (item := next((c for c in related if str(c.get("id")) == dependency_id), None))
            is not None
        ),
        None,
    )
    if direct is not None:
        return direct
    seed_id = str(seed.get("id"))
    return next((item for item in eligible if str(item.get("id")) != seed_id), None)


def _strategy_alternative(
    strategy: str,
    seed_alternatives: list[str],
    companion: dict[str, Any] | None,
    evidence: dict[str, dict[str, Any]],
    *,
    fallback: str,
) -> str:
    if strategy == "mechanistic-deepening":
        return seed_alternatives[-1]
    if strategy == "cross-scale-bridge" and companion is not None:
        alternatives = _strings(companion.get("alternatives"))
        if alternatives:
            return alternatives[0]
    if strategy == "paradigm-challenge" and companion is not None:
        if _outgrowth_boundary(companion, evidence):
            return "Prior exposure changes tumour-initiation frequency rather than post-initiation outgrowth."
        return seed_alternatives[-1]
    return fallback


def _outgrowth_boundary(claim: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> bool:
    claim_text = str(claim.get("text", "")).casefold()
    if not any(marker in claim_text for marker in ("outgrowth", "larger", "growth")):
        return False
    statements = " ".join(
        str(evidence[evidence_id].get("statement", "")).casefold()
        for evidence_id in _strings(claim.get("supports"))
        if evidence_id in evidence
    )
    return any(
        marker in statements
        for marker in (
            "did not have more macroscopic tumour",
            "did not have more macroscopic tumor",
            "no increase in tumour number",
            "no increase in tumor number",
        )
    )


def _seed_key(claim: dict[str, Any]) -> tuple[int, int, str]:
    burden = {
        "mechanism": 7,
        "mediation": 6,
        "causal_effect": 5,
        "generalization": 4,
        "temporal": 3,
        "predictive": 3,
        "association": 2,
        "difference": 1,
        "descriptive": 0,
    }
    return (
        burden.get(str(claim.get("type")), 0),
        len(_strings(claim.get("supports"))),
        str(claim.get("id")),
    )


def _find_reusable_run(
    runs: list[Any],
    hypotheses: list[Any],
    provider_id: str,
    provider_version: str,
    input_hash: str,
) -> dict[str, Any] | None:
    statuses = {str(item.get("id")): item.get("status") for item in _dicts(hypotheses)}
    for run in reversed(_dicts(runs)):
        provider = run.get("provider") if isinstance(run.get("provider"), dict) else {}
        outputs = _strings(run.get("output_ids"))
        if (
            run.get("kind") == "hypothesis_generation"
            and run.get("status") == "completed"
            and provider.get("id") == provider_id
            and provider.get("version") == provider_version
            and run.get("input_hash") == input_hash
            and outputs
            and all(output in statuses and statuses[output] != "superseded" for output in outputs)
        ):
            return run
    return None


def _next_identifiers(items: list[Any], prefix: str, count: int) -> list[str]:
    scratch = list(items)
    result: list[str] = []
    for _ in range(count):
        identifier = next_identifier(scratch, prefix)
        result.append(identifier)
        scratch.append({"id": identifier})
    return result


def _hypothesis_extension(item: dict[str, Any]) -> dict[str, Any]:
    extensions = item.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    value = extensions.get("org.paperci.hypothesis.v1")
    return value if isinstance(value, dict) else {}


def _claim_by_id(claims: list[dict[str, Any]], claim_id: str) -> dict[str, Any]:
    return next(item for item in claims if str(item.get("id")) == claim_id)


def _nested(item: dict[str, Any], first: str, second: str) -> str:
    value = item.get(first)
    return str(value.get(second, "?")) if isinstance(value, dict) else "?"


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _index(value: Any) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in _dicts(value) if "id" in item}


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _sorted_records(value: Any) -> list[dict[str, Any]]:
    return sorted(_dicts(value), key=lambda item: str(item.get("id", "")))
