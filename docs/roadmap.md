# MVP and roadmap

## Release strategy

PaperCI should earn adoption in layers. The first release is a trustworthy linter
and story comparator, not a broad autonomous research platform.

## Milestone 0 — specification and fixtures

**Goal:** make the core contract reviewable before implementation hardens it.

Deliverables:

- versioned combined JSON Schema;
- five minimal projects covering experimental, observational, omics, null, and
  contradictory evidence;
- ten initial deterministic rule definitions;
- RFC template and compatibility policy;
- license decision and code of conduct;
- one public design partner case with reusable licensing.

Exit criteria:

- two independent researchers can author a valid project from the documentation;
- unknown information can be represented without fake precision;
- all identifiers and source links survive a round trip through YAML and JSON.

## Milestone 1 — useful local CLI

**Goal:** useful without an API key.

Commands:

```text
paperci init
paperci add
paperci validate
paperci lint
paperci report
paperci doctor
```

Deliverables:

- typed models and schema validation;
- interactive evidence-card entry;
- Markdown report;
- at least ten hard rules;
- local file hash and source-locator checks;
- offline guarantee and tests;
- SARIF output;
- deterministic fake provider for plugin tests.

Exit criteria:

- installation from PyPI in one command;
- first report within ten minutes for a six-card project;
- Windows, macOS, and Linux CI;
- no network calls during the offline test suite;
- actionable error messages for all fixture failures.

## Milestone 2 — competing story generation

**Goal:** use models where they add value while retaining deterministic boundaries.

Commands:

```text
paperci propose --arcs 3
paperci compare
paperci redteam
```

Deliverables:

- one OpenAI-compatible remote adapter;
- one documented local-model adapter;
- outbound-data preview and redaction;
- structured-output repair with a strict retry budget;
- arc-diversity checks to prevent three paraphrases of one story;
- model-run manifests and cost display;
- “conservative,” “high-risk/high-reward,” and “minimum-new-experiment” strategies.

Exit criteria:

- every generated claim refers only to existing evidence or is explicitly marked
  as a hypothesis;
- hard lint results are provider-independent;
- replacing a model requires configuration, not core changes;
- no model output can self-promote to verified.

## Milestone 3 — first domain pack

**Goal:** demonstrate depth in mechanistic biomedicine without making the core
biomedical-only.

Initial rules:

- association versus intervention;
- motif enrichment versus TF binding;
- accessibility versus gene regulation;
- cell abundance versus cell-state expression;
- technical versus biological replicate;
- pseudoreplication and invalid pairing;
- mechanism requirements for perturbation, rescue, orthogonal support, and scope;
- cohort association versus clinical prediction and causality.

Deliverables:

- CSV and common differential-result importers;
- figure-panel evidence cards;
- mechanistic biology profile;
- public, license-clean case suite;
- expert adjudication guide.

Exit criteria:

- at least five external domain reviewers;
- false-positive and false-negative analysis for every error-level rule;
- at least one independent plugin contribution.

## Milestone 4 — connected research workflow

**Goal:** make story checks rerunnable when results change.

Potential integrations:

- Jupyter and Quarto;
- Snakemake and Nextflow manifests;
- RO-Crate export;
- GitHub and GitLab annotations;
- lightweight local web viewer;
- manuscript claim import and bidirectional linking.

The web UI should follow proven CLI usage instead of defining a second data model.

## Benchmark: PaperCI Bench

### Task families

1. **Entailment:** does evidence support the claim as written?
2. **Overclaim:** identify the smallest unsupported increase in type, strength, or scope.
3. **Contradiction:** update a story when counterevidence is added.
4. **Arc construction:** produce distinct, coherent claim paths from the same evidence.
5. **Gap selection:** choose an experiment that separates competing explanations.
6. **Provenance integrity:** preserve source IDs, locators, and uncertainty.
7. **Model upgrade:** measure what improves and what regresses under a new provider.

### Evaluation layers

- exact deterministic checks for schema and provenance;
- rule-level precision/recall for known boundary violations;
- blinded expert pairwise preference for story utility;
- calibration of uncertainty labels;
- counterevidence sensitivity rather than only polished final output;
- cost, latency, and amount of disclosed input.

Do not collapse these into one leaderboard number. A model may be creative but
unsafe, conservative but unhelpful, or accurate but too expensive.

### Case policy

- start with synthetic cases designed to isolate one rule;
- add open-data cases with explicit artifact licenses;
- never redistribute publisher figures without permission;
- allow private local cases for self-evaluation without leaderboard upload;
- retain expert disagreements as labels rather than forcing false consensus;
- version case revisions immutably.

## Pilot plan

Recruit five design partners representing:

- wet-lab mechanistic biology;
- clinical cohort analysis;
- single-cell or multi-omics;
- a non-biomedical experimental field;
- a methods or statistics group.

Each partner runs two sessions:

1. initial six-card story exploration;
2. rerun after adding or changing evidence.

Measure setup time, abandoned fields, accepted/rejected findings, changed story
decisions, disclosure concerns, and return use. Do not ask only whether the output
“looks good.”

## Explicit deferrals

The following are attractive but premature before Milestone 3:

- autonomous manuscript generation;
- general literature novelty scoring;
- a hosted multi-tenant SaaS;
- fine-tuning a proprietary story model;
- journal-specific acceptance scores;
- automatic execution of proposed experiments or analysis code.
