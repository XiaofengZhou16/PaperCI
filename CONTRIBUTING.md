# Contributing to PaperCI

Thank you for helping make scientific stories more inspectable and evidence-bound.
Contributions from researchers, statisticians, research-software engineers,
maintainers, designers, and documentation writers are welcome.

## Development setup

PaperCI requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check src tests
pytest
paperci doctor examples/minimal-project.yaml
```

The core test suite must run without an API key and without network access.

## Good first contributions

- improve a user-facing error or remediation;
- add a passing or failing fixture for an existing rule;
- document a false positive or disciplinary exception;
- improve Markdown or SARIF output;
- test installation on another operating system;
- add an example that contains only redistributable artifacts.

## Adding or changing a rule

A rule pull request must include:

1. a stable rule ID and default severity;
2. a minimal failing fixture;
3. a nearby passing fixture;
4. a scientific rationale and primary source when applicable;
5. actionable remediation text;
6. known exceptions and false positives;
7. tests showing that unrelated claims are not flagged;
8. a proposed owner and expert review date for domain rules.

Core rules must be broadly applicable. Assay-, discipline-, or design-specific
rules belong in a rule-pack plugin.

## Changing the specification

Changes to `spec/paperci.schema.json`, field semantics, identifier behavior,
promotion permissions, or plugin contracts require an RFC before implementation.
An RFC should include compatibility impact, migration behavior, examples, and at
least two realistic use cases.

Patch changes may clarify documentation or error messages without changing which
projects validate. New optional fields normally require a minor spec version.
Breaking semantics require a major spec version and migration command.

## Pull requests

- keep each pull request focused;
- add or update tests;
- do not require paid model credentials for core checks;
- do not include unpublished or identifying research data;
- state how generated files are regenerated;
- update documentation when behavior changes;
- retain uncertainty and expert disagreement rather than forcing consensus labels.

Run before requesting review:

```bash
ruff check src tests
pytest
python -m compileall -q src tests
paperci validate examples/minimal-project.yaml
paperci lint examples/minimal-project.yaml --fail-on never
```

The example intentionally triggers a mechanism error, so use `--fail-on never` for
that smoke test.

## Conduct and security

Participation follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report security or
privacy vulnerabilities through [SECURITY.md](SECURITY.md), especially when a report
could expose unpublished data or credentials.
