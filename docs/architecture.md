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
      |             |            |
      +------ provenance graph ---+
                    |
       deterministic validators
                    |
         model-based reviewers
                    |
          Markdown / JSON report
```

## Core packages

The recommended v0.1 implementation is Python 3.11+.

```text
src/paperci/
  spec/          typed models, JSON Schema export, migrations
  store/         canonical project loading and content hashing
  graph/         evidence/claim/story links and traversal
  rules/         deterministic validation engine
  providers/     optional model protocol and local mock provider
  workflows/     propose, lint, compare, report
  render/        Markdown and machine-readable reports
  cli/           init, add, propose, lint, report, doctor
```

Recommended dependencies:

- Pydantic v2 for typed validation and schema generation;
- Typer for the CLI;
- `jsonschema` for conformance tests;
- NetworkX initially for in-memory traversal;
- Jinja2 for reports;
- optional LiteLLM-compatible adapters, not a core dependency.

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

The combined JSON Schema is in `spec/paperci.schema.json`. Public releases should
publish immutable schema URIs such as:

```text
https://paperci.org/spec/v0.1/project.schema.json
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

Only after hard gates run do models compare arcs, propose alternatives, and rank
gaps. Model findings are namespaced, reproducible records and never override hard
gate failures.

## Model provider protocol

The core invokes a small capability-based interface:

```python
class StoryProvider(Protocol):
    provider_id: str

    def capabilities(self) -> set[str]: ...
    def generate_structured(self, task: TaskBundle) -> ProviderResult: ...
```

Capabilities may include:

- `text_reasoning`;
- `vision_figure_reading`;
- `long_context`;
- `tool_calling`;
- `local_inference`.

Every run records provider, model identifier, adapter version, parameters, prompt
bundle hash, input manifest hash, token/cost information when available, output
hash, and timestamp. Secrets and raw prompts are not stored by default.

Provider adapters must support an outbound-data preview. Before a remote call, the
CLI shows which fields and artifacts will leave the machine. `--offline` is a hard
guarantee enforced below the workflow layer.

## Plugin contracts

Plugins are discovered through Python entry points and declare compatibility with
a PaperCI spec version.

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
  run: paperci lint --fail-on error --offline
```

Model-based story generation is not required in ordinary CI because it can be
non-deterministic, costly, or disclose private material. Teams may pin a provider
and snapshot run when they explicitly want model comparison.

## Security and privacy

- local and offline by default for `lint`, `report`, and `doctor`;
- no arbitrary execution of model-generated code in v0.1;
- no recursive upload of a project directory;
- allowlist exact artifacts included in each model task;
- redact local absolute paths from remote payloads;
- content hashes instead of content where possible;
- configurable sensitive fields and institution policy hooks;
- no telemetry in v0.1; later telemetry must be opt-in and documented;
- prompt injection text from documents is treated as data, never as instructions.

## Compatibility policy

- JSON Schema follows semantic versioning;
- patch releases may clarify validation without changing accepted structures;
- minor releases add optional fields and new rule IDs;
- major releases may change semantics and require a migration command;
- the core supports reading the current and previous minor schema versions;
- plugins declare `spec_requires` and fail with an actionable message.
