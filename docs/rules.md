# Core lint rules

## Rule philosophy

Core rules protect relationships that are broadly valid across disciplines. A
domain rule pack may require stronger evidence, but cannot weaken these rules.
Every current finding identifies the affected record, rule ID, remediation, and
available evidence/path context. Explicit rule-version fields and override
suppression remain future compatibility work.

Use `paperci explain PCI-MECH-001` to inspect the initial detailed rule explanation
in text, or add `--format json` for tools and interfaces. The explanation separates
the minimum core trigger from stronger, context-dependent evidence expectations.

Severity means:

- `error`: the current project representation is invalid or the claim crosses a
  major evidence boundary;
- `warning`: important information is missing or a defensible exception may exist;
- `note`: improvement that does not block use.

Review decisions are append-only events with a reason. The current core retains
findings instead of silently suppressing them.

## Current core rules (ProjectSpec 0.4)

### `PCI-REF-001` — dangling reference

**Default:** error, no override.

Every evidence, claim, story, hypothesis, figure, gap, run, and review reference
must resolve to a compatible record type.

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

### `PCI-STAT-002` — effect claim lacks magnitude and uncertainty

**Default:** warning.

Difference, association, predictive, causal, mediation, and mechanism claims should
link to an effect estimate and uncertainty where that representation is meaningful.
A p-value alone does not express scientific magnitude.

### `PCI-STAT-003` — nested outcomes lack cluster metadata

**Default:** warning.

When `unit_of_analysis` explicitly declares `_nested_within_`, the design must name
the `parent_unit` and each group must record its number of independent `clusters`.
This exposes potential pseudoreplication without inferring whether a particular
mixed model, GEE, or cluster-level analysis is adequate.

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

### `PCI-MECH-001` — mechanism claim lacks mechanistic-role evidence

**Default:** error.

A mechanism claim cannot rely exclusively on observational difference, correlation,
enrichment, prediction, or colocalization. Domain packs define acceptable combinations
of perturbation, temporal, rescue, binding, structural, lineage-tracing, and
orthogonal evidence. The core recognizes explicit roles including
`lineage_tracing`, `washout_persistence`, `state_erasure_test`, `direct_occupancy`,
`functional_perturbation`, and `target_engagement`; a role never expands the claim
beyond the recorded biological scale. Context-specific roles pass only compatible
claim language—for example, lineage tracing can support clonal propagation but does
not unlock an unrelated direct-binding claim. `target_engagement` alone is also
insufficient without perturbation, functional perturbation, or rescue.

### `PCI-REL-001` — evidence is both support and challenge

**Default:** error.

One evidence ID cannot simultaneously appear in a claim's `supports` and
`challenges` lists. A genuinely mixed result should be split into bounded evidence
records or the relationship should be resolved explicitly; silently counting it in
both directions makes downstream gates indeterminate.

### `PCI-SEM-001` — explicit semantic category boundary crossed

**Default:** error.

The v0.4 core implements two conservative, benchmark-derived contrasts: cellular or
clonal inheritance is not organismal/intergenerational transmission, and tumour
outgrowth with an explicit null tumour-count result is not increased initiation
frequency. This is a small deterministic vocabulary, not general natural-language
entailment. New contrasts require adjacent passing and failing fixtures.

### `PCI-CLAIM-001` — cyclic claim dependencies

**Default:** error, no override.

`depends_on` must form a directed acyclic graph. A cycle prevents a stable ordering
of premises and conclusions and cannot be used to justify a generated story.

### `PCI-CONTRA-001` — material challenging evidence is omitted from the story

**Default:** warning.

If a central claim links to challenging evidence, the selected story must expose it
as a boundary, alternative, or unresolved gap. Deleting the edge is not remediation.

### `PCI-STORY-001` — unsupported claim in an active story

**Default:** error.

Every claim in an active story's central/path set must resolve, have at least one
supporting evidence item, and not be `prohibited` or `superseded`. Rejected and
superseded stories remain auditable without blocking current scientific gates.

### `PCI-STORY-002` — figure contains evidence but no argumentative question

**Default:** note.

Each main figure should answer a scientific question and connect its evidence to at
least one claim. This encourages figure-level argument without prescribing a fixed
number of figures.

### `PCI-AI-001` — generated output escapes its input manifest

**Default:** error, no override.

A generated story or hypothesis may cite only claim and evidence IDs included in
its recorded input manifest, and its provider identity must match that run. New
observations must return as import suggestions, never evidence.

### `PCI-HYP-001` — novelty has not been checked

**Default:** note.

Offline hypothesis generation cannot claim novelty. Until a dated assessment with
traceable literature sources exists, renderers keep novelty as `unchecked`.

### `PCI-HYP-002` — hypothesis lacks a falsifier

**Default:** error.

Every active frontier hypothesis requires a decisive test and an explicit result
that would falsify or materially narrow it. A generic request for “more validation”
is insufficient.

### `PCI-HYP-003` — competing explanation absent

**Default:** error.

Every active frontier hypothesis names at least one plausible alternative. Its
decisive test should describe different expected outcomes under the leading and
competing models.

### `PCI-HYP-004` — software-generated hypothesis self-shortlisted

**Default:** error, no override.

A hypothesis may be `shortlisted` only when a human `select` ReviewEvent targets
it. Software and models may generate or review hypotheses but cannot promote them.

### `PCI-HYP-005` — offline provider claims literature novelty

**Default:** error, no override.

A generation run recorded with `literature_mode: offline` must leave novelty
`unchecked` and cannot attach supposed literature sources. A provider cannot
manufacture a novelty assessment without performing and recording the search.

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
