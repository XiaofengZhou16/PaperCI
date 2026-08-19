# PaperCI open specification

## Design goals

The specification must be:

- simple enough to author manually;
- precise enough for deterministic linting;
- expressive enough for experimental and observational work;
- extensible without embedding one discipline's ontology in the core;
- compatible in spirit with established provenance and research-object standards;
- explicit about unknown, inferred, generated, and human-verified information.

## ProjectSpec

A project contains metadata, evidence, claims, stories, frontier hypotheses, review
events, generation-run manifests, and optional extensions. The top-level `spec_version`
selects the interpretation of all fields. Project `mode` describes the expected
workflow; it is not a shortcut that promotes every record in the project.

The current authoring version is `0.4`. The v0.4 validator also reads `0.1`–`0.3`
projects. A mutating `paperci propose` or `paperci hypothesize` run upgrades its
output to `0.4`; the new version adds explicit claim dependencies and nested-design
metadata. ProjectSpec `0.3` introduced the separate `hypotheses` collection.

PaperCI `0.5.0a1` keeps ProjectSpec at `0.4`. Table-import manifests and workflow
profiles use the existing namespaced `extensions` object under
`org.paperci.import.v1` and `org.paperci.profile.v1`. Unknown extensions remain data,
not scientific proof, unless a core rule or an installed rule pack explicitly
defines their semantics.

```yaml
spec_version: "0.4"
project:
  id: gout-cvd-story
  title: Trained myelopoiesis and plaque inflammation
  mode: sketch
evidence: []
claims: []
stories: []
hypotheses: []
reviews: []
runs: []
```

IDs are stable within a project and use prefixes by convention: `E`, `C`, `S`,
`H`, `G`, `R`, and `RUN`. They are not regenerated when text or ordering changes.

## EvidenceSpec

### Required minimal fields

```yaml
- id: E001
  kind: quantitative_result
  statement: Cxcl16 expression was higher in HFD than control GMP-derived cells.
  status: draft
  source:
    uri: results/cxcl16.csv
    locator: "row=18"
```

### Recommended scientific context

```yaml
  design:
    family: experiment
    unit_of_analysis: mouse
    parent_unit: cage
    groups:
      - id: control
        n: 5
        clusters: 3
      - id: hfd
        n: 5
        clusters: 3
    randomized: unknown
    blinded: unknown
  result:
    outcome: Cxcl16 expression
    contrast: HFD minus control
    direction: increase
    effect:
      value: 1.2
      unit: log2_fold_change
    uncertainty:
      kind: confidence_interval
      level: 0.95
      lower: 0.4
      upper: 2.0
    p_value: 0.01
    multiplicity: not_applicable
  scope:
    species: Mus musculus
    system: GMP-derived myeloid cells
    context: high-fat diet
```

An evidence statement describes the result and must not quietly contain a stronger
causal or mechanistic conclusion than the design permits.

`parent_unit` and `clusters` are used only when the recorded observations are nested.
For example, if `unit_of_analysis` is `tumour_nested_within_mouse`, `parent_unit`
should be `mouse`, group `n` may record tumours, and `clusters` records the number of
independent mice. The fields expose the hierarchy; they do not certify that the
statistical model handled it correctly.

### Evidence kinds

- `quantitative_result`
- `qualitative_observation`
- `figure_panel`
- `table`
- `dataset`
- `analysis_output`
- `external_source`

### Evidence status

- `draft`: user- or model-entered, not checked;
- `reviewed`: inspected but not fully source-verified;
- `verified`: representation and source locator confirmed by a human;
- `disputed`: accuracy or interpretation is actively contested;
- `superseded`: retained for history but replaced by another record.

## ClaimSpec

```yaml
- id: C001
  text: HFD exposure is associated with persistent Cxcl16 upregulation in the
    tested GMP-derived myeloid system.
  type: association
  strength: supports
  status: conditional
  supports: [E001, E002]
  challenges: [E009]
  depends_on: [C000]
  assumptions:
    - Batch effects do not explain the observed difference.
  alternatives:
    - Cell-composition shifts account for the signal.
  scope:
    species: Mus musculus
    system: GMP-derived myeloid cells
    context: tested ex vivo protocol
```

### Claim types

Ordered roughly by increasing evidential burden:

- `descriptive`
- `difference`
- `association`
- `temporal`
- `predictive`
- `causal_effect`
- `mediation`
- `mechanism`
- `generalization`
- `null`
- `resource`

### Claim strength

- `observes`
- `suggests`
- `supports`
- `demonstrates`
- `establishes`

Strength and type are separate. A verified descriptive result does not automatically
justify an `establishes` mechanism claim.

`depends_on` records scientific prerequisites, not chronology or citation order. The
graph must be acyclic and every referenced claim must exist. Story providers traverse
prerequisites before a downstream central claim, which makes long reasoning chains
explicit and reviewable.

### Claim decision status

- `candidate`
- `allowed`
- `conditional`
- `prohibited`
- `disputed`
- `superseded`

PaperCI validators recommend decisions, but a review event records the project
team's final promotion. `prohibited` means “not supportable from the current project
evidence,” not “false in nature.”

## StorySpec

```yaml
- id: S001
  title: Primed myelopoiesis sustains a plaque-relevant inflammatory signal
  profile: mechanistic_biology
  central_question: How can prior metabolic exposure create a durable inflammatory
    signal relevant to later vascular injury?
  central_claim: C001
  claim_path: [C010, C001, C004, C008]
  beats:
    - role: setup
      claim_ids: [C010]
    - role: discovery
      claim_ids: [C001]
    - role: mechanism
      claim_ids: [C004]
    - role: implication
      claim_ids: [C008]
  figure_plan:
    - figure: 1
      question: Does prior exposure alter the progenitor-derived response?
      evidence_ids: [E001, E002]
      claim_ids: [C001]
  gaps:
    - id: G001
      question: Is RUNX1 binding required for persistent Cxcl16 expression?
      blocks: [C004]
      severity: central
  status: candidate
```

### Story beats

The core recognizes a small vocabulary without forcing every story into one shape:

- `setup`
- `tension`
- `discovery`
- `explanation`
- `mechanism`
- `validation`
- `boundary`
- `implication`
- `resolution`

Profiles may add labels, but renderers must retain the base role.

## HypothesisSpec

A frontier hypothesis is not a current claim. It may be ambitious, but every
reasoning transition and decisive test remains inspectable.

```yaml
- id: H001
  statement: A candidate regulator may mediate the anchored response, and a
    target-engaged perturbation plus rescue should alter the outcome.
  strategy: mechanistic-deepening
  status: speculative
  seed_claim: C002
  anchor_claims: [C001, C002]
  evidence_ids: [E001, E002]
  inference_steps:
    - kind: observed
      statement: Target expression and motif accessibility changed after exposure.
      grounded_in: [E001, E002]
    - kind: inferred
      statement: The changes may share a regulatory process.
      grounded_in: [C001, C002]
    - kind: speculative
      statement: The candidate regulator is functionally required.
      grounded_in: [C002]
  alternatives:
    - The motif marks a correlated chromatin state without direct regulation.
  predictions:
    - Perturbation changes the outcome with measurable target engagement.
  decisive_tests:
    - design: Perturb the regulator and perform rescue with a pre-specified readout.
      distinguishes: [direct_regulation, correlated_chromatin_state]
      expected_outcomes:
        - model: direct_regulation
          expected: Perturbation changes the outcome and rescue restores it.
        - model: correlated_chromatin_state
          expected: The outcome persists despite target engagement.
      falsifier: A well-powered target-engaged perturbation leaves the outcome unchanged.
      feasibility: medium
      expected_information_gain: high
      dependencies: [validated perturbation, matched controls]
  evidence_upgrade_path:
    - Replicate the anchored result with uncertainty.
    - Establish temporal order and functional engagement.
    - Add rescue and orthogonal validation.
  evidence_distance: near
  ambition_profile:
    conceptual_advance: {level: medium, basis: "Mechanism could connect the anchors."}
    explanatory_breadth: {level: medium, basis: "Two claims are linked."}
    cross_scale_reach: {level: low, basis: "No cross-scale bridge is yet specified."}
    discriminating_power: {level: high, basis: "Competing outcomes are explicit."}
    testability: {level: high, basis: "A falsifier is pre-specified."}
    feasibility: {level: medium, basis: "Requires a validated perturbation."}
  novelty:
    status: unchecked
    note: No literature search was performed.
    literature_sources: []
  figure_plan:
    - figure: 1
      role: evidence_anchor
      question: Which observations motivate the hypothesis?
      evidence_ids: [E001, E002]
```

Strategies are `mechanistic-deepening`, `cross-scale-bridge`, and
`paradigm-challenge`. Generated hypotheses always start as `speculative`.
`shortlisted` requires a human `select` ReviewEvent.

Novelty status is `unchecked`, `checked`, `potentially_novel`, or `not_novel`.
Any status other than `unchecked` requires a dated assessment and at least one
traceable literature source. This is a provenance requirement, not proof of
priority or publication fit.

## Gap and experiment proposals

A gap is an unresolved question linked to the claims it blocks. A proposed
experiment is decision support, not evidence.

```yaml
gaps:
  - id: G001
    question: Does RUNX1 directly control the persistent signal?
    competing_explanations: [direct_binding, correlated_chromatin_state]
    proposed_tests:
      - design: RUNX1 perturbation with binding and expression readouts
        distinguishes: [direct_binding, correlated_chromatin_state]
        feasibility: medium
        expected_information_gain: high
        dependencies: []
```

`expected_information_gain` is an ordinal expert/model judgment until a domain
plugin supplies a formal calculation. It must not be rendered as a calibrated
probability.

## RunManifest

Every built-in generation run records what the provider was allowed to see and
which stories or hypotheses it produced:

```yaml
- id: RUN001
  kind: story_proposal
  provider:
    id: paperci.builtin.deterministic
    version: "1"
    kind: software
  input_hash: ea0dda9051851f3e7c66b1a854d8f4d979d6bfa7a0e7f0ba21efc1e6bddff40a
  input_manifest:
    evidence_ids: [E001, E002]
    claim_ids: [C001, C002]
  parameters:
    arcs: 3
    strategies: [evidence-conservative, high-risk-hypothesis, minimum-gap]
    central_claim: null
  output_ids: [S002, S003, S004]
  status: completed
  created_at: 2026-08-12T12:10:00+08:00
```

The current input hash covers the spec version, project identity, evidence, claims,
provider identity/version, and proposal parameters. Identical inputs reuse the
completed run unless `--force` is supplied. A changed input creates a new run and
supersedes prior candidate stories produced by the same provider; manual, selected,
or rejected stories are not silently rewritten.

Generated stories carry a namespaced extension pointing to their run, provider,
version, and strategy. `PCI-AI-001` fails if they cite a claim or evidence ID outside
the recorded input manifest. Run provenance does not verify scientific correctness,
and generated stories always begin as `candidate`.

Hypothesis generation uses `kind: hypothesis_generation`, outputs `H` IDs, and
records `org.paperci.hypothesis.v1`. The same input-boundary rule applies, while
generated hypotheses always begin as `speculative`.

## ReviewEvent

```yaml
- id: R001
  target: E001
  actor:
    kind: human
    id: researcher-or-orcid
  decision: verify
  timestamp: 2026-08-12T12:00:00+08:00
  note: Checked against row 18 and analysis notebook.
```

Events are append-only. Current state can be derived from the event stream, while
the convenient `status` field allows readable diffs. A conformance validator checks
that the two agree. Only an actor with `kind: human` may issue promotion decisions
such as `verify`, `allow`, `condition`, `prohibit`, `select`, or `reject`. Model and
software reviews are stored as findings or non-promoting `review` events.

## Extensions

Domain fields live under namespaced keys:

```yaml
extensions:
  org.paperci.biomed.v1:
    assay: CUT&Tag
    target: RUNX1
```

Extensions cannot redefine core semantics. New broadly useful concepts should be
proposed through an RFC and tested against at least two domains before promotion
to the core schema.

## Interoperability direction

Future exporters should map:

- source entities, generating activities, and responsible actors to W3C PROV;
- the complete project bundle to RO-Crate JSON-LD;
- atomic verified claims to nanopublication assertions where appropriate;
- lint findings to SARIF for code-hosting review;
- persistent people and research outputs to ORCID and DOI identifiers.

These mappings are compatibility layers. Requiring researchers to author RDF is
explicitly out of scope.
