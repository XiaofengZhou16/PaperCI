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

A project contains metadata, evidence, claims, stories, review events, and optional
extensions. The top-level `spec_version` selects the interpretation of all fields.
Project `mode` describes the expected workflow; it is not a shortcut that promotes
every record in the project.

```yaml
spec_version: "0.1"
project:
  id: gout-cvd-story
  title: Trained myelopoiesis and plaque inflammation
  mode: sketch
evidence: []
claims: []
stories: []
reviews: []
```

IDs are stable within a project and use prefixes by convention: `E`, `C`, `S`,
`G`, and `R`. They are not regenerated when text or ordering changes.

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
    groups:
      - id: control
        n: 5
      - id: hfd
        n: 5
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
