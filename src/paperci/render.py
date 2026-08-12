from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from paperci import __version__
from paperci.findings import Finding, Severity, counts
from paperci.project import ProjectDocument


def findings_text(findings: list[Finding]) -> str:
    if not findings:
        return "No findings."
    lines: list[str] = []
    for finding in findings:
        path = f" ({finding.path})" if finding.path else ""
        lines.append(
            f"{finding.severity.label().upper():7} {finding.rule_id} [{finding.target}]{path} {finding.message}"
        )
        lines.append(f"        Fix: {finding.remediation}")
    summary = counts(findings)
    lines.append("")
    lines.append(
        f"Summary: {summary['error']} error(s), {summary['warning']} warning(s), {summary['note']} note(s)."
    )
    return "\n".join(lines)


def findings_json(document: ProjectDocument, findings: list[Finding]) -> str:
    payload = {
        "tool": {"name": "paperci", "version": __version__},
        "project": {"id": document.project_id, "path": str(document.path)},
        "summary": counts(findings),
        "findings": [finding.to_dict() for finding in findings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def findings_sarif(document: ProjectDocument, findings: list[Finding]) -> str:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for finding in findings:
        rules.setdefault(
            finding.rule_id,
            {
                "id": finding.rule_id,
                "shortDescription": {"text": finding.message},
                "help": {"text": finding.remediation},
            },
        )
        level = {
            Severity.ERROR: "error",
            Severity.WARNING: "warning",
            Severity.NOTE: "note",
        }[finding.severity]
        result: dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": level,
            "message": {"text": f"[{finding.target}] {finding.message} Fix: {finding.remediation}"},
        }
        if finding.path:
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": document.path.name},
                    },
                    "logicalLocations": [{"fullyQualifiedName": finding.path}],
                }
            ]
        results.append(result)
    payload = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PaperCI",
                        "version": __version__,
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def markdown_report(document: ProjectDocument, findings: list[Finding]) -> str:
    summary = counts(findings)
    by_target: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_target[finding.target].append(finding)
    data = document.data
    evidence = _dicts(data.get("evidence"))
    claims = _dicts(data.get("claims"))
    stories = _dicts(data.get("stories"))
    runs = _dicts(data.get("runs"))
    lines = [
        f"# PaperCI report: {document.title}",
        "",
        f"- Project: `{document.project_id}`",
        f"- Mode: `{document.mode}`",
        f"- Source: `{document.path.name}`",
        f"- PaperCI: `{__version__}`",
        f"- Findings: **{summary['error']} errors**, {summary['warning']} warnings, {summary['note']} notes",
        "",
        "## Gate status",
        "",
    ]
    if summary["error"]:
        lines.append("**FAIL** — error-level findings must be resolved before the story passes.")
    else:
        lines.append("**PASS** — no error-level findings were detected by the current rule set.")
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No findings.")
    else:
        for finding in findings:
            lines.extend(
                [
                    f"### {finding.severity.label().upper()} · {finding.rule_id} · `{finding.target}`",
                    "",
                    finding.message,
                    "",
                    f"**Remediation:** {finding.remediation}",
                    "",
                ]
            )
    lines.extend(["## Evidence inventory", ""])
    if evidence:
        lines.extend(["| ID | Status | Kind | Statement | Findings |", "|---|---|---|---|---|"])
        for item in evidence:
            item_id = str(item.get("id", "?"))
            lines.append(
                f"| `{item_id}` | {item.get('status', '?')} | {item.get('kind', '?')} | "
                f"{_cell(item.get('statement', ''))} | {_finding_ids(by_target[item_id])} |"
            )
    else:
        lines.append("No evidence cards yet. Run `paperci add`.")
    lines.extend(["", "## Claim register", ""])
    if claims:
        lines.extend(
            ["| ID | Decision | Type | Claim | Support | Findings |", "|---|---|---|---|---|---|"]
        )
        for item in claims:
            item_id = str(item.get("id", "?"))
            support = ", ".join(f"`{value}`" for value in item.get("supports", [])) or "—"
            lines.append(
                f"| `{item_id}` | {item.get('status', '?')} | {item.get('type', '?')} | "
                f"{_cell(item.get('text', ''))} | {support} | {_finding_ids(by_target[item_id])} |"
            )
    else:
        lines.append("No claims yet.")
    lines.extend(["", "## Story arcs", ""])
    if not stories:
        lines.append("No story arcs yet. Add supported claims, then run `paperci propose`.")
    for story in stories:
        story_id = str(story.get("id", "?"))
        extension = _proposal_extension(story)
        lines.extend(
            [
                f"### {story.get('title', story_id)} (`{story_id}`)",
                "",
                f"- Status: `{story.get('status', '?')}`",
                f"- Strategy: `{extension.get('strategy', 'manual')}`",
                f"- Central question: {story.get('central_question', '—')}",
                f"- Central claim: `{story.get('central_claim', '?')}`",
                "- Claim path: "
                + (" → ".join(f"`{value}`" for value in story.get("claim_path", [])) or "—"),
                f"- Findings: {_finding_ids(by_target[story_id])}",
                "",
            ]
        )
        figures = _dicts(story.get("figure_plan"))
        if figures:
            lines.extend(["| Figure | Question | Evidence | Claims |", "|---|---|---|---|"])
            for figure in figures:
                evidence_ids = ", ".join(f"`{value}`" for value in figure.get("evidence_ids", []))
                claim_ids = ", ".join(f"`{value}`" for value in figure.get("claim_ids", []))
                lines.append(
                    f"| {figure.get('figure', '?')} | {_cell(figure.get('question', ''))} | "
                    f"{evidence_ids or '—'} | {claim_ids or '—'} |"
                )
            lines.append("")
        gaps = _dicts(story.get("gaps"))
        if gaps:
            lines.append("**Recorded gaps**")
            lines.append("")
            for gap in gaps:
                lines.append(
                    f"- `{gap.get('id', '?')}` ({gap.get('severity', '?')}): {gap.get('question', '—')}"
                )
            lines.append("")
    lines.extend(["## Proposal runs", ""])
    if runs:
        lines.extend(
            [
                "| Run | Provider | Input hash | Outputs | Status |",
                "|---|---|---|---|---|",
            ]
        )
        for run in runs:
            provider = run.get("provider") if isinstance(run.get("provider"), dict) else {}
            provider_label = f"{provider.get('id', '?')}@{provider.get('version', '?')}"
            output_ids = ", ".join(f"`{value}`" for value in run.get("output_ids", [])) or "—"
            input_hash = str(run.get("input_hash", "?"))
            lines.append(
                f"| `{run.get('id', '?')}` | {_cell(provider_label)} | `{input_hash[:12]}…` | "
                f"{output_ids} | {run.get('status', '?')} |"
            )
    else:
        lines.append("No proposal runs recorded.")
    lines.append("")
    lines.extend(
        [
            "## Interpretation boundary",
            "",
            "This report checks the structured project against the current PaperCI rules. "
            "It is not peer review, statistical certification, or a journal acceptance prediction.",
            "",
        ]
    )
    return "\n".join(lines)


def write_or_return(text: str, output: Path | None) -> str:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text.rstrip() + "\n", encoding="utf-8")
        return str(output.resolve())
    return text


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _finding_ids(findings: list[Finding]) -> str:
    return ", ".join(f"`{finding.rule_id}`" for finding in findings) or "—"


def _proposal_extension(story: dict[str, Any]) -> dict[str, Any]:
    extensions = story.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    value = extensions.get("org.paperci.proposal.v1")
    return value if isinstance(value, dict) else {}
