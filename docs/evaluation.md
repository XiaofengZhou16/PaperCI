# Story evaluation

## Why there is no single story score

A scalar score would hide unacceptable trade-offs. A creative story can be weakly
supported; a rigorous story can be too incremental; a broad story can overgeneralize.
PaperCI therefore separates hard validity gates from a comparative scorecard.

Stories with error-level hard-gate failures are not ranked as submission-ready.
They may remain visible as hypotheses or high-risk arcs.

## Comparative scorecard

Each dimension uses an ordinal four-level rubric and includes a rationale plus
evidence/claim references.

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Conceptual advance | restates results | incremental relation | changes local model | reframes a broader problem |
| Coherence | disconnected | several unsupported jumps | mostly continuous path | every major transition is explicit |
| Causal depth | descriptive only | causal language, weak design | partial intervention chain | discriminating perturbation and alternatives addressed |
| Convergent evidence | one fragile modality | repeated same-modality result | orthogonal support | independent modalities across relevant scales |
| Alternative resistance | alternatives absent | named only | some alternatives tested | major alternatives discriminated |
| Audience breadth | project-specific | narrow subfield | multiple adjacent fields | clear general principle with bounded scope |
| Figure economy | redundant or meandering | major compression needed | mostly efficient | each figure changes the reader's model |
| Coverage | major claims unlinked | several weak links | central path supported | central and boundary claims fully traceable |

These levels are comparative decision aids, not probabilities or universal measures
of scientific quality.

## Arc diversity contract

When enough distinct eligible claims exist, `paperci propose --arcs 3` must return
different scientific commitments, not three title rewrites. The default strategies
are:

1. **Evidence-conservative:** prefer the strongest arc that passes current hard
   gates; if none passes, expose the least-burden supported option as failing.
2. **High-risk/high-reward:** most consequential supported hypothesis, with blocked
   claims and current gates visible.
3. **Minimum-gap:** alternative claim path with the smallest current gate/gap burden.

Two arcs are insufficiently distinct when they share the same central claim, claim
path, principal alternative, and central gap. A deterministic diversity check can
reject such output before model judging.

## Red-team roles

Model reviewers receive the same structured project but distinct bounded tasks:

- **Evidence auditor:** finds unsupported transitions and source mismatches;
- **Causal skeptic:** proposes non-causal and reverse-causal explanations;
- **Mechanism skeptic:** distinguishes pathway plausibility from demonstrated steps;
- **Statistical reviewer:** checks unit, estimand, uncertainty, missingness, and multiplicity;
- **Generalist editor:** tests conceptual importance and accessibility;
- **Reproducibility reviewer:** asks whether another team can locate and regenerate evidence.

Their findings remain separate. A consensus summary must preserve minority objections
and cannot erase a deterministic failure.

## Human evaluation protocol

Benchmark experts compare two anonymized arcs against the same evidence packet.
They answer concrete questions:

1. Which central claim is better supported?
2. Which arc teaches the more important bounded lesson?
3. Which arc better represents contradictory evidence?
4. Which proposed experiment most cleanly separates the leading explanations?
5. What is the first claim you would soften or reject?

Reviewers may choose “tie” or “both unacceptable.” Agreement statistics and raw
disagreement distributions are reported; majority vote is not treated as ground
truth for genuinely interpretive judgments.

## Model-upgrade evaluation

When a new model becomes available, the benchmark reruns a frozen suite and reports:

- hard-rule violation rate;
- invented-reference rate;
- sensitivity to added counterevidence;
- expert pairwise preference by story strategy;
- arc diversity;
- uncertainty calibration;
- latency, cost, and disclosed input volume.

An upgrade is not adopted by default if it improves prose preference while worsening
evidence integrity. Provider defaults change through a versioned decision record.
