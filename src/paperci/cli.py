from __future__ import annotations

import platform
import re
import sys
from pathlib import Path

import typer
from jsonschema import Draft202012Validator

from paperci import __version__
from paperci.comparison import compare_stories, comparison_json, comparison_text
from paperci.engine import validate_project
from paperci.errors import PaperCIError, ProposalError
from paperci.findings import Finding, Severity, counts
from paperci.project import (
    ProjectDocument,
    empty_project,
    find_schema_path,
    load_project,
    load_schema,
    next_identifier,
    save_project,
)
from paperci.proposals import proposal_json, proposal_text, propose_stories
from paperci.providers import get_provider
from paperci.render import (
    findings_json,
    findings_sarif,
    findings_text,
    markdown_report,
    write_or_return,
)

app = typer.Typer(
    name="paperci",
    help="Continuous integration for scientific stories.",
    no_args_is_help=True,
    add_completion=False,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"paperci {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version.",
    ),
) -> None:
    """Inspect and lint evidence-backed scientific stories."""


@app.command("init")
def init_command(
    destination: Path = typer.Argument(
        Path("."), help="Directory in which to create paperci.yaml."
    ),
    project_id: str | None = typer.Option(None, "--id", help="Stable project identifier."),
    title: str | None = typer.Option(None, "--title", help="Human-readable project title."),
    mode: str = typer.Option("sketch", help="Starting mode: sketch, verified, or connected."),
) -> None:
    """Create a new local PaperCI project without contacting a network."""
    if mode not in {"sketch", "verified", "connected"}:
        _fail("--mode must be sketch, verified, or connected.")
    destination = destination.expanduser()
    path = destination / "paperci.yaml"
    if path.exists():
        _fail(f"Refusing to overwrite existing project: {path}")
    if destination.exists() and not destination.is_dir():
        _fail(f"Destination is not a directory: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    inferred = _slug(destination.resolve().name or "paperci-project")
    project_id = project_id or inferred
    title = title or project_id.replace("-", " ").title()
    document = ProjectDocument(path=path.resolve(), data=empty_project(project_id, title, mode))
    save_project(document)
    typer.echo(f"Created {document.path}")
    typer.echo(
        "Next: paperci add && paperci claim --support E001 && paperci propose && paperci compare"
    )


@app.command("add")
def add_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    statement: str | None = typer.Option(
        None,
        "--statement",
        "-s",
        help="A bounded statement of what was observed.",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        help="Local path, URL, DOI, or notes URI for the source.",
    ),
    locator: str | None = typer.Option(
        None,
        "--locator",
        help="Row, table, figure panel, cell, or equivalent locator.",
    ),
    kind: str = typer.Option("quantitative_result", help="Evidence kind."),
    unit_of_analysis: str | None = typer.Option(
        None,
        "--unit-of-analysis",
        help="Independent unit, for example mouse or participant.",
    ),
    group: list[str] | None = typer.Option(
        None,
        "--group",
        help="Group and n as NAME=N; repeat for multiple groups.",
    ),
) -> None:
    """Append one draft evidence card; no model or network is used."""
    kinds = {
        "quantitative_result",
        "qualitative_observation",
        "figure_panel",
        "table",
        "dataset",
        "analysis_output",
        "external_source",
    }
    if kind not in kinds:
        _fail(f"Unknown evidence kind {kind!r}. Choose one of: {', '.join(sorted(kinds))}")
    document = _load_or_fail(project)
    statement = statement or typer.prompt("What was observed?")
    source = source or typer.prompt(
        "Where can a human verify it?",
        default="notes://manual-entry",
        show_default=True,
    )
    if locator is None and sys.stdin.isatty():
        locator = typer.prompt("Precise locator (optional)", default="", show_default=False) or None
    evidence = document.data.setdefault("evidence", [])
    if not isinstance(evidence, list):
        _fail("Project field 'evidence' is not a list; run paperci validate.")
    source_record: dict[str, object] = {"uri": source.strip()}
    if locator:
        source_record["locator"] = locator.strip()
    record: dict[str, object] = {
        "id": next_identifier(evidence, "E"),
        "kind": kind,
        "statement": statement.strip(),
        "status": "draft",
        "source": source_record,
    }
    parsed_groups = _parse_groups(group or [])
    if unit_of_analysis or parsed_groups:
        design: dict[str, object] = {"family": "unknown"}
        if unit_of_analysis:
            design["unit_of_analysis"] = unit_of_analysis
        if parsed_groups:
            design["groups"] = parsed_groups
        record["design"] = design
    evidence.append(record)
    save_project(document)
    typer.echo(f"Added draft evidence {record['id']} to {document.path}")
    typer.echo(
        "Edit the YAML to add effect, uncertainty, scope, or limitations; then run paperci lint."
    )


@app.command("claim")
def claim_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    text: str | None = typer.Option(None, "--text", help="The proposition to test."),
    claim_type: str = typer.Option("association", "--type", help="Scientific claim type."),
    strength: str = typer.Option("suggests", help="Claim strength."),
    support: list[str] | None = typer.Option(
        None,
        "--support",
        help="Supporting evidence ID; repeat for multiple records.",
    ),
    challenge: list[str] | None = typer.Option(
        None,
        "--challenge",
        help="Challenging evidence ID; repeat for multiple records.",
    ),
    assumption: list[str] | None = typer.Option(
        None,
        "--assumption",
        help="Assumption; repeat for multiple entries.",
    ),
    alternative: list[str] | None = typer.Option(
        None,
        "--alternative",
        help="Competing explanation; repeat for multiple entries.",
    ),
    scope: list[str] | None = typer.Option(
        None,
        "--scope",
        help="Scope as FIELD=VALUE; repeat for multiple fields.",
    ),
) -> None:
    """Append one candidate claim linked only to existing evidence."""
    claim_types = {
        "descriptive",
        "difference",
        "association",
        "temporal",
        "predictive",
        "causal_effect",
        "mediation",
        "mechanism",
        "generalization",
        "null",
        "resource",
    }
    strengths = {"observes", "suggests", "supports", "demonstrates", "establishes"}
    if claim_type not in claim_types:
        _fail(f"Unknown claim type {claim_type!r}. Choose one of: {', '.join(sorted(claim_types))}")
    if strength not in strengths:
        _fail(f"Unknown strength {strength!r}. Choose one of: {', '.join(sorted(strengths))}")
    document = _load_or_fail(project)
    text = (text or typer.prompt("What proposition should the evidence support?")).strip()
    if not text:
        _fail("Claim text must not be empty.")
    evidence_records = document.data.get("evidence", [])
    if not isinstance(evidence_records, list):
        _fail("Project field 'evidence' is not a list; run paperci validate.")
    evidence_ids = {
        str(item.get("id"))
        for item in evidence_records
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    supports = _unique_strings(support or [])
    challenges = _unique_strings(challenge or [])
    unknown = sorted((set(supports) | set(challenges)) - evidence_ids)
    if unknown:
        _fail(f"Unknown evidence ID(s): {', '.join(unknown)}")
    claims = document.data.setdefault("claims", [])
    if not isinstance(claims, list):
        _fail("Project field 'claims' is not a list; run paperci validate.")
    if any(
        isinstance(item, dict)
        and str(item.get("text", "")).strip() == text
        and item.get("status") != "superseded"
        for item in claims
    ):
        _fail("An active claim with identical text already exists.")
    parsed_scope = _parse_scope(scope or [])
    record: dict[str, object] = {
        "id": next_identifier(claims, "C"),
        "text": text,
        "type": claim_type,
        "strength": strength,
        "status": "candidate",
        "supports": supports,
        "challenges": challenges,
        "assumptions": _unique_strings(assumption or []),
        "alternatives": _unique_strings(alternative or []),
    }
    if parsed_scope:
        record["scope"] = parsed_scope
    claims.append(record)
    save_project(document)
    typer.echo(f"Added candidate claim {record['id']} to {document.path}")
    if not supports:
        typer.echo(
            "Note: this claim has no supporting evidence and will not be proposed into a story."
        )


@app.command("propose")
def propose_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    arcs: int = typer.Option(3, "--arcs", min=1, max=3, help="Number of competing arcs."),
    provider_id: str = typer.Option(
        "builtin",
        "--provider",
        help="Provider ID; v0.2 includes the offline deterministic provider.",
    ),
    central_claim: str | None = typer.Option(
        None,
        "--central-claim",
        help="Force an eligible claim to anchor the conservative arc.",
    ),
    force: bool = typer.Option(False, "--force", help="Create a new run even if inputs match."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without changing the project."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write output to a file."),
) -> None:
    """Generate bounded competing story candidates; the built-in provider is offline."""
    document = _load_or_fail(project)
    try:
        provider = get_provider(provider_id)
        outcome = propose_stories(
            document,
            provider,
            arcs=arcs,
            central_claim=central_claim,
            force=force,
        )
    except (ProposalError, ValueError) as exc:
        _fail(str(exc))
    if not dry_run and not outcome.reused:
        save_project(outcome.document)
    if output_format == "text":
        rendered = proposal_text(outcome)
    elif output_format == "json":
        rendered = proposal_json(outcome, dry_run=dry_run)
    else:
        _fail("--format must be text or json.")
    if dry_run and output_format == "text":
        rendered += "\n\nDry run: project file was not changed."
    if output:
        path = write_or_return(rendered, output)
        typer.echo(f"Wrote {path}")
    else:
        typer.echo(rendered)


@app.command("compare")
def compare_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write output to a file."),
) -> None:
    """Compare active arcs by hard gates and transparent coverage signals."""
    document = _load_or_fail(project)
    structural_errors = [
        finding
        for finding in validate_project(document, scientific=False)
        if finding.severity == Severity.ERROR
    ]
    if structural_errors:
        rules = ", ".join(sorted({finding.rule_id for finding in structural_errors}))
        _fail(f"Project has structural errors ({rules}); run paperci validate first.")
    result = compare_stories(document)
    if output_format == "text":
        rendered = comparison_text(result)
    elif output_format == "json":
        rendered = comparison_json(result)
    else:
        _fail("--format must be text or json.")
    if output:
        path = write_or_return(rendered, output)
        typer.echo(f"Wrote {path}")
    else:
        typer.echo(rendered)


@app.command("validate")
def validate_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
) -> None:
    """Validate schema, references, sources, hashes, and promotion events."""
    document = _load_or_fail(project)
    findings = validate_project(document, scientific=False)
    _emit_findings(document, findings, output_format)
    if any(finding.severity == Severity.ERROR for finding in findings):
        raise typer.Exit(code=1)


@app.command("lint")
def lint_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    output_format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text, json, or sarif.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to a file instead of stdout.",
    ),
    fail_on: str = typer.Option(
        "error",
        "--fail-on",
        help="Exit non-zero on: error, warning, note, or never.",
    ),
) -> None:
    """Run deterministic scientific-story rules; always offline."""
    document = _load_or_fail(project)
    findings = validate_project(document, scientific=True)
    rendered = _render_findings(document, findings, output_format)
    if output:
        path = write_or_return(rendered, output)
        typer.echo(f"Wrote {path}")
    else:
        typer.echo(rendered)
    threshold = _threshold(fail_on)
    if threshold is not None and any(finding.severity >= threshold for finding in findings):
        raise typer.Exit(code=1)


@app.command("report")
def report_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write Markdown to this path.",
    ),
) -> None:
    """Render an evidence, claim, story, and finding report as Markdown."""
    document = _load_or_fail(project)
    findings = validate_project(document, scientific=True)
    rendered = markdown_report(document, findings)
    if output:
        path = write_or_return(rendered, output)
        typer.echo(f"Wrote {path}")
    else:
        typer.echo(rendered)


@app.command("doctor")
def doctor_command(
    project: Path | None = typer.Argument(None, help="Optional project file or directory."),
) -> None:
    """Check the installation and, optionally, the current project."""
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Python", sys.version_info >= (3, 11), platform.python_version()))
    try:
        schema_path = find_schema_path()
        Draft202012Validator.check_schema(load_schema())
        checks.append(("Schema", True, str(schema_path)))
    except Exception as exc:  # doctor must report all checks
        checks.append(("Schema", False, str(exc)))
    checks.append(
        (
            "Offline core",
            True,
            "all built-in commands import no network client",
        )
    )
    if project is not None:
        try:
            document = load_project(project)
            findings = validate_project(document, scientific=False)
            error_count = counts(findings)["error"]
            checks.append(("Project", error_count == 0, f"{document.path}; {error_count} errors"))
        except PaperCIError as exc:
            checks.append(("Project", False, str(exc)))
    for name, passed, detail in checks:
        typer.echo(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")
    if not all(passed for _, passed, _ in checks):
        raise typer.Exit(code=1)


def _emit_findings(document: ProjectDocument, findings: list[Finding], output_format: str) -> None:
    typer.echo(_render_findings(document, findings, output_format))


def _render_findings(document: ProjectDocument, findings: list[Finding], output_format: str) -> str:
    if output_format == "text":
        return findings_text(findings)
    if output_format == "json":
        return findings_json(document, findings)
    if output_format == "sarif":
        return findings_sarif(document, findings)
    _fail("--format must be text, json, or sarif.")
    raise AssertionError("unreachable")


def _threshold(value: str) -> Severity | None:
    mapping = {
        "error": Severity.ERROR,
        "warning": Severity.WARNING,
        "note": Severity.NOTE,
        "never": None,
    }
    try:
        return mapping[value.lower()]
    except KeyError:
        _fail("--fail-on must be error, warning, note, or never.")
        raise AssertionError("unreachable") from None


def _load_or_fail(project: Path) -> ProjectDocument:
    try:
        return load_project(project)
    except PaperCIError as exc:
        _fail(str(exc))
        raise AssertionError("unreachable") from None


def _parse_groups(values: list[str]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for value in values:
        if "=" not in value:
            _fail(f"Invalid --group {value!r}; expected NAME=N.")
        name, raw_n = value.rsplit("=", 1)
        try:
            n = int(raw_n)
        except ValueError:
            _fail(f"Invalid group size in {value!r}; N must be an integer.")
        if not name or n < 0:
            _fail(f"Invalid --group {value!r}; name must be nonempty and N nonnegative.")
        result.append({"id": _slug(name), "n": n})
    return result


def _parse_scope(values: list[str]) -> dict[str, str]:
    allowed = {"species", "population", "system", "context", "time"}
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            _fail(f"Invalid --scope {value!r}; expected FIELD=VALUE.")
        field, text = value.split("=", 1)
        field = field.strip()
        text = text.strip()
        if field not in allowed:
            _fail(f"Unknown scope field {field!r}. Choose one of: {', '.join(sorted(allowed))}")
        if not text:
            _fail(f"Scope value for {field!r} must not be empty.")
        result[field] = text
    return result


def _unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-_.").lower()
    if not slug or not slug[0].isalpha():
        slug = f"project-{slug or 'untitled'}"
    return slug


def _fail(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
