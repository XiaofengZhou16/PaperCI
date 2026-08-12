# Frontier hypothesis design and figure-planning report

## Scope and information completeness

This design is based on the repository README, product contract, architecture,
ProjectSpec, provider implementation, validators, reports, and tests. It is a
system-level design, not an analysis of a particular manuscript. Domain-specific
mechanism quality and experimental feasibility therefore remain `unknown` unless
the project records enough context for an expert or future domain provider.

## Dual-track product contract

```text
recorded evidence
      |
      +--> Claim and Story track: what can responsibly be concluded now?
      |
      +--> Frontier Hypothesis track: what ambitious, falsifiable mechanism is
                                      worth testing next?
```

The second track is not an escape from the first. A hypothesis can use recorded
evidence and claims as anchors, but it is stored separately with status
`speculative`. It cannot become a supported claim or a shortlisted direction merely
because software generated it.

## Hypothesis Card

Every card records:

- a bounded speculative statement and one of three strategies;
- the seed claim, all anchor claims, and all evidence IDs;
- an inference ladder separating `observed`, `inferred`, and `speculative` steps;
- competing explanations and distinct predictions;
- a decisive test with model-specific expected outcomes and an explicit falsifier;
- the minimum evidence-upgrade path and evidence distance;
- a multidimensional research-ambition profile;
- novelty status and traceable literature sources when novelty has actually been
  checked;
- a figure-question plan.

The built-in offline provider generates three scaffolds. In v0.4, decisive-test
text reuses the recorded seed process, connected prerequisite, selected competing
explanation, target-engagement requirement, and rescue logic instead of emitting a
domain-free validation sentence:

1. `mechanistic-deepening`: closest intervention/rescue path from the current
   evidence boundary;
2. `cross-scale-bridge`: a more distant cell-to-context or scale-to-scale bridge;
3. `paradigm-challenge`: a competing mechanism that could overturn the leading
   interpretation.

## Research-ambition profile

The profile keeps dimensions separate:

- conceptual advance;
- explanatory breadth;
- cross-scale reach;
- discriminating power;
- testability;
- feasibility.

These dimensions reflect public high-impact editorial themes such as conceptual
advance, broad implications, surprising conclusions, and importance. For example,
[Nature's public criteria](https://www.nature.com/nature/for-authors/editorial-criteria-and-processes)
emphasize outstanding importance and interdisciplinary interest, while
[Cell's public description](https://info.cell.com/meet-the-editors-at-cell-symposia-towards-sustainable-agriculture)
emphasizes significant conceptual advances or provocative biological questions.
PaperCI does not claim to reproduce either journal's decisions and never sums these
dimensions into a journal-fit or acceptance score.

Offline generation always records novelty as `unchecked`. A checked or potentially
novel status requires a dated assessment and at least one traceable literature
source. Even then it remains an assessment, not proof of priority.

## Figure-question planning

The figure planner is an argumentative map, not fabricated results.

| Priority | Role | Required question | Visual boundary |
|---|---|---|---|
| Must have | Evidence anchor | Which observed results motivate the hypothesis? | Only existing evidence; solid links |
| Must have | Mechanism model | Which unverified links connect evidence to mechanism? | Speculative nodes and links visibly distinct |
| Must have | Discriminating test | Which result separates the leading models? | Show both model-specific expected outcomes |
| Recommended | Boundary | What would falsify or narrow the hypothesis? | Failure and null outcomes remain visible |

No generated mechanism diagram may depict an untested node as an observed result.
Future figure renderers should use solid edges for evidenced relations and dashed
edges for speculative transitions, with IDs retained for auditability.

## Safety and evaluation invariants

- Generated hypotheses may reference only evidence and claims in their run manifest.
- Generated status is always `speculative`.
- `shortlisted` requires a human `select` ReviewEvent.
- At least one alternative and one decisive falsifiable test are mandatory.
- Current claims are never modified or created by hypothesis generation.
- Comparison may prioritize the next human review but cannot label a hypothesis
  scientifically best, novel, journal-ready, or likely to be published.
- A useful provider must improve domain specificity without worsening invented
  references, hidden inference jumps, or falsifiability.
