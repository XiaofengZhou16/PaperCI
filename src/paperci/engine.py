from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

from paperci.findings import Finding, Severity, sort_findings
from paperci.project import ProjectDocument, load_schema

EFFECT_CLAIM_TYPES = {
    "difference",
    "association",
    "temporal",
    "predictive",
    "causal_effect",
    "mediation",
    "mechanism",
    "generalization",
}
CAUSAL_CLAIM_TYPES = {"causal_effect", "mediation"}
MECHANISTIC_ROLES = {
    "perturbation",
    "rescue",
    "direct_binding",
    "structural",
    "temporal_intervention",
    "causal_identification",
    "functional_perturbation",
}


def validate_project(document: ProjectDocument, *, scientific: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_schema_findings(document))
    index, duplicate_findings = _build_index(document)
    findings.extend(duplicate_findings)
    findings.extend(_reference_findings(document, index))
    findings.extend(_claim_dependency_findings(document, index))
    findings.extend(_provenance_findings(document))
    if scientific:
        findings.extend(_scientific_findings(document, index))
    return sort_findings(findings)


def _schema_findings(document: ProjectDocument) -> list[Finding]:
    validator = Draft202012Validator(load_schema(), format_checker=FormatChecker())
    results: list[Finding] = []
    for error in sorted(validator.iter_errors(document.data), key=lambda item: list(item.path)):
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        results.append(
            Finding(
                rule_id="PCI-SCHEMA-001",
                severity=Severity.ERROR,
                target=path or "/",
                path=path or "/",
                message=error.message,
                remediation="Edit the field to conform to a supported PaperCI spec version.",
            )
        )
    return results


def _records(document: ProjectDocument) -> Iterable[tuple[str, int, dict[str, Any]]]:
    for collection in ("evidence", "claims", "stories", "hypotheses", "reviews", "runs"):
        values = document.data.get(collection, [])
        if not isinstance(values, list):
            continue
        for offset, value in enumerate(values):
            if isinstance(value, dict):
                yield collection, offset, value


def _build_index(
    document: ProjectDocument,
) -> tuple[dict[str, tuple[str, dict[str, Any]]], list[Finding]]:
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    findings: list[Finding] = []
    for collection, offset, record in _records(document):
        record_id = record.get("id")
        if not isinstance(record_id, str):
            continue
        if record_id in index:
            first_collection, _ = index[record_id]
            findings.append(
                Finding(
                    rule_id="PCI-REF-001",
                    severity=Severity.ERROR,
                    target=record_id,
                    path=f"/{collection}/{offset}/id",
                    message=f"Duplicate ID; it already exists in {first_collection}.",
                    remediation="Assign a unique, stable ID and update references.",
                )
            )
        else:
            index[record_id] = (collection, record)
    return index, findings


def _reference_findings(
    document: ProjectDocument,
    index: dict[str, tuple[str, dict[str, Any]]],
) -> list[Finding]:
    findings: list[Finding] = []

    def require(
        owner: str,
        reference: Any,
        expected: set[str],
        path: str,
    ) -> None:
        if not isinstance(reference, str):
            return
        resolved = index.get(reference)
        if resolved is None:
            message = f"Reference {reference!r} does not exist."
        elif resolved[0] not in expected:
            message = (
                f"Reference {reference!r} resolves to {resolved[0]}, expected {sorted(expected)}."
            )
        else:
            return
        findings.append(
            Finding(
                rule_id="PCI-REF-001",
                severity=Severity.ERROR,
                target=owner,
                path=path,
                message=message,
                remediation="Restore the target record or update the reference.",
            )
        )

    claims = document.data.get("claims", [])
    if isinstance(claims, list):
        for offset, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            owner = str(claim.get("id", f"claims[{offset}]"))
            for field in ("supports", "challenges"):
                references = claim.get(field, [])
                if isinstance(references, list):
                    for position, reference in enumerate(references):
                        require(
                            owner, reference, {"evidence"}, f"/claims/{offset}/{field}/{position}"
                        )
            for position, reference in enumerate(_list(claim.get("depends_on"))):
                require(owner, reference, {"claims"}, f"/claims/{offset}/depends_on/{position}")

    stories = document.data.get("stories", [])
    if isinstance(stories, list):
        for offset, story in enumerate(stories):
            if not isinstance(story, dict):
                continue
            owner = str(story.get("id", f"stories[{offset}]"))
            require(
                owner, story.get("central_claim"), {"claims"}, f"/stories/{offset}/central_claim"
            )
            for position, reference in enumerate(_list(story.get("claim_path"))):
                require(owner, reference, {"claims"}, f"/stories/{offset}/claim_path/{position}")
            for beat_index, beat in enumerate(_dicts(story.get("beats"))):
                for position, reference in enumerate(_list(beat.get("claim_ids"))):
                    require(
                        owner,
                        reference,
                        {"claims"},
                        f"/stories/{offset}/beats/{beat_index}/claim_ids/{position}",
                    )
            for figure_index, figure in enumerate(_dicts(story.get("figure_plan"))):
                for position, reference in enumerate(_list(figure.get("evidence_ids"))):
                    require(
                        owner,
                        reference,
                        {"evidence"},
                        f"/stories/{offset}/figure_plan/{figure_index}/evidence_ids/{position}",
                    )
                for position, reference in enumerate(_list(figure.get("claim_ids"))):
                    require(
                        owner,
                        reference,
                        {"claims"},
                        f"/stories/{offset}/figure_plan/{figure_index}/claim_ids/{position}",
                    )
            for gap_index, gap in enumerate(_dicts(story.get("gaps"))):
                for position, reference in enumerate(_list(gap.get("blocks"))):
                    require(
                        owner,
                        reference,
                        {"claims"},
                        f"/stories/{offset}/gaps/{gap_index}/blocks/{position}",
                    )

    hypotheses = document.data.get("hypotheses", [])
    if isinstance(hypotheses, list):
        for offset, hypothesis in enumerate(hypotheses):
            if not isinstance(hypothesis, dict):
                continue
            owner = str(hypothesis.get("id", f"hypotheses[{offset}]"))
            require(
                owner,
                hypothesis.get("seed_claim"),
                {"claims"},
                f"/hypotheses/{offset}/seed_claim",
            )
            for field, expected in (
                ("anchor_claims", {"claims"}),
                ("evidence_ids", {"evidence"}),
            ):
                for position, reference in enumerate(_list(hypothesis.get(field))):
                    require(
                        owner,
                        reference,
                        expected,
                        f"/hypotheses/{offset}/{field}/{position}",
                    )
            for step_index, step in enumerate(_dicts(hypothesis.get("inference_steps"))):
                for position, reference in enumerate(_list(step.get("grounded_in"))):
                    require(
                        owner,
                        reference,
                        {"evidence", "claims"},
                        f"/hypotheses/{offset}/inference_steps/{step_index}/grounded_in/{position}",
                    )
            for figure_index, figure in enumerate(_dicts(hypothesis.get("figure_plan"))):
                for position, reference in enumerate(_list(figure.get("evidence_ids"))):
                    require(
                        owner,
                        reference,
                        {"evidence"},
                        f"/hypotheses/{offset}/figure_plan/{figure_index}/evidence_ids/{position}",
                    )
    reviews = document.data.get("reviews", [])
    if isinstance(reviews, list):
        for offset, review in enumerate(reviews):
            if not isinstance(review, dict):
                continue
            owner = str(review.get("id", f"reviews[{offset}]"))
            require(
                owner,
                review.get("target"),
                {"evidence", "claims", "stories", "hypotheses"},
                f"/reviews/{offset}/target",
            )

    runs = document.data.get("runs", [])
    if isinstance(runs, list):
        for offset, run in enumerate(runs):
            if not isinstance(run, dict):
                continue
            owner = str(run.get("id", f"runs[{offset}]"))
            manifest = run.get("input_manifest")
            if isinstance(manifest, dict):
                for position, reference in enumerate(_list(manifest.get("evidence_ids"))):
                    require(
                        owner,
                        reference,
                        {"evidence"},
                        f"/runs/{offset}/input_manifest/evidence_ids/{position}",
                    )
                for position, reference in enumerate(_list(manifest.get("claim_ids"))):
                    require(
                        owner,
                        reference,
                        {"claims"},
                        f"/runs/{offset}/input_manifest/claim_ids/{position}",
                    )
            expected_outputs = (
                {"hypotheses"} if run.get("kind") == "hypothesis_generation" else {"stories"}
            )
            for position, reference in enumerate(_list(run.get("output_ids"))):
                require(
                    owner,
                    reference,
                    expected_outputs,
                    f"/runs/{offset}/output_ids/{position}",
                )

    if isinstance(stories, list):
        for offset, story in enumerate(stories):
            if not isinstance(story, dict):
                continue
            extension = _proposal_extension(story)
            if extension.get("generated") is True:
                owner = str(story.get("id", f"stories[{offset}]"))
                run_id = extension.get("run_id")
                path = f"/stories/{offset}/extensions/org.paperci.proposal.v1/run_id"
                if isinstance(run_id, str):
                    require(owner, run_id, {"runs"}, path)
                else:
                    findings.append(
                        Finding(
                            rule_id="PCI-REF-001",
                            severity=Severity.ERROR,
                            target=owner,
                            path=path,
                            message="Generated story has no valid proposal-run reference.",
                            remediation="Restore its string run_id or regenerate the story.",
                        )
                    )
    if isinstance(hypotheses, list):
        for offset, hypothesis in enumerate(hypotheses):
            if not isinstance(hypothesis, dict):
                continue
            extension = _hypothesis_extension(hypothesis)
            if extension.get("generated") is True:
                owner = str(hypothesis.get("id", f"hypotheses[{offset}]"))
                run_id = extension.get("run_id")
                path = f"/hypotheses/{offset}/extensions/org.paperci.hypothesis.v1/run_id"
                if isinstance(run_id, str):
                    require(owner, run_id, {"runs"}, path)
                else:
                    findings.append(
                        Finding(
                            rule_id="PCI-REF-001",
                            severity=Severity.ERROR,
                            target=owner,
                            path=path,
                            message="Generated hypothesis has no valid generation-run reference.",
                            remediation="Restore its string run_id or regenerate the hypothesis.",
                        )
                    )
    return findings


def _claim_dependency_findings(
    document: ProjectDocument,
    index: dict[str, tuple[str, dict[str, Any]]],
) -> list[Finding]:
    claims = {
        record_id: record
        for record_id, (collection, record) in index.items()
        if collection == "claims"
    }
    graph = {
        claim_id: [
            dependency for dependency in _list(claim.get("depends_on")) if dependency in claims
        ]
        for claim_id, claim in claims.items()
    }
    state: dict[str, int] = {}
    stack: list[str] = []
    cycle_nodes: set[str] = set()

    def visit(claim_id: str) -> None:
        state[claim_id] = 1
        stack.append(claim_id)
        for dependency in graph.get(claim_id, []):
            dependency_state = state.get(dependency, 0)
            if dependency_state == 0:
                visit(dependency)
            elif dependency_state == 1:
                cycle_nodes.update(stack[stack.index(dependency) :])
        stack.pop()
        state[claim_id] = 2

    for claim_id in graph:
        if state.get(claim_id, 0) == 0:
            visit(claim_id)
    return [
        Finding(
            rule_id="PCI-CLAIM-001",
            severity=Severity.ERROR,
            target=claim_id,
            message="Claim dependency graph contains a cycle.",
            remediation="Remove or redirect a depends_on edge so evidence-to-claim reasoning is acyclic.",
        )
        for claim_id in sorted(cycle_nodes)
    ]


def _provenance_findings(document: ProjectDocument) -> list[Finding]:
    findings: list[Finding] = []
    reviews = _dicts(document.data.get("reviews"))
    human_verifications = {
        review.get("target")
        for review in reviews
        if review.get("decision") == "verify"
        and isinstance(review.get("actor"), dict)
        and review["actor"].get("kind") == "human"
    }
    evidence = document.data.get("evidence", [])
    if not isinstance(evidence, list):
        return findings
    for offset, item in enumerate(evidence):
        if not isinstance(item, dict):
            continue
        target = str(item.get("id", f"evidence[{offset}]"))
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        locator = source.get("locator")
        if item.get("kind") == "quantitative_result" and not locator:
            findings.append(
                Finding(
                    rule_id="PCI-PROV-001",
                    severity=Severity.ERROR if document.mode == "verified" else Severity.WARNING,
                    target=target,
                    path=f"/evidence/{offset}/source/locator",
                    message="Quantitative evidence has no precise source locator.",
                    remediation="Add a row, table, figure-panel, cell, or equivalent locator.",
                )
            )
        if item.get("status") == "verified" and target not in human_verifications:
            findings.append(
                Finding(
                    rule_id="PCI-PROV-002",
                    severity=Severity.ERROR,
                    target=target,
                    path=f"/evidence/{offset}/status",
                    message="Evidence is marked verified without a human verification event.",
                    remediation="Add a human verify ReviewEvent or return the evidence to reviewed.",
                )
            )
        uri = source.get("uri")
        if isinstance(uri, str) and _is_local_uri(uri):
            path = (document.root / uri).resolve()
            if not path.is_file():
                findings.append(
                    Finding(
                        rule_id="PCI-PROV-003",
                        severity=(
                            Severity.ERROR
                            if document.mode in {"verified", "connected"}
                            else Severity.WARNING
                        ),
                        target=target,
                        path=f"/evidence/{offset}/source/uri",
                        message=f"Local source does not exist: {uri}",
                        remediation="Restore the artifact or update the source URI.",
                    )
                )
            elif isinstance(source.get("sha256"), str):
                actual = _sha256(path)
                if actual.lower() != source["sha256"].lower():
                    findings.append(
                        Finding(
                            rule_id="PCI-PROV-004",
                            severity=Severity.ERROR,
                            target=target,
                            path=f"/evidence/{offset}/source/sha256",
                            message="Source SHA-256 does not match the current artifact.",
                            remediation="Investigate the change, then update evidence and hash deliberately.",
                        )
                    )
            if path.is_file() and isinstance(locator, str) and locator.startswith("row="):
                try:
                    row = int(locator.split("=", 1)[1])
                    line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
                    valid_row = 1 <= row <= line_count
                except (OSError, UnicodeDecodeError, ValueError):
                    valid_row = False
                if not valid_row:
                    findings.append(
                        Finding(
                            rule_id="PCI-PROV-005",
                            severity=Severity.ERROR,
                            target=target,
                            path=f"/evidence/{offset}/source/locator",
                            message=f"Row locator cannot be resolved in the local source: {locator}",
                            remediation="Correct the row locator or use another precise locator syntax.",
                        )
                    )
    return findings


def _scientific_findings(
    document: ProjectDocument,
    index: dict[str, tuple[str, dict[str, Any]]],
) -> list[Finding]:
    findings: list[Finding] = []
    evidence_index = {
        record_id: record
        for record_id, (collection, record) in index.items()
        if collection == "evidence"
    }
    claim_index = {
        record_id: record
        for record_id, (collection, record) in index.items()
        if collection == "claims"
    }
    story_index = {
        record_id: record
        for record_id, (collection, record) in index.items()
        if collection == "stories"
    }
    run_index = {
        record_id: record
        for record_id, (collection, record) in index.items()
        if collection == "runs"
    }
    evidence = document.data.get("evidence", [])
    if isinstance(evidence, list):
        for offset, item in enumerate(evidence):
            if not isinstance(item, dict) or item.get("kind") != "quantitative_result":
                continue
            target = str(item.get("id", f"evidence[{offset}]"))
            design = item.get("design") if isinstance(item.get("design"), dict) else {}
            groups = _dicts(design.get("groups"))
            if (
                not design.get("unit_of_analysis")
                or not groups
                or any("n" not in g for g in groups)
            ):
                findings.append(
                    Finding(
                        rule_id="PCI-STAT-001",
                        severity=Severity.WARNING,
                        target=target,
                        message="Quantitative comparison lacks unit of analysis or group size.",
                        remediation="Record the independent unit and n for every compared group.",
                    )
                )
            unit = str(design.get("unit_of_analysis", "")).casefold()
            if "_nested_within_" in unit and (
                not design.get("parent_unit") or any("clusters" not in group for group in groups)
            ):
                findings.append(
                    Finding(
                        rule_id="PCI-STAT-003",
                        severity=Severity.WARNING,
                        target=target,
                        message=(
                            "Nested observations lack an explicit parent unit or per-group cluster counts."
                        ),
                        remediation=(
                            "Record design.parent_unit and group.clusters; analyze independent parent "
                            "units or use a model that accounts for clustering."
                        ),
                    )
                )

    claims = document.data.get("claims", [])
    if isinstance(claims, list):
        for offset, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            target = str(claim.get("id", f"claims[{offset}]"))
            supports_set = _string_set(claim.get("supports"))
            challenges_set = _string_set(claim.get("challenges"))
            overlap = sorted(supports_set & challenges_set)
            if overlap:
                findings.append(
                    Finding(
                        rule_id="PCI-REL-001",
                        severity=Severity.ERROR,
                        target=target,
                        evidence_ids=tuple(overlap),
                        message=(
                            "The same evidence is linked as both support and challenge: "
                            + ", ".join(overlap)
                            + "."
                        ),
                        remediation=(
                            "Resolve the evidence relationship, split mixed results into bounded "
                            "evidence records, or represent the claim as disputed."
                        ),
                    )
                )
            if claim.get("status") in {"prohibited", "superseded"}:
                continue
            supports = [
                evidence_index[record_id]
                for record_id in _list(claim.get("supports"))
                if record_id in evidence_index
            ]
            evidence_ids = tuple(
                record_id
                for record_id in _list(claim.get("supports"))
                if isinstance(record_id, str)
            )
            if claim.get("type") in EFFECT_CLAIM_TYPES and supports:
                has_effect = any(
                    isinstance(item.get("result"), dict)
                    and isinstance(item["result"].get("effect"), dict)
                    and isinstance(item["result"].get("uncertainty"), dict)
                    for item in supports
                )
                if not has_effect:
                    findings.append(
                        Finding(
                            rule_id="PCI-STAT-002",
                            severity=Severity.WARNING,
                            target=target,
                            evidence_ids=evidence_ids,
                            message="Effect claim has no supporting effect estimate with uncertainty.",
                            remediation="Link an effect and uncertainty, or explain why they are not applicable.",
                        )
                    )
            findings.extend(_scope_findings(target, claim, supports, evidence_ids))
            findings.extend(_semantic_boundary_findings(target, claim, supports, evidence_ids))
            if claim.get("type") in CAUSAL_CLAIM_TYPES and supports:
                identified = any(
                    _has_role(item, "causal_identification")
                    or (
                        isinstance(item.get("design"), dict)
                        and item["design"].get("family") == "experiment"
                        and _has_any_role(item, {"perturbation", "temporal_intervention", "rescue"})
                    )
                    for item in supports
                )
                if not identified:
                    findings.append(
                        Finding(
                            rule_id="PCI-CAUSAL-001",
                            severity=Severity.ERROR,
                            target=target,
                            evidence_ids=evidence_ids,
                            message="Causal claim has no explicit intervention or causal-identification evidence.",
                            remediation="Soften the claim or add design-specific causal evidence and estimand.",
                        )
                    )
            if claim.get("type") == "mechanism" and supports:
                if not any(_supports_mechanism(claim, item) for item in supports):
                    findings.append(
                        Finding(
                            rule_id="PCI-MECH-001",
                            severity=Severity.ERROR,
                            target=target,
                            evidence_ids=evidence_ids,
                            message="Mechanism claim is supported only by non-mechanistic evidence.",
                            remediation=(
                                "Treat it as a candidate mechanism or add perturbation, rescue, direct, "
                                "structural, or temporally discriminating evidence."
                            ),
                        )
                    )

    stories = document.data.get("stories", [])
    if isinstance(stories, list):
        for offset, story in enumerate(stories):
            if not isinstance(story, dict):
                continue
            target = str(story.get("id", f"stories[{offset}]"))
            active = story.get("status") not in {"rejected", "superseded"}
            story_claim_ids = list(
                dict.fromkeys([story.get("central_claim"), *_list(story.get("claim_path"))])
            )
            invalid_claims = [
                str(claim_id)
                for claim_id in story_claim_ids
                if claim_id in claim_index
                and (
                    not _list(claim_index[claim_id].get("supports"))
                    or claim_index[claim_id].get("status") in {"prohibited", "superseded"}
                )
            ]
            if active and invalid_claims:
                findings.append(
                    Finding(
                        rule_id="PCI-STORY-001",
                        severity=Severity.ERROR,
                        target=target,
                        message=(
                            "Active story uses unsupported, prohibited, or superseded claims: "
                            + ", ".join(invalid_claims)
                            + "."
                        ),
                        remediation=(
                            "Remove those claims from the active path, restore valid support, or reject "
                            "the story."
                        ),
                    )
                )
            path_claims = (
                [
                    claim_index[claim_id]
                    for claim_id in _list(story.get("claim_path"))
                    if claim_id in claim_index
                ]
                if active
                else []
            )
            has_boundary = any(
                beat.get("role") == "boundary" for beat in _dicts(story.get("beats"))
            )
            challenged = [
                str(claim.get("id")) for claim in path_claims if _list(claim.get("challenges"))
            ]
            if challenged and not has_boundary:
                findings.append(
                    Finding(
                        rule_id="PCI-CONTRA-001",
                        severity=Severity.WARNING,
                        target=target,
                        message=f"Challenging evidence for {', '.join(challenged)} is absent from story boundaries.",
                        remediation="Expose it in a boundary beat, alternative explanation, or central gap.",
                    )
                )
            for figure in _dicts(story.get("figure_plan")) if active else []:
                if not str(figure.get("question", "")).strip() or not _list(
                    figure.get("claim_ids")
                ):
                    findings.append(
                        Finding(
                            rule_id="PCI-STORY-002",
                            severity=Severity.NOTE,
                            target=target,
                            message=f"Figure {figure.get('figure', '?')} lacks an argumentative question or claim.",
                            remediation="State what the figure tests and which claim its evidence supports.",
                        )
                    )
            extension = _proposal_extension(story)
            if extension.get("generated") is True:
                run_id = extension.get("run_id")
                run = run_index.get(run_id) if isinstance(run_id, str) else None
                if run is not None:
                    manifest = (
                        run.get("input_manifest")
                        if isinstance(run.get("input_manifest"), dict)
                        else {}
                    )
                    allowed_evidence = _string_set(manifest.get("evidence_ids"))
                    allowed_claims = _string_set(manifest.get("claim_ids"))
                    used_evidence, used_claims = _story_references(story)
                    extra_evidence = sorted(used_evidence - allowed_evidence)
                    extra_claims = sorted(used_claims - allowed_claims)
                    output_ids = set(_list(run.get("output_ids")))
                    provider = run.get("provider") if isinstance(run.get("provider"), dict) else {}
                    mismatches: list[str] = []
                    if extra_evidence:
                        mismatches.append(f"evidence outside manifest: {', '.join(extra_evidence)}")
                    if extra_claims:
                        mismatches.append(f"claims outside manifest: {', '.join(extra_claims)}")
                    if target not in output_ids:
                        mismatches.append(f"story is absent from run {run_id} output_ids")
                    if extension.get("provider_id") != provider.get("id"):
                        mismatches.append("provider ID does not match its run")
                    if extension.get("provider_version") != provider.get("version"):
                        mismatches.append("provider version does not match its run")
                    if mismatches:
                        findings.append(
                            Finding(
                                rule_id="PCI-AI-001",
                                severity=Severity.ERROR,
                                target=target,
                                message="Generated story violates its recorded input boundary: "
                                + "; ".join(mismatches)
                                + ".",
                                remediation=(
                                    "Regenerate from the recorded inputs or correct the manifest; "
                                    "never add unrecorded evidence or claims to generated output."
                                ),
                            )
                        )
    for run_id, run in run_index.items():
        for output_id in _string_set(run.get("output_ids")):
            if run.get("kind") != "story_proposal":
                continue
            story = story_index.get(output_id)
            if story is None:
                continue
            extension = _proposal_extension(story)
            if extension.get("generated") is not True or extension.get("run_id") != run_id:
                findings.append(
                    Finding(
                        rule_id="PCI-AI-001",
                        severity=Severity.ERROR,
                        target=output_id,
                        message=(
                            f"Run {run_id} lists this story as output, but the story does not "
                            "identify that generating run."
                        ),
                        remediation="Restore the proposal extension or remove the false run-output link.",
                    )
                )
    findings.extend(_hypothesis_findings(document, run_index, evidence_index, claim_index))
    return findings


def _hypothesis_findings(
    document: ProjectDocument,
    run_index: dict[str, dict[str, Any]],
    evidence_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    hypothesis_index = {
        str(item["id"]): item for item in _dicts(document.data.get("hypotheses")) if "id" in item
    }
    human_shortlists = {
        review.get("target")
        for review in _dicts(document.data.get("reviews"))
        if review.get("decision") == "select"
        and isinstance(review.get("actor"), dict)
        and review["actor"].get("kind") == "human"
    }
    for item in hypothesis_index.values():
        hypothesis_id = str(item.get("id", "?"))
        if item.get("status") in {"rejected", "superseded"}:
            continue
        if item.get("status") == "shortlisted" and hypothesis_id not in human_shortlists:
            findings.append(
                Finding(
                    rule_id="PCI-HYP-004",
                    severity=Severity.ERROR,
                    target=hypothesis_id,
                    message="Hypothesis is shortlisted without a human selection event.",
                    remediation="Add a human select ReviewEvent or return the hypothesis to speculative.",
                )
            )
        novelty = item.get("novelty") if isinstance(item.get("novelty"), dict) else {}
        if novelty.get("status") == "unchecked":
            findings.append(
                Finding(
                    rule_id="PCI-HYP-001",
                    severity=Severity.NOTE,
                    target=hypothesis_id,
                    message="Hypothesis novelty has not been checked against the literature.",
                    remediation=(
                        "Keep novelty language disabled until a dated literature assessment with "
                        "traceable sources is recorded."
                    ),
                )
            )
        decisive_tests = _dicts(item.get("decisive_tests"))
        if not decisive_tests or any(
            not str(test.get("falsifier", "")).strip() for test in decisive_tests
        ):
            findings.append(
                Finding(
                    rule_id="PCI-HYP-002",
                    severity=Severity.ERROR,
                    target=hypothesis_id,
                    message="Active hypothesis lacks a decisive test with an explicit falsifier.",
                    remediation="Add an intervention or comparison that distinguishes alternatives and states what would falsify the hypothesis.",
                )
            )
        if not _list(item.get("alternatives")):
            findings.append(
                Finding(
                    rule_id="PCI-HYP-003",
                    severity=Severity.ERROR,
                    target=hypothesis_id,
                    message="Active hypothesis has no competing explanation.",
                    remediation="Record at least one plausible alternative and a result that distinguishes it.",
                )
            )
        extension = _hypothesis_extension(item)
        if extension.get("generated") is True:
            run_id = extension.get("run_id")
            run = run_index.get(run_id) if isinstance(run_id, str) else None
            mismatches: list[str] = []
            if run is not None:
                parameters = (
                    run.get("parameters") if isinstance(run.get("parameters"), dict) else {}
                )
                literature_sources = _list(novelty.get("literature_sources"))
                if parameters.get("literature_mode") == "offline" and (
                    novelty.get("status") != "unchecked" or literature_sources
                ):
                    findings.append(
                        Finding(
                            rule_id="PCI-HYP-005",
                            severity=Severity.ERROR,
                            target=hypothesis_id,
                            message="Offline-generated hypothesis claims a literature novelty assessment.",
                            remediation="Reset novelty to unchecked with no sources, or regenerate through a provider that records a real literature search.",
                        )
                    )
                manifest = (
                    run.get("input_manifest") if isinstance(run.get("input_manifest"), dict) else {}
                )
                allowed_evidence = _string_set(manifest.get("evidence_ids"))
                allowed_claims = _string_set(manifest.get("claim_ids"))
                used_evidence, used_claims = _hypothesis_references(
                    item, set(evidence_index), set(claim_index)
                )
                extra_evidence = sorted(used_evidence - allowed_evidence)
                extra_claims = sorted(used_claims - allowed_claims)
                if extra_evidence:
                    mismatches.append(f"evidence outside manifest: {', '.join(extra_evidence)}")
                if extra_claims:
                    mismatches.append(f"claims outside manifest: {', '.join(extra_claims)}")
                if hypothesis_id not in _string_set(run.get("output_ids")):
                    mismatches.append(f"hypothesis is absent from run {run_id} output_ids")
                provider = run.get("provider") if isinstance(run.get("provider"), dict) else {}
                if extension.get("provider_id") != provider.get("id"):
                    mismatches.append("provider ID does not match its run")
                if extension.get("provider_version") != provider.get("version"):
                    mismatches.append("provider version does not match its run")
            if mismatches:
                findings.append(
                    Finding(
                        rule_id="PCI-AI-001",
                        severity=Severity.ERROR,
                        target=hypothesis_id,
                        message="Generated hypothesis violates its recorded input boundary: "
                        + "; ".join(mismatches)
                        + ".",
                        remediation="Regenerate from recorded inputs; never attach unrecorded evidence or claims to generated output.",
                    )
                )
    for run_id, run in run_index.items():
        if run.get("kind") != "hypothesis_generation":
            continue
        for output_id in _string_set(run.get("output_ids")):
            hypothesis = hypothesis_index.get(output_id)
            if hypothesis is None:
                continue
            extension = _hypothesis_extension(hypothesis)
            if extension.get("generated") is not True or extension.get("run_id") != run_id:
                findings.append(
                    Finding(
                        rule_id="PCI-AI-001",
                        severity=Severity.ERROR,
                        target=output_id,
                        message=f"Run {run_id} lists this hypothesis as output, but it does not identify that generating run.",
                        remediation="Restore the hypothesis extension or remove the false run-output link.",
                    )
                )
    return findings


def _scope_findings(
    target: str,
    claim: dict[str, Any],
    supports: list[dict[str, Any]],
    evidence_ids: tuple[str, ...],
) -> list[Finding]:
    claim_scope = claim.get("scope") if isinstance(claim.get("scope"), dict) else {}
    if not claim_scope or not supports:
        return []
    conflicts: list[str] = []
    unknown: list[str] = []
    for field, claim_value in claim_scope.items():
        values = {
            item["scope"][field]
            for item in supports
            if isinstance(item.get("scope"), dict) and field in item["scope"]
        }
        if not values:
            unknown.append(field)
        elif claim_value not in values:
            conflicts.append(field)
    findings: list[Finding] = []
    if conflicts:
        findings.append(
            Finding(
                rule_id="PCI-SCOPE-001",
                severity=Severity.ERROR,
                target=target,
                evidence_ids=evidence_ids,
                message=f"Claim scope conflicts with supporting evidence for: {', '.join(conflicts)}.",
                remediation="Narrow the claim or add bridging evidence for the broader scope.",
            )
        )
    if unknown:
        findings.append(
            Finding(
                rule_id="PCI-SCOPE-001",
                severity=Severity.WARNING,
                target=target,
                evidence_ids=evidence_ids,
                message=f"Supporting evidence does not declare claim scope fields: {', '.join(unknown)}.",
                remediation="Add evidence scope or explicitly mark the generalization as conditional.",
            )
        )
    return findings


def _semantic_boundary_findings(
    target: str,
    claim: dict[str, Any],
    supports: list[dict[str, Any]],
    evidence_ids: tuple[str, ...],
) -> list[Finding]:
    """Catch a few explicit category errors; this is not unrestricted NLP inference."""
    if not supports:
        return []
    claim_text = str(claim.get("text", "")).casefold()
    support_texts = [str(item.get("statement", "")).casefold() for item in supports]
    joined = " ".join(support_texts)
    findings: list[Finding] = []

    organismal_transmission = (
        "offspring",
        "between animals",
        "transgenerational",
        "intergenerational",
        "germline transmission",
    )
    cellular_inheritance = (
        "cell division",
        "cell divisions",
        "clonal",
        "clone-label",
        "organoid",
    )
    support_has_organismal_bridge = any(
        marker in joined for marker in ("breeding", "offspring", "germline", "cross-foster")
    )
    if (
        any(marker in claim_text for marker in organismal_transmission)
        and any(marker in joined for marker in cellular_inheritance)
        and any(_has_role(item, "lineage_tracing") for item in supports)
        and not support_has_organismal_bridge
    ):
        findings.append(
            Finding(
                rule_id="PCI-SEM-001",
                severity=Severity.ERROR,
                target=target,
                evidence_ids=evidence_ids,
                message=(
                    "Cellular or clonal inheritance is being generalized to organismal or "
                    "intergenerational transmission without bridging evidence."
                ),
                remediation=(
                    "Narrow the claim to mitotic or clonal inheritance, or add an organism-level "
                    "transmission design."
                ),
            )
        )

    initiation_claim = any(
        marker in claim_text
        for marker in (
            "tumour-initiation",
            "tumor-initiation",
            "initiation frequency",
            "frequency of tumour",
            "frequency of tumor",
            "tumour incidence",
            "tumor incidence",
        )
    )
    explicit_count_boundary = any(
        marker in joined
        for marker in (
            "did not have more macroscopic tumour",
            "did not have more macroscopic tumor",
            "did not increase tumour number",
            "did not increase tumor number",
            "no increase in tumour number",
            "no increase in tumor number",
            "unchanged tumour number",
            "unchanged tumor number",
        )
    )
    if initiation_claim and explicit_count_boundary:
        findings.append(
            Finding(
                rule_id="PCI-SEM-001",
                severity=Severity.ERROR,
                target=target,
                evidence_ids=evidence_ids,
                message=(
                    "Tumour outgrowth or size evidence with an explicit null count result does not "
                    "support increased tumour-initiation frequency."
                ),
                remediation=(
                    "Narrow the claim to post-initiation growth, or add an initiation-count design "
                    "with the independent experimental unit recorded."
                ),
            )
        )
    return findings


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_set(value: Any) -> set[str]:
    return {item for item in _list(value) if isinstance(item, str)}


def _proposal_extension(story: dict[str, Any]) -> dict[str, Any]:
    extensions = story.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    value = extensions.get("org.paperci.proposal.v1")
    return value if isinstance(value, dict) else {}


def _hypothesis_extension(hypothesis: dict[str, Any]) -> dict[str, Any]:
    extensions = hypothesis.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    value = extensions.get("org.paperci.hypothesis.v1")
    return value if isinstance(value, dict) else {}


def _story_references(story: dict[str, Any]) -> tuple[set[str], set[str]]:
    evidence_ids: set[str] = set()
    claim_ids = _string_set(story.get("claim_path"))
    central = story.get("central_claim")
    if isinstance(central, str):
        claim_ids.add(central)
    for beat in _dicts(story.get("beats")):
        claim_ids.update(_string_set(beat.get("claim_ids")))
    for figure in _dicts(story.get("figure_plan")):
        evidence_ids.update(_string_set(figure.get("evidence_ids")))
        claim_ids.update(_string_set(figure.get("claim_ids")))
    for gap in _dicts(story.get("gaps")):
        claim_ids.update(_string_set(gap.get("blocks")))
    return evidence_ids, claim_ids


def _hypothesis_references(
    hypothesis: dict[str, Any],
    known_evidence: set[str],
    known_claims: set[str],
) -> tuple[set[str], set[str]]:
    evidence_ids = _string_set(hypothesis.get("evidence_ids"))
    claim_ids = _string_set(hypothesis.get("anchor_claims"))
    seed_claim = hypothesis.get("seed_claim")
    if isinstance(seed_claim, str):
        claim_ids.add(seed_claim)
    for step in _dicts(hypothesis.get("inference_steps")):
        for reference in _string_set(step.get("grounded_in")):
            if reference in known_evidence:
                evidence_ids.add(reference)
            elif reference in known_claims:
                claim_ids.add(reference)
    for figure in _dicts(hypothesis.get("figure_plan")):
        evidence_ids.update(_string_set(figure.get("evidence_ids")))
    return evidence_ids, claim_ids


def _is_local_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    return not parsed.scheme and not uri.startswith("doi:")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evidence_roles(evidence: dict[str, Any]) -> set[str]:
    extensions = evidence.get("extensions")
    if not isinstance(extensions, dict):
        return set()
    raw = extensions.get("org.paperci.core.v1")
    if not isinstance(raw, dict):
        return set()
    roles = raw.get("evidence_roles", [])
    if isinstance(roles, str):
        return {roles}
    return {str(role) for role in roles} if isinstance(roles, list) else set()


def _has_role(evidence: dict[str, Any], role: str) -> bool:
    return role in _evidence_roles(evidence)


def _has_any_role(evidence: dict[str, Any], roles: set[str]) -> bool:
    return bool(_evidence_roles(evidence) & roles)


def _supports_mechanism(claim: dict[str, Any], evidence: dict[str, Any]) -> bool:
    roles = _evidence_roles(evidence)
    if roles & MECHANISTIC_ROLES:
        return True
    claim_text = str(claim.get("text", "")).casefold()
    contextual_roles = {
        "direct_occupancy": ("direct", "bind", "occupancy"),
        "lineage_tracing": ("clon", "lineage", "inherit", "propagat", "cell-intrinsic"),
        "state_erasure_test": ("eras", "reset", "memory state"),
        "washout_persistence": ("persist", "washout", "memory"),
    }
    if any(
        role in roles and any(marker in claim_text for marker in markers)
        for role, markers in contextual_roles.items()
    ):
        return True
    return "target_engagement" in roles and bool(
        roles & {"perturbation", "functional_perturbation", "rescue"}
    )
