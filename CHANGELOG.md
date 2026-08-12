# Changelog

All notable changes to PaperCI will be documented here. The project follows
Semantic Versioning for the Python package; the public data specification has its
own version declared by `spec_version`.

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
