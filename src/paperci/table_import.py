from __future__ import annotations

import copy
import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from paperci.project import ProjectDocument, next_identifier

EVIDENCE_KINDS = {
    "quantitative_result",
    "qualitative_observation",
    "figure_panel",
    "table",
    "dataset",
    "analysis_output",
    "external_source",
}
IMPORT_EXTENSION = "org.paperci.import.v1"


class TableImportError(ValueError):
    """Raised when a table cannot be imported without guessing its meaning."""


@dataclass(frozen=True, slots=True)
class TableImportResult:
    document: ProjectDocument
    manifest: dict[str, Any]
    evidence: tuple[dict[str, Any], ...]


def import_table(
    document: ProjectDocument,
    table: Path,
    *,
    statement_column: str,
    locator_column: str | None = None,
    kind: str = "quantitative_result",
    kind_column: str | None = None,
    unit_column: str | None = None,
    delimiter: str = "auto",
) -> TableImportResult:
    if kind not in EVIDENCE_KINDS:
        raise TableImportError(f"Unknown evidence kind {kind!r}.")
    path = table.expanduser().resolve()
    if not path.is_file():
        raise TableImportError(f"Table does not exist: {path}")
    separator, delimiter_name = _delimiter(path, delimiter)
    digest = _sha256(path)
    source_uri = _source_uri(document.root, path)
    columns = {
        "statement": statement_column,
        "locator": locator_column,
        "kind": kind_column,
        "unit_of_analysis": unit_column,
    }
    columns = {field: column for field, column in columns.items() if column}

    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise TableImportError(f"Cannot read table {path}: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle, delimiter=separator)
        if not reader.fieldnames:
            raise TableImportError("Table has no header row.")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise TableImportError("Table contains duplicate column names.")
        missing = sorted(set(columns.values()) - set(reader.fieldnames))
        if missing:
            raise TableImportError(f"Mapped column(s) not found: {', '.join(missing)}")
        rows: list[tuple[int, dict[str, str]]] = []
        for row in reader:
            if None in row:
                raise TableImportError(
                    f"Row {reader.line_num} contains more values than the header defines."
                )
            normalized = {str(key): str(value or "").strip() for key, value in row.items()}
            if not any(normalized.values()):
                continue
            rows.append((reader.line_num, normalized))
    if not rows:
        raise TableImportError("Table contains no non-empty data rows.")

    data = copy.deepcopy(document.data)
    evidence = data.setdefault("evidence", [])
    if not isinstance(evidence, list):
        raise TableImportError("Project field 'evidence' is not a list; run paperci validate.")
    extensions = data.setdefault("extensions", {})
    if not isinstance(extensions, dict):
        raise TableImportError("Project field 'extensions' is not an object; run paperci validate.")
    import_extension = extensions.setdefault(IMPORT_EXTENSION, {"runs": []})
    if not isinstance(import_extension, dict):
        raise TableImportError(f"Project extension {IMPORT_EXTENSION!r} is not an object.")
    runs = import_extension.setdefault("runs", [])
    if not isinstance(runs, list):
        raise TableImportError(f"Project extension {IMPORT_EXTENSION!r}.runs is not a list.")

    signature = {
        "sha256": digest,
        "columns": columns,
        "default_kind": kind,
        "delimiter": delimiter_name,
    }
    if any(
        isinstance(run, dict)
        and all(run.get(field) == value for field, value in signature.items())
        for run in runs
    ):
        raise TableImportError(
            "An identical table and column mapping were already imported; change the mapping or source."
        )

    import_id = next_identifier(runs, "IMPORT")
    imported: list[dict[str, Any]] = []
    for line_number, row in rows:
        statement = row[statement_column]
        if not statement:
            raise TableImportError(
                f"Mapped statement column {statement_column!r} is empty at row {line_number}."
            )
        row_kind = row[kind_column] if kind_column else kind
        if row_kind not in EVIDENCE_KINDS:
            raise TableImportError(f"Unknown evidence kind {row_kind!r} at row {line_number}.")
        locator = row[locator_column] if locator_column else f"row={line_number}"
        if not locator:
            raise TableImportError(
                f"Mapped locator column {locator_column!r} is empty at row {line_number}."
            )
        record: dict[str, Any] = {
            "id": next_identifier([*evidence, *imported], "E"),
            "kind": row_kind,
            "statement": statement,
            "status": "draft",
            "source": {
                "uri": source_uri,
                "locator": locator,
                "sha256": digest,
                "media_type": (
                    "text/tab-separated-values" if separator == "\t" else "text/csv"
                ),
                "generated_by": "paperci import-table",
            },
            "extensions": {
                IMPORT_EXTENSION: {
                    "import_id": import_id,
                    "row": line_number,
                    "verification": "unverified",
                }
            },
        }
        if unit_column and row[unit_column]:
            record["design"] = {
                "family": "unknown",
                "unit_of_analysis": row[unit_column],
            }
        imported.append(record)

    manifest: dict[str, Any] = {
        "id": import_id,
        "source_uri": source_uri,
        **signature,
        "imported_ids": [record["id"] for record in imported],
        "row_count": len(imported),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    evidence.extend(imported)
    runs.append(manifest)
    return TableImportResult(
        document=ProjectDocument(path=document.path, data=data),
        manifest=manifest,
        evidence=tuple(imported),
    )


def _delimiter(path: Path, value: str) -> tuple[str, str]:
    normalized = value.casefold()
    if normalized == "auto":
        normalized = "tsv" if path.suffix.casefold() in {".tsv", ".tab"} else "csv"
    if normalized == "csv":
        return ",", "csv"
    if normalized == "tsv":
        return "\t", "tsv"
    raise TableImportError("--delimiter must be auto, csv, or tsv.")


def _source_uri(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
