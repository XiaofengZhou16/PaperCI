# Changelog

All notable changes to PaperCI will be documented here. The project follows
Semantic Versioning for the Python package; the public data specification has its
own version declared by `spec_version`.

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
