from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RuleExplanation:
    rule_id: str
    title: str
    severity: str
    rationale: str
    triggers_when: tuple[str, ...]
    acceptable_evidence: tuple[str, ...]
    does_not_establish: tuple[str, ...]
    remediation: tuple[str, ...]
    example: str
    counterexample: str


RULE_EXPLANATIONS = {
    "PCI-MECH-001": RuleExplanation(
        rule_id="PCI-MECH-001",
        title="Mechanism claim lacks mechanistic-role evidence",
        severity="error",
        rationale=(
            "An association, enrichment, prediction, or colocalization can nominate a mechanism but "
            "does not by itself discriminate the proposed causal route from plausible alternatives."
        ),
        triggers_when=(
            "an active claim has type 'mechanism'",
            "the claim has supporting evidence",
            "none of that evidence has a claim-compatible mechanistic role",
        ),
        acceptable_evidence=(
            "perturbation or functional perturbation in the recorded biological context",
            "rescue or reversal that distinguishes the route from alternatives",
            "direct binding, occupancy, or structural evidence for a compatible direct claim",
            "temporally discriminating intervention or lineage evidence for a compatible process claim",
            "target engagement combined with perturbation, functional perturbation, or rescue",
        ),
        does_not_establish=(
            "passing the core gate does not prove the complete mechanism",
            "one role does not expand a claim across species, systems, scales, or time",
            "target engagement alone does not establish functional mediation",
            "motif enrichment, accessibility, correlation, or prediction alone remain hypothesis-generating",
        ),
        remediation=(
            "downgrade the record to an association or explicitly speculative hypothesis",
            "add claim-compatible perturbation, rescue, direct, structural, or temporal evidence",
            "narrow the claim to the biological scale and context actually tested",
            "record competing explanations and a decisive falsification test",
        ),
        example=(
            "A perturbation changes the phenotype, target engagement is confirmed, and a route-specific "
            "rescue reverses the effect in the same experimental context."
        ),
        counterexample=(
            "A motif is enriched and the linked gene is more highly expressed; this nominates a candidate "
            "regulatory mechanism but does not demonstrate direct binding or functional mediation."
        ),
    )
}


def explain_rule(rule_id: str) -> RuleExplanation:
    normalized = rule_id.strip().upper()
    try:
        return RULE_EXPLANATIONS[normalized]
    except KeyError as exc:
        available = ", ".join(sorted(RULE_EXPLANATIONS))
        raise ValueError(f"No detailed explanation for {normalized!r}. Available: {available}") from exc


def explanation_text(explanation: RuleExplanation) -> str:
    sections = [
        f"{explanation.rule_id} — {explanation.title}",
        f"Default severity: {explanation.severity}",
        f"\nRationale\n  {explanation.rationale}",
        _list_section("Triggers when", explanation.triggers_when),
        _list_section("Acceptable evidence", explanation.acceptable_evidence),
        _list_section("Does not establish", explanation.does_not_establish),
        _list_section("Remediation", explanation.remediation),
        f"\nPassing example\n  {explanation.example}",
        f"\nCounterexample\n  {explanation.counterexample}",
    ]
    return "\n".join(sections)


def explanation_json(explanation: RuleExplanation) -> str:
    return json.dumps(asdict(explanation), indent=2, ensure_ascii=False)


def _list_section(title: str, values: tuple[str, ...]) -> str:
    return f"\n{title}\n" + "\n".join(f"  - {value}" for value in values)
