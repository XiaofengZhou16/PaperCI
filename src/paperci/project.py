from __future__ import annotations

import json
import sysconfig
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from paperci.errors import ProjectLoadError, ProjectNotFoundError, SchemaNotFoundError

PROJECT_FILENAMES = ("paperci.yaml", "paperci.yml", "paperci.json")


@dataclass(slots=True)
class ProjectDocument:
    path: Path
    data: dict[str, Any]

    @property
    def root(self) -> Path:
        return self.path.parent

    @property
    def mode(self) -> str:
        project = self.data.get("project", {})
        return project.get("mode", "sketch") if isinstance(project, dict) else "sketch"

    @property
    def project_id(self) -> str:
        project = self.data.get("project", {})
        return project.get("id", "unknown") if isinstance(project, dict) else "unknown"

    @property
    def title(self) -> str:
        project = self.data.get("project", {})
        return (
            project.get("title", self.project_id) if isinstance(project, dict) else self.project_id
        )


def resolve_project_path(value: str | Path = ".") -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    if candidate.is_dir():
        for name in PROJECT_FILENAMES:
            project_file = candidate / name
            if project_file.is_file():
                return project_file.resolve()
        expected = ", ".join(PROJECT_FILENAMES)
        raise ProjectNotFoundError(
            f"No PaperCI project in {candidate.resolve()} (expected {expected})."
        )
    raise ProjectNotFoundError(f"Project path does not exist: {candidate}")


def load_project(value: str | Path = ".") -> ProjectDocument:
    path = resolve_project_path(value)
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ProjectLoadError(f"Cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectLoadError(f"Project root must be a mapping/object: {path}")
    return ProjectDocument(path=path, data=data)


def save_project(document: ProjectDocument) -> None:
    path = document.path
    if path.suffix.lower() == ".json":
        text = json.dumps(document.data, indent=2, ensure_ascii=False) + "\n"
    else:
        text = yaml.safe_dump(
            document.data,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    path.write_text(text, encoding="utf-8")


def find_schema_path() -> Path:
    source_tree = Path(__file__).resolve().parents[2] / "spec" / "paperci.schema.json"
    installed = Path(sysconfig.get_path("data")) / "share" / "paperci" / "paperci.schema.json"
    for candidate in (source_tree, installed):
        if candidate.is_file():
            return candidate
    raise SchemaNotFoundError(
        "Cannot locate paperci.schema.json. Reinstall PaperCI or run it from the source tree."
    )


def load_schema() -> dict[str, Any]:
    path = find_schema_path()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaNotFoundError(f"Cannot load schema at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaNotFoundError(f"Schema root must be an object: {path}")
    return value


def empty_project(project_id: str, title: str, mode: str = "sketch") -> dict[str, Any]:
    return {
        "spec_version": "0.3",
        "project": {
            "id": project_id,
            "title": title,
            "mode": mode,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        "evidence": [],
        "claims": [],
        "stories": [],
        "hypotheses": [],
        "reviews": [],
        "runs": [],
    }


def next_identifier(items: list[Any], prefix: str) -> str:
    used = {
        item.get("id")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    number = 1
    while f"{prefix}{number:03d}" in used:
        number += 1
    return f"{prefix}{number:03d}"
