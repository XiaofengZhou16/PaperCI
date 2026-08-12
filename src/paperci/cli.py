from __future__ import annotations

import platform
import re
import sys
from pathlib import Path
from typing import Optional

import typer
from jsonschema import Draft202012Validator

from paperci import __version__
from paperci.engine import validate_project
from paperci.errors import PaperCIError
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
    version: Optional[bool] = typer.Option(
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
    destination: Path = typer.Argument(Path("."), help="Directory in which to create paperci.yaml."),
    project_id: Optional[str] = typer.Option(None, "--id", help="Stable project identifier."),
    title: Optional[str] = typer.Option(None, "--title", help="Human-readable project title."),
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
    typer.echo("Next: paperci add && paperci lint && paperci report -o paperci-report.md")


@app.command("add")
def add_command(
    project: Path = typer.Argument(Path("."), help="Project file or directory."),
    statement: Optional[str] = typer.Option(
        None,
        "--statement",
        "-s",
        help="A bounded statement of what was observed.",
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        help="Local path, URL, DOI, or notes URI for the source.",
    ),
    locator: Optional[str] = typer.Option(
        None,
        "--locator",
        help="Row, table, figure panel, cell, or equivalent locator.",
    ),
    kind: str = typer.Option("quantitative_result", help="Evidence kind."),
    unit_of_analysis: Optional[str] = typer.Option(
        None,
        "--unit-of-analysis",
        help="Independent unit, for example mouse or participant.",
    ),
    group: Optional[list[str]] = typer.Option(
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
    typer.echo("Edit the YAML to add effect, uncertainty, scope, or limitations; then run paperci lint.")


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
    output: Optional[Path] = typer.Option(
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
    output: Optional[Path] = typer.Option(
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
    project: Optional[Path] = typer.Argument(None, help="Optional project file or directory."),
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
    checks.append(("Offline core", True, "validate/lint/report import no network client"))
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
        raise AssertionError("unreachable")


def _load_or_fail(project: Path) -> ProjectDocument:
    try:
        return load_project(project)
    except PaperCIError as exc:
        _fail(str(exc))
        raise AssertionError("unreachable")


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
