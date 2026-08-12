# Core lint rules

## Rule philosophy

Core rules protect relationships that are broadly valid across disciplines. A
domain rule pack may require stronger evidence, but cannot weaken these rules.
Every finding identifies the affected record, evidence path, remediation, rule
version, and whether a human override is possible.

Severity means:

- `error`: the current project representation is invalid or the claim crosses a
  major evidence boundary;
- `warning`: important information is missing or a defensible exception may exist;
- `note`: improvement that does not block use.

Overrides are append-only review events with a reason. They suppress presentation,
not history.

## Proposed v0.1 rules

### `PCI-REF-001` — dangling reference

**Default:** error, no override.

Every evidence, claim, story, figure, gap, and review reference must resolve to a
compatible record type.

### `PCI-PROV-001` — quantitative source has no locator

**Default:** error in `verified` mode; warning in `sketch` mode.

A quantitative result needs a locator precise enough for another person to find
the reported value. A filename alone is insufficient for a multi-result artifact.

### `PCI-PROV-002` — verified without human verification event

**Default:** error, no override.

Evidence cannot have status `verified` unless a human `verify` event targets it.
Model or software identities cannot satisfy the requirement.

### `PCI-PROV-003` — local source is missing

**Default:** error in `verified` or `connected` mode; warning in `sketch` mode.

A relative source URI must resolve from the project file's directory. Remote and
logical URIs are not contacted during linting.

### `PCI-PROV-004` — source hash changed

**Default:** error.

When a source declares SHA-256, the current local artifact must match it. PaperCI
does not silently update hashes because a changed source can invalidate claims.

### `PCI-PROV-005` — row locator cannot be resolved

**Default:** error.

For a local text source with a `row=N` locator, N must address an existing line.
Other locator families remain opaque until a matching importer or validator exists.

### `PCI-STAT-001` — sample unit or group size missing

**Default:** warning.

A quantitative comparison should state its unit of analysis and group sizes. This
rule does not guess that cells, reads, fields of view, or technical replicates are
independent biological samples.

### `PCI-STAT-002` — effect claim reports significance without magnitude

**Default:** warning.

Difference, association, predictive, causal, mediation, and mechanism claims should
link to an effect estimate and uncertainty where that representation is meaningful.
A p-value alone does not express scientific magnitude.

### `PCI-SCOPE-001` — claim exceeds evidence scope

**Default:** error for explicit conflicts; warning for missing scope.

A claim cannot silently generalize beyond the supporting species, population,
system, context, or time. Cross-system implications must be labeled as hypotheses
or supported by bridging evidence.

### `PCI-CAUSAL-001` — causal claim without causal identification

**Default:** error.

A `causal_effect` or `mediation` claim requires an intervention or a design and
analysis that explicitly identify the causal estimand. Temporal order, prediction,
adjusted regression, or biological plausibility alone is insufficient.

### `PCI-MECH-001` — mechanism claim supported only by association

**Default:** error.

A mechanism claim cannot rely exclusively on observational difference, correlation,
enrichment, prediction, or colocalization. Domain packs define acceptable combinations
of perturbation, temporal, rescue, binding, structural, and orthogonal evidence.

### `PCI-CONTRA-001` — material challenging evidence is omitted from the story

**Default:** warning.

If a central claim links to challenging evidence, the selected story must expose it
as a boundary, alternative, or unresolved gap. Deleting the edge is not remediation.

### `PCI-STORY-001` — unsupported central claim

**Default:** error.

A story's central claim must resolve, have at least one supporting evidence item,
and not be `prohibited` or `superseded`.

### `PCI-STORY-002` — figure contains evidence but no argumentative question

**Default:** note.

Each main figure should answer a scientific question and connect its evidence to at
least one claim. This encourages figure-level argument without prescribing a fixed
number of figures.

### `PCI-AI-001` — generated claim invents evidence

**Default:** error, no override.

A model-generated claim may cite only evidence IDs included in its input manifest.
New observations must return as hypotheses or import suggestions, never evidence.

## Domain-specific examples

The following should not enter the core until their scope is encoded by a domain
pack:

- motif enrichment is not direct TF binding;
- chromatin accessibility is not transcriptional regulation;
- cell-level replication is not subject-level replication;
- diagnostic discrimination is not clinical utility;
- animal-model efficacy is not human therapeutic efficacy.

They are ideal for the first `paperci-biomed` pack because each can be tested with
focused positive and negative fixtures.

## Rule contribution checklist

A proposed rule is incomplete without:

- one minimal failing fixture;
- one nearby passing fixture;
- a scientific rationale and source where applicable;
- a remediation message;
- known exceptions and false positives;
- severity justification;
- owner and last expert review date.
