# Technical architecture

## Architectural objective

PaperCI should gain capability from new foundation models without making its
scientific guarantees depend on one model. The stable center is a versioned,
model-independent intermediate representation and a deterministic validation
engine.

```text
files / notes / pipelines
          |
          v
  EvidenceDraft importers
          |
    human confirmation
          v
 EvidenceSpec -> ClaimSpec -> StorySpec
      |             |
      |             +------> HypothesisSpec
      |                        (separate speculative track)
      +------------ provenance graph --------+
                    |
       deterministic validators
                    |
         model-based reviewers
                    |
          Markdown / JSON report
```

## Core packages

The v0.4 implementation is Python 3.11+ and keeps the initial core deliberately
small:

```text
src/paperci/
  project.py      canonical YAML/JSON loading and identifiers
  engine.py       schema, provenance, reference, and scientific rules
  providers.py    provider protocol and offline deterministic baseline
  proposals.py    input hashing, idempotency, superseding, and run manifests
  comparison.py   hard-gate and transparent coverage comparison
  hypotheses.py   offline frontier Hypothesis Cards and run manifests
  hypothesis_comparison.py  multidimensional ambition comparison
  render.py       Markdown, JSON, text, and SARIF output
  cli.py          evidence/story and frontier-hypothesis commands
```

Current runtime dependencies are intentionally limited to Typer for the CLI,
`jsonschema` for conformance, and PyYAML for readable project files. Typed-model,
graph, template, and model-adapter libraries should be added only when an
implemented workflow needs them; remote-provider packages must remain optional.

Canonical project data remains YAML/JSON in the repository. SQLite or DuckDB may
be added as a disposable index, never as the only source of truth.

## The stable intermediate representation

### EvidenceSpec

Represents what was observed, under which design and scope, with a verifiable
source. It does not contain an inflated interpretation.

### ClaimSpec

Represents a proposition, its type and scope, supporting and challenging evidence,
assumptions, alternatives, and promotion state.

### StorySpec

Represents a paper-level argument: central question, central claim, ordered claim
path, story beats, figure sequence, unresolved gaps, and proposed discriminating
experiments.

### HypothesisSpec

Represents an explicitly speculative research direction: evidence and claim
anchors, an observed/inferred/speculative reasoning ladder, alternatives,
predictions, falsifiers, decisive tests, evidence distance, ambition dimensions,
novelty-assessment provenance, and a figure-question plan. It is not a ClaimSpec and
cannot be treated as a current conclusion.

The combined JSON Schema is in `spec/paperci.schema.json`. Public releases should
publish immutable schema URIs such as:

```text
https://paperci.org/spec/v0.4/project.schema.json
```

## Validation pipeline

Validation happens in a fixed order.

### 1. Structural validation

- schema conformance;
- unique identifiers;
- valid references;
- legal state transitions;
- version compatibility.

### 2. Provenance validation

- source exists when a local path is used;
- optional SHA-256 matches;
- locator is present for quantitative evidence;
- generated artifacts identify generator and version;
- verification event exists before state `verified`.

### 3. Scientific boundary validation

Rule packs inspect claim type, evidence design, scope, and language. Examples:

```text
PCI-CAUSAL-001
  A causal_effect claim requires an intervention, an identified causal design,
  or an explicit profile-specific exception.

PCI-MECH-002
  A mechanism claim cannot be supported only by association or motif enrichment.

PCI-SCOPE-003
  Claim population, system, context, or time range exceeds all supporting evidence.

PCI-STAT-004
  A reported numeric claim lacks effect/uncertainty or points to an inconsistent n.
```

Rules produce findings; they do not silently rewrite claims.

### 4. Model review

Only after structural gates run may a provider propose arcs. Scientific hard gates
are computed for the provider context and rerun on its output. The built-in story
and hypothesis providers are deterministic and offline: they use only existing
claim and evidence IDs. Future model findings must remain namespaced, reproducible
records and must never override hard-gate failures.

## Model provider protocol

The core invokes a small capability-based interface:

```python
class StoryProvider(Protocol):
    provider_id: str
    provider_version: str
    provider_kind: str

    def propose(self, context: ProposalContext) -> ProviderResult: ...
```

The frontier track exposes the parallel `HypothesisProvider` protocol. The core
allocates IDs, forces generated state to `speculative`, records the run manifest,
and revalidates provider output. A provider controls scientific content but cannot
self-promote, escape recorded inputs, or claim a literature assessment from an
offline run.

Future provider capabilities may include:

- `text_reasoning`;
- `vision_figure_reading`;
- `long_context`;
- `tool_calling`;
- `local_inference`.

Every current run records provider identity and version, parameters, a canonical
input hash, the exact allowed evidence and claim IDs, output story IDs, status, and
timestamp. Future model adapters must additionally define prompt-bundle identity,
token/cost reporting when available, and output hashing without storing secrets or
raw prompts by default.

Future remote-provider adapters must support an outbound-data preview. Before a
remote call, the CLI must show which fields and artifacts will leave the machine.
`--offline` will be a hard guarantee enforced below the workflow layer.

## Plugin contracts

Planned plugins will be discovered through Python entry points and declare
compatibility with a PaperCI spec version.

### ImporterPlugin

```text
input artifacts -> EvidenceDraft[] + ImportFinding[]
```

Importers may parse CSV, notebooks, figures, workflow manifests, or domain files.
They cannot create verified evidence.

### RulePackPlugin

```text
ProjectSpec -> Finding[]
```

Rules must have stable IDs, fixtures, documentation, severity rationale, and false
positive examples.

### ProfilePlugin

Defines audience and editorial priorities, allowed story vocabulary, required
dimensions, and preferred review prompts. Profiles cannot weaken core provenance
or causal rules.

### RendererPlugin

Turns a validated project and findings into Markdown, HTML, notebook, or another
presentation format. It must preserve IDs and status labels.

### ProviderPlugin

Adds a remote or local model adapter. Core tests run against a deterministic fake
provider so contributors never require paid credentials.

## State machines

Evidence lifecycle and claim decisions are intentionally separate.

```text
Evidence: draft -> reviewed -> verified
             |          |          |
             +------> disputed <---+
                           |
                        superseded

Claim:    candidate -> allowed
                    -> conditional
                    -> prohibited
                    -> disputed
```

Generated evidence begins as `draft`; generated claims begin as `candidate`.
Evidence verification means that a human confirmed its representation and source,
not that every interpretation derived from it is true. Claim promotion requires a
human review event with actor, timestamp, decision, and optional note. Models and
software emit findings but cannot use promotion decisions.

## Reproducibility and CI

`paperci lint --format sarif` should make scientific findings visible in GitHub
code review. A CI run should be able to fail on configured severities:

```yaml
- name: Lint scientific claims
  run: paperci lint --fail-on error
```

Model-based story generation is not required in ordinary CI because it can be
non-deterministic, costly, or disclose private material. Teams may pin a provider
and snapshot run when they explicitly want model comparison.

## Security and privacy

- all currently shipped commands are local and offline;
- no arbitrary execution of model-generated code before 1.0;
- no recursive upload of a project directory;
- allowlist exact artifacts included in each model task;
- redact local absolute paths from remote payloads;
- content hashes instead of content where possible;
- configurable sensitive fields and institution policy hooks;
- no telemetry before 1.0; later telemetry must be opt-in and documented;
- prompt injection text from documents is treated as data, never as instructions.

## Compatibility policy

- JSON Schema follows semantic versioning;
- patch releases may clarify validation without changing accepted structures;
- minor releases add optional fields and new rule IDs;
- major releases may change semantics and require a migration command;
- the core supports reading the current and previous minor schema versions;
- plugins declare `spec_requires` and fail with an actionable message.
