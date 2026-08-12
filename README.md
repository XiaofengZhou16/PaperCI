# PaperCI

**Continuous integration for scientific stories.**

[![CI](https://github.com/XiaofengZhou16/PaperCI/actions/workflows/ci.yml/badge.svg)](https://github.com/XiaofengZhou16/PaperCI/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

PaperCI helps researchers answer one difficult question:

> Given the results we actually have, what is the strongest scientific story we can responsibly tell?

It converts experimental results into traceable evidence cards, proposes competing
paper arcs, tests every claim against its evidence, and identifies the smallest set
of experiments that would resolve the most important remaining uncertainty.

PaperCI is designed to improve when foundation models improve. Models may propose
better interpretations and stories; the project owns the stable evidence format,
claim rules, provenance, evaluation cases, and human review workflow.

## The first useful workflow

```text
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -e .

$ paperci init
$ paperci add
  What was compared?      HFD vs control in bone-marrow GMPs
  What was measured?      Cxcl16 expression
  What happened?          Higher in HFD
  How certain is it?      n=5/group; effect and CI in results/cxcl16.csv
  Where is the source?    results/cxcl16.csv#row=18

$ paperci propose --arcs 3
$ paperci lint
$ paperci report
```

For a non-interactive smoke test from this repository:

```bash
paperci doctor examples/minimal-project.yaml
paperci validate examples/minimal-project.yaml
paperci lint examples/minimal-project.yaml --fail-on never
paperci report examples/minimal-project.yaml -o paperci-report.md
```

The example intentionally contains an overstated mechanism claim. `paperci lint`
should flag `PCI-MECH-001`; that failure demonstrates the evidence boundary rather
than a broken example.

The report contains:

- three meaningfully different story arcs;
- the evidence path behind every major claim;
- unsupported, overstated, or contradictory claims;
- a proposed Figure 1–6 sequence;
- alternative explanations that remain open;
- experiments ranked by how much uncertainty they would resolve.

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

## Repository design package

- [Product contract](docs/product.md)
- [Technical architecture](docs/architecture.md)
- [Open specification](docs/specification.md)
- [Core lint rules](docs/rules.md)
- [Story evaluation](docs/evaluation.md)
- [Ecosystem and differentiation](docs/ecosystem.md)
- [MVP and roadmap](docs/roadmap.md)
- [Community and governance](docs/community.md)
- [Combined JSON Schema](spec/paperci.schema.json)
- [Minimal example](examples/minimal-project.yaml)

The repository now contains the Milestone 1 Python core and CLI. Model-assisted
competing-story generation remains a Milestone 2 feature; current validation and
reporting are deterministic and offline.

## Commands

| Command | Purpose | Network |
|---|---|---|
| `paperci init` | Create a readable `paperci.yaml` | Never |
| `paperci add` | Add a draft evidence card | Never |
| `paperci validate` | Check schema, references, sources, hashes, and promotion | Never |
| `paperci lint` | Apply deterministic scientific-story rules | Never |
| `paperci report` | Render a Markdown decision report | Never |
| `paperci doctor` | Check installation and project health | Never |

`paperci lint --format sarif` can feed findings into GitHub or another SARIF-aware
code-review system. CI may use `--fail-on error`; exploratory work may use
`--fail-on never` while retaining every finding.

## Project status

**Pre-alpha / v0.1.0a1.** The offline CLI is implemented and tested; field semantics
and plugin boundaries remain open for RFC discussion. No output should be used in
a submission without independent scientific review.

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
