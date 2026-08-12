# Changelog

All notable changes to PaperCI will be documented here. The project follows
Semantic Versioning for the Python package; the public data specification has its
own version declared by `spec_version`.

## 0.4.0a1 — 2026-08-13

Nature benchmark-driven reasoning upgrade:

- ProjectSpec `0.4` adds acyclic `claim.depends_on` links and explicit nested-design
  fields (`design.parent_unit` and `group.clusters`), while retaining read
  compatibility for `0.1`–`0.3` projects;
- `PCI-REL-001` rejects an evidence record linked as both support and challenge;
- `PCI-SEM-001` blocks the tested cellular-to-organismal inheritance and
  tumour-outgrowth-to-initiation category errors;
- `PCI-STAT-003` exposes missing parent units and cluster counts for nested outcomes;
- lineage tracing and five additional mechanistic evidence roles no longer fail the
  mechanism gate solely because the core vocabulary was incomplete;
- the deterministic story provider follows claim dependencies in topological order
  and can emit long, auditable evidence-to-mechanism chains;
- frontier hypothesis tests now name the recorded process, connected claim, selected
  competing explanation, target engagement, and rescue logic;
- nine core regression tests reproduce the failures observed in the Nagaraja et al.
  Nature benchmark.

## 0.3.0a2 — 2026-08-13

Adoption-readiness pre-release:

- reproducible PyPI publishing through a dedicated Trusted Publishing workflow;
- release-tag and package-version consistency checks before publication;
- wheel and source-distribution metadata checks and clean-install smoke tests;
- PyPI-first installation instructions for the synthetic pilot;
- version-neutral bug and first-run forms plus feature-request and RFC entry points;
- private vulnerability-reporting guidance aligned with the enabled repository setting.

This release does not change ProjectSpec semantics or add scientific rules.

## 0.3.0a1 — 2026-08-13

Dual-track evidence and frontier-hypothesis baseline:

- ProjectSpec `0.3` adds a distinct Hypothesis Card while retaining read
  compatibility for `0.1` and `0.2` projects;
- offline `hypothesize` command with mechanistic-deepening, cross-scale-bridge,
  and paradigm-challenge strategies;
- explicit observed, inferred, and speculative reasoning steps linked only to
  recorded evidence and claims;
- competing explanations, predictions, falsifiers, expected outcomes, decisive
  tests, and minimum evidence-upgrade paths;
- multidimensional research-ambition profiles without a scalar impact, journal-fit,
  novelty, or publication-probability score;
- novelty locked to `unchecked` in offline generation; checked novelty requires a
  dated assessment and at least one traceable literature source;
- `compare-hypotheses` and a dedicated report section that keeps hypotheses separate
  from supported claims;
- hypothesis run manifests, input-boundary enforcement, idempotency, superseding,
  and human-only shortlisting checks.

## 0.2.0a1 — 2026-08-13

Offline competing-story baseline:

- one-command `paperci demo` onboarding with synthetic artifacts, three competing
  arcs, a run manifest, and a Markdown report;
- `claim` command for evidence-linked candidate claims;
- deterministic `propose` provider with evidence-conservative, high-risk-hypothesis,
  and minimum-gap strategies;
- idempotent proposal runs with provider identity, input hash, exact input manifest,
  parameters, outputs, and timestamp;
- generated-story input-boundary enforcement through `PCI-AI-001`;
- ProjectSpec `0.2` with read compatibility for `0.1` projects;
- `compare` command using hard-gate status and transparent coverage signals, without
  a synthetic scientific-quality score;
- proposal-run and strategy details in Markdown reports;
- dry-run, forced regeneration, superseding, and cross-reference tests.

## 0.1.0a1 — 2026-08-12

Initial pre-alpha implementation:

- offline `init`, `add`, `validate`, `lint`, `report`, and `doctor` commands;
- PaperCI ProjectSpec `0.1` JSON Schema;
- evidence, claim, story, gap, and review records;
- structural, provenance, statistical, scope, causal, mechanism, contradiction,
  and story rules;
- text, JSON, Markdown, and SARIF outputs;
- human-only promotion constraint;
- intentionally failing mechanistic-biology example;
- cross-platform CI and wheel packaging.
