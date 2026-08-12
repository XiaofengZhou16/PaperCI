from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    NOTE = 1
    WARNING = 2
    ERROR = 3

    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: Severity
    target: str
    message: str
    remediation: str
    path: str | None = None
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["severity"] = self.severity.label()
        value["evidence_ids"] = list(self.evidence_ids)
        return value


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda item: (-int(item.severity), item.rule_id, item.target, item.message),
    )


def counts(findings: list[Finding]) -> dict[str, int]:
    result = {"error": 0, "warning": 0, "note": 0}
    for finding in findings:
        result[finding.severity.label()] += 1
    return result
