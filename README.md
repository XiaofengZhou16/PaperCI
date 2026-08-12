# PaperCI

**Continuous integration for evidence-backed scientific stories and hypotheses.**

[![CI](https://github.com/XiaofengZhou16/PaperCI/actions/workflows/ci.yml/badge.svg)](https://github.com/XiaofengZhou16/PaperCI/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

PaperCI helps researchers answer two linked questions:

> Given the results we actually have, what is the strongest scientific story we can responsibly tell?

> Which ambitious, falsifiable mechanisms are worth testing next without pretending they are already established?

It converts experimental results into traceable evidence cards, proposes competing
paper arcs, tests every claim against its evidence, and makes the most important
remaining uncertainties explicit for human review. A separate frontier track turns
those boundaries into speculative Hypothesis Cards with competing explanations,
predictions, falsifiers, decisive tests, and evidence-upgrade paths.

PaperCI is designed to improve when foundation models improve. Models may propose
better interpretations and stories; the project owns the stable evidence format,
claim rules, provenance, evaluation cases, and human review workflow.

## Try it in two minutes

PaperCI is pre-alpha. Install the current pre-release from PyPI, then create a
complete synthetic project without an API key or network call:

```bash
$ python -m venv .venv
$ source .venv/bin/activate
$ python -m pip install --pre paperci
$ paperci demo
$ cd paperci-demo
$ paperci lint --fail-on never
$ paperci compare
$ paperci compare-hypotheses
```

The demo creates two synthetic result files, traceable evidence and claims, three
competing stories, three frontier hypotheses, generation manifests, and
`paperci-report.md`. It intentionally contains an overstated mechanism claim.
`paperci lint` flags `PCI-MECH-001`; the frontier track retains ambitious mechanisms
as explicitly speculative and falsifiable research directions.

See the [ten-minute pilot](docs/pilot.md) to evaluate PaperCI with a safe synthetic
case and report first-run friction.

## Build a project manually

From a source checkout installed with `python -m pip install -e .`:

```text
$ paperci init demo --id demo-study --title "Demo study"
$ paperci add demo --statement "Target expression was higher after exposure." \
    --source notes://pilot --locator result-1
$ paperci claim demo --text "Exposure is associated with higher target expression." \
    --type association --strength supports --support E001
$ paperci claim demo --text "Exposure directly activates the target mechanism." \
    --type mechanism --strength demonstrates --support E001
$ paperci propose demo --arcs 3
$ paperci lint demo --fail-on never
$ paperci compare demo
$ paperci hypothesize demo --count 3
$ paperci compare-hypotheses demo
$ paperci report demo -o demo/paperci-report.md
```

For a non-interactive smoke test from this repository:

```bash
paperci doctor examples/minimal-project.yaml
paperci validate examples/minimal-project.yaml
paperci propose examples/minimal-project.yaml --arcs 3 --dry-run
paperci lint examples/minimal-project.yaml --fail-on never
paperci compare examples/minimal-project.yaml
paperci hypothesize examples/minimal-project.yaml --count 3 --dry-run
paperci report examples/minimal-project.yaml -o paperci-report.md
```

The repository example also intentionally contains the same overstated mechanism
claim, so `paperci lint` should flag `PCI-MECH-001`.

The report contains:

- distinct candidate arcs when the claim register supports different commitments;
- the evidence path behind every major claim;
- unsupported, overstated, or contradictory claims;
- a figure-question sequence linked to existing evidence and claims;
- alternative explanations that remain open;
- explicit gaps, run provenance, and human-review boundaries.

## Three adoption modes

| Mode | Input | Promise |
|---|---|---|
| `sketch` | Short result notes | Fast story exploration; everything remains unverified |
| `verified` | Notes plus source locators and review | Traceable claims suitable for team discussion |
| `connected` | Analysis-pipeline adapters | Re-runnable evidence updates and CI checks |

The user can start in `sketch` and progressively add provenance. A perfect data
model is not a prerequisite for receiving value.

## What PaperCI is not

- not a journal acceptance predictor;
- not a replacement for domain experts, statisticians, or reviewers;
- not an autonomous manuscript factory;
- not permission to promote association, motif enrichment, or prediction into causality;
- not a system that silently uploads unpublished results.

## Design principles

1. **Evidence before eloquence.** A fluent claim with weak support still fails.
2. **Competing stories, not one confident answer.** The system exposes trade-offs.
3. **Hard gates before taste.** Validity is pass/fail; editorial appeal is comparative.
4. **Local first.** Core inspection and linting work without a network or model API.
5. **Model agnostic.** Model adapters are replaceable and all runs are recorded.
6. **Git friendly.** Canonical YAML/JSON is readable, diffable, and reviewable.
7. **Human promotion.** Generated evidence and claims never self-verify.
8. **Dual-track reasoning.** Current claims and frontier hypotheses remain separate records.
9. **No journal score.** Ambition is multidimensional; novelty and publication fit require review.

## Repository design package

- [Product contract](docs/product.md)
- [Technical architecture](docs/architecture.md)
- [Open specification](docs/specification.md)
- [Core lint rules](docs/rules.md)
- [Story evaluation](docs/evaluation.md)
- [Ecosystem and differentiation](docs/ecosystem.md)
- [MVP and roadmap](docs/roadmap.md)
- [Release process](docs/releasing.md)
- [Community and governance](docs/community.md)
- [Combined JSON Schema](spec/paperci.schema.json)
- [Minimal example](examples/minimal-project.yaml)

The repository contains the local evidence-bound story workflow plus an offline
frontier-hypothesis baseline. The built-in hypothesis provider creates transparent
research scaffolds; it does not search literature, nominate a named molecular actor
that is absent from the input, or predict journal acceptance. Remote and local
foundation-model adapters remain future work.

## Commands

| Command | Purpose | Network |
|---|---|---|
| `paperci demo` | Create and run a complete synthetic example | Never |
| `paperci init` | Create a readable `paperci.yaml` | Never |
| `paperci add` | Add a draft evidence card | Never |
| `paperci claim` | Add an evidence-linked candidate claim | Never |
| `paperci propose` | Generate bounded candidate arcs with the built-in provider | Never |
| `paperci compare` | Compare active arcs by gates and coverage signals | Never |
| `paperci hypothesize` | Generate evidence-anchored, falsifiable frontier hypotheses | Never |
| `paperci compare-hypotheses` | Compare ambition dimensions without a journal score | Never |
| `paperci validate` | Check schema, references, sources, hashes, and promotion | Never |
| `paperci lint` | Apply deterministic scientific-story rules | Never |
| `paperci report` | Render a Markdown decision report | Never |
| `paperci doctor` | Check installation and project health | Never |

`paperci lint --format sarif` can feed findings into GitHub or another SARIF-aware
code-review system. CI may use `--fail-on error`; exploratory work may use
`--fail-on never` while retaining every finding.

## Project status

**Pre-alpha / v0.3.0a2.** The offline CLI separates evidence-bound claims from
frontier hypotheses. Hypothesis novelty remains `unchecked` unless a dated,
traceable literature assessment is recorded. No output should be used in a
submission or experimental decision without independent scientific review.

## License

Code, schemas, tests, and repository documentation are licensed under Apache-2.0.
Imported benchmark artifacts retain their source-specific licenses and must include
a case manifest before public redistribution. See [LICENSE](LICENSE).

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Scientific rules require failing and
passing fixtures, an actionable remediation, known exceptions, and review ownership.
Security or privacy concerns should follow [SECURITY.md](SECURITY.md), not a public
issue containing unpublished data.

Repository: [github.com/XiaofengZhou16/PaperCI](https://github.com/XiaofengZhou16/PaperCI)
