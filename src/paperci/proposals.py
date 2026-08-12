from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from paperci.engine import validate_project
from paperci.errors import ProposalError
from paperci.findings import Severity
from paperci.project import ProjectDocument, next_identifier
from paperci.providers import DEFAULT_STRATEGIES, ProposalContext, StoryProvider


@dataclass(slots=True)
class ProposalOutcome:
    document: ProjectDocument
    run: dict[str, Any]
    stories: list[dict[str, Any]]
    notes: list[str]
    reused: bool = False


def proposal_text(outcome: ProposalOutcome) -> str:
    provider = outcome.run.get("provider") if isinstance(outcome.run.get("provider"), dict) else {}
    state = "reused existing" if outcome.reused else "generated new"
    lines = [
        f"Proposal run {outcome.run.get('id', '?')} ({state})",
        f"Provider: {provider.get('id', '?')}@{provider.get('version', '?')}",
        f"Input hash: {outcome.run.get('input_hash', '?')}",
        "",
    ]
    for story in outcome.stories:
        extension = _proposal_extension(story)
        path = " -> ".join(_strings(story.get("claim_path"))) or "none"
        lines.extend(
            [
                f"{story.get('id', '?')}  {story.get('title', '?')}",
                f"  Strategy: {extension.get('strategy', 'unknown')}",
                f"  Central claim: {story.get('central_claim', '?')}",
                f"  Claim path: {path}",
                f"  Recorded gaps: {len(_dicts(story.get('gaps')))}",
            ]
        )
    if outcome.notes:
        lines.extend(["", "Provider notes:"])
        lines.extend(f"- {note}" for note in outcome.notes)
    if outcome.reused:
        lines.extend(
            ["", "Reused the stored run and story statuses; no project records were changed."]
        )
    else:
        lines.extend(
            [
                "",
                "All generated stories remain candidates. Run paperci lint and paperci compare, "
                "then review them as a human.",
            ]
        )
    return "\n".join(lines)


def proposal_json(outcome: ProposalOutcome, *, dry_run: bool = False) -> str:
    return json.dumps(
        {
            "dry_run": dry_run,
            "reused": outcome.reused,
            "run": outcome.run,
            "stories": outcome.stories,
            "notes": outcome.notes,
        },
        indent=2,
        ensure_ascii=False,
    )


def propose_stories(
    document: ProjectDocument,
    provider: StoryProvider,
    *,
    arcs: int = 3,
    central_claim: str | None = None,
    force: bool = False,
) -> ProposalOutcome:
    if not 1 <= arcs <= len(DEFAULT_STRATEGIES):
        raise ProposalError(f"--arcs must be between 1 and {len(DEFAULT_STRATEGIES)}.")
    structural = validate_project(document, scientific=False)
    errors = [finding for finding in structural if finding.severity == Severity.ERROR]
    if errors:
        rules = ", ".join(sorted({finding.rule_id for finding in errors}))
        raise ProposalError(f"Project has structural errors ({rules}); run paperci validate first.")

    working = ProjectDocument(path=document.path, data=copy.deepcopy(document.data))
    working.data["spec_version"] = "0.2"
    evidence = _dict_index(working.data.get("evidence"))
    claims = tuple(_dicts(working.data.get("claims")))
    if not claims:
        raise ProposalError(
            "No claims exist. Add at least one supported candidate with paperci claim."
        )
    if central_claim and central_claim not in {str(claim.get("id")) for claim in claims}:
        raise ProposalError(f"Central claim does not exist: {central_claim}")

    strategies = tuple(DEFAULT_STRATEGIES[:arcs])
    parameters = {
        "arcs": arcs,
        "strategies": list(strategies),
        "central_claim": central_claim,
    }
    input_manifest = {
        "evidence_ids": sorted(evidence),
        "claim_ids": sorted(str(claim["id"]) for claim in claims),
    }
    input_hash = proposal_input_hash(working, provider, parameters)
    runs = working.data.setdefault("runs", [])
    if not isinstance(runs, list):
        raise ProposalError("Project field 'runs' must be a list.")
    stories = working.data.setdefault("stories", [])
    if not isinstance(stories, list):
        raise ProposalError("Project field 'stories' must be a list.")

    if not force:
        existing = _find_reusable_run(
            runs, stories, provider.provider_id, provider.provider_version, input_hash
        )
        if existing is not None:
            output_ids = set(_strings(existing.get("output_ids")))
            existing_stories = [
                story for story in _dicts(stories) if str(story.get("id")) in output_ids
            ]
            return ProposalOutcome(working, existing, existing_stories, [], reused=True)

    for story in _dicts(stories):
        extension = _proposal_extension(story)
        if (
            extension.get("generated") is True
            and extension.get("provider_id") == provider.provider_id
            and story.get("status") == "candidate"
        ):
            story["status"] = "superseded"

    run_id = next_identifier(runs, "RUN")
    story_ids = _next_identifiers(stories, "S", arcs)
    scientific_findings = tuple(validate_project(working, scientific=True))
    context = ProposalContext(
        run_id=run_id,
        story_ids=tuple(story_ids),
        evidence=copy.deepcopy(evidence),
        claims=tuple(copy.deepcopy(claims)),
        findings=scientific_findings,
        strategies=strategies,
        central_claim=central_claim,
    )
    result = provider.propose(context)
    if not result.stories:
        detail = " ".join(str(note) for note in result.notes) or "The provider returned no stories."
        raise ProposalError(detail)
    if any(not isinstance(story, dict) for story in result.stories):
        raise ProposalError("The provider returned a non-object story.")
    generated = [copy.deepcopy(story) for story in result.stories]
    output_ids = [str(story.get("id")) for story in generated]
    if (
        len(output_ids) != len(set(output_ids))
        or not set(output_ids) <= set(story_ids)
        or any(story.get("id") is None for story in generated)
    ):
        raise ProposalError("The provider returned duplicate or unallocated story IDs.")
    strategy_by_story_id = dict(zip(story_ids, strategies, strict=True))
    for story, story_id in zip(generated, output_ids, strict=True):
        story["status"] = "candidate"
        extensions = story.setdefault("extensions", {})
        if not isinstance(extensions, dict):
            raise ProposalError("The provider returned invalid story extensions.")
        extensions["org.paperci.proposal.v1"] = {
            "generated": True,
            "run_id": run_id,
            "provider_id": provider.provider_id,
            "provider_version": provider.provider_version,
            "strategy": strategy_by_story_id[story_id],
        }
    stories.extend(generated)
    run = {
        "id": run_id,
        "kind": "story_proposal",
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
    provider_boundary_errors = [
        finding
        for finding in validate_project(working, scientific=True)
        if finding.severity == Severity.ERROR
        and finding.rule_id in {"PCI-SCHEMA-001", "PCI-REF-001", "PCI-AI-001"}
    ]
    if provider_boundary_errors:
        rules = ", ".join(sorted({finding.rule_id for finding in provider_boundary_errors}))
        detail = "; ".join(
            f"{finding.target}: {finding.message}" for finding in provider_boundary_errors[:3]
        )
        raise ProposalError(f"Provider output violates the project boundary ({rules}): {detail}")
    return ProposalOutcome(working, run, generated, list(result.notes))


def proposal_input_hash(
    document: ProjectDocument,
    provider: StoryProvider,
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


def _find_reusable_run(
    runs: list[Any],
    stories: list[Any],
    provider_id: str,
    provider_version: str,
    input_hash: str,
) -> dict[str, Any] | None:
    story_status = {str(story.get("id")): story.get("status") for story in _dicts(stories)}
    for run in reversed(_dicts(runs)):
        provider = run.get("provider") if isinstance(run.get("provider"), dict) else {}
        output_ids = _strings(run.get("output_ids"))
        if (
            run.get("kind") == "story_proposal"
            and run.get("status") == "completed"
            and provider.get("id") == provider_id
            and provider.get("version") == provider_version
            and run.get("input_hash") == input_hash
            and output_ids
            and all(
                output_id in story_status and story_status[output_id] != "superseded"
                for output_id in output_ids
            )
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


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _dict_index(value: Any) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in _dicts(value) if "id" in item}


def _sorted_records(value: Any) -> list[dict[str, Any]]:
    return sorted(_dicts(value), key=lambda item: str(item.get("id", "")))


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _proposal_extension(story: dict[str, Any]) -> dict[str, Any]:
    extensions = story.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    value = extensions.get("org.paperci.proposal.v1")
    return value if isinstance(value, dict) else {}
