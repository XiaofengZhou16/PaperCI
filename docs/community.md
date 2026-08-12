# Community, governance, and contribution design

## Community promise

PaperCI should be a scientific commons rather than a thin interface around one
vendor's model. Its specifications, rules, fixtures, benchmark labels, and decision
history should remain inspectable and forkable.

## Licensing

- Apache-2.0 for code, schemas, tests, and repository documentation because its explicit
  patent grant is helpful for broad institutional adoption;
- per-case licenses for benchmark artifacts, recorded in each case manifest;
- no artifact enters the public benchmark unless redistribution rights are clear.

## Governance stages

### Stage 1: founding maintainers

Maintainers may merge ordinary changes, but all core schema fields, error-level
scientific rules, telemetry, and governance changes require an RFC and public
review period.

### Stage 2: domain maintainers

Contributors who maintain a tested rule pack or importer can become domain
maintainers. They own review in their package but cannot weaken core guarantees.

### Stage 3: technical steering group

When at least three institutions contribute regularly, elect a small, term-limited
steering group. No model provider should hold a majority of seats.

## Decision records

Use three lightweight mechanisms:

- issues for bugs, user pain, and small features;
- RFCs for schema, plugin, policy, or scientific-rule changes;
- ADRs for implementation choices that do not change the public contract.

An accepted error-level rule must document:

1. the scientific failure it prevents;
2. the evidence/design pattern it detects;
3. passing and failing fixtures;
4. known false positives and exceptions;
5. domain reviewers and review date;
6. whether it is core or profile-specific.

## Contribution paths

Good first contributions should not require model expertise:

- improve an error message;
- add a synthetic rule fixture;
- translate the CLI or documentation;
- add a Markdown renderer feature;
- document a false positive;
- test a public case in another discipline.

Advanced contributions include:

- an importer plugin;
- a domain rule pack;
- a local or remote provider adapter;
- an expert-adjudicated benchmark case;
- a standards exporter.

## Pull-request requirements

- no API key required for core tests;
- deterministic tests for core behavior;
- new fields include migration and compatibility notes;
- new rules include both positive and negative fixtures;
- model-dependent tests are recorded separately and never gate unrelated PRs;
- generated files state how to regenerate them;
- public cases include provenance and license manifests.

## Responsible-use policy

PaperCI should require visible AI-assistance metadata in exported run manifests,
but should not dictate manuscript authorship. Researchers remain responsible for
scientific claims, disclosure obligations, ethics, and journal policies.

The project must never market:

- guaranteed publication;
- calibrated journal acceptance predictions without prospective validation;
- automated replacement of scientific reviewers;
- unsupported claims of eliminating hallucinations;
- benchmark performance based on private or undisclosed labels.

## Sustainability

Keep the core useful without hosted infrastructure. Sustainable options that do
not undermine openness include:

- grants and institutional sponsorship;
- paid support and private deployment;
- hosted collaboration for teams;
- funded domain packs developed in public;
- community calls and design-partner programs.

The open specification, local CLI, validators, and public benchmark must not be
held back as a hosted-service moat.

## Launch sequence

1. Publish the specification and one compelling end-to-end example.
2. Invite critique from scientists, statisticians, research-software engineers,
   reproducibility researchers, and journal-methods editors.
3. Run a small design-partner pilot before promoting a broad public beta.
4. Publish failures and rule false-positive analyses alongside success stories.
5. Tag the first non-pre-alpha release only after distribution, compatibility, and
   design-partner tests are real.
