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
}


def validate_project(document: ProjectDocument, *, scientific: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_schema_findings(document))
    index, duplicate_findings = _build_index(document)
    findings.extend(duplicate_findings)
    findings.extend(_reference_findings(document, index))
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
    for collection in ("evidence", "claims", "stories", "reviews", "runs"):
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

    reviews = document.data.get("reviews", [])
    if isinstance(reviews, list):
        for offset, review in enumerate(reviews):
            if not isinstance(review, dict):
                continue
            owner = str(review.get("id", f"reviews[{offset}]"))
            require(
                owner,
                review.get("target"),
                {"evidence", "claims", "stories"},
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
            for position, reference in enumerate(_list(run.get("output_ids"))):
                require(owner, reference, {"stories"}, f"/runs/{offset}/output_ids/{position}")

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
    return findings


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

    claims = document.data.get("claims", [])
    if isinstance(claims, list):
        for offset, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            target = str(claim.get("id", f"claims[{offset}]"))
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
                if not any(_has_any_role(item, MECHANISTIC_ROLES) for item in supports):
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
