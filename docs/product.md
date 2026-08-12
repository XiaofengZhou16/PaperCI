# Product contract

## Product thesis

Researchers do not primarily need another tool that turns a prompt into polished
prose. They need a workspace that makes the relationship among results, claims,
alternative explanations, figures, and missing experiments explicit.

PaperCI's initial wedge is deliberately narrow:

> I already have results. Help me discover and stress-test the best paper-level
> story without saying more than those results support.

Its second, linked job is:

> Given those evidence boundaries, propose ambitious mechanisms worth testing next,
> while exposing every speculative jump, alternative explanation, and falsifier.

This begins after exploratory analysis and before manuscript drafting. It can
later connect to upstream analysis and downstream writing tools without trying to
replace them.

## Primary users

### 1. First author assembling a paper

- has figures, result tables, and several plausible interpretations;
- needs to decide the central claim and figure order;
- worries that an elegant mechanism is ahead of the evidence;
- wants concrete next experiments rather than generic reviewer comments.

### 2. Principal investigator reviewing a project

- wants to see evidence and assumptions behind a proposed story;
- compares a conservative arc with a high-risk/high-reward arc;
- needs a stable record of what the team accepted, rejected, or deferred.

### 3. Methods and domain contributors

- encode reusable rules for a study design or assay;
- contribute public benchmark cases;
- add model providers or importers without changing the core protocol.

The first release optimizes for the first author. A tool that does not help one
researcher on one real project within ten minutes will not earn team adoption.

## Jobs to be done

When I have a folder of heterogeneous results, help me:

1. state each important result in a consistent, inspectable form;
2. generate genuinely competing explanations and story arcs;
3. see which claims are directly supported, conditional, or prohibited;
4. turn the selected arc into a figure-level argument;
5. find the smallest decisive experiment, not merely a longer wish list;
6. rerun the review when a result, analysis, or model changes.
7. explore mechanistic-deepening, cross-scale, and paradigm-challenging hypotheses
   without promoting them into current claims.

## The ten-minute contract

A new user should be able to install PaperCI, enter six evidence cards, and obtain
a useful comparison of story arcs in ten minutes. The minimum evidence card asks:

1. What was compared or observed?
2. What was measured?
3. What happened?
4. How robust or uncertain is the result?
5. Where can a human verify it?

Unknown values are allowed and visibly marked. The tool must not convert missing
information into invented precision.

## Progressive trust

### Sketch

The user may paste notes such as “RUNX1 motif enriched near Cxcl16.” PaperCI can
explore stories, but stores the card as `draft`, renders it as unverified, and
blocks strong downstream claims.

### Verified

A person confirms source, locator, design, sample unit, effect, and uncertainty.
PaperCI records who verified what and when. Verification means “faithfully
represented,” not “scientifically true.”

### Connected

An adapter creates evidence cards from a workflow artifact. A content hash and
generator version make changes detectable. Human promotion is still required for
interpretive claims.

## Output contract

PaperCI returns three layers rather than one opaque score.

The v0.4 pre-alpha implements deterministic validity gates plus two separate
records: evidence-bound stories and speculative frontier hypotheses. Hypotheses add
transparent ambition dimensions and falsifiable tests, but literature-aware novelty
and domain-specific experiment design remain future provider capabilities.

### A. Validity gates

Deterministic findings with stable identifiers and severity:

- missing source or locator;
- sample unit inconsistent with reported `n`;
- unsupported causal or mechanistic language;
- claim scope broader than evidence scope;
- contradicted direction or statistics;
- unresolved multiplicity or missingness;
- generated output citing an evidence or claim ID outside its run manifest.

### B. Comparative story review

Ordinal dimensions, never an acceptance probability:

- conceptual advance;
- explanatory coherence;
- causal depth;
- convergent evidence;
- alternative-explanation resistance;
- audience breadth;
- figure economy;
- claim-to-evidence coverage.

Each judgment includes reasons, counterarguments, and the model/run identity.

### C. Decision support

- recommended arc and why;
- strongest competing arc and when it would be preferable;
- claims to keep, soften, split, or remove;
- Figure 1–6 argument map;
- experiments ranked by discrimination, feasibility, and dependency.

### D. Frontier hypothesis support

- three genuinely different hypothesis strategies rather than three paraphrases;
- explicit observed, inferred, and speculative transitions;
- multidimensional ambition profile without a scalar journal or impact score;
- novelty status that defaults to `unchecked` offline;
- model-specific expected outcomes and a result that would falsify each hypothesis;
- human-only shortlisting.

## Non-goals before 1.0

- writing the full manuscript;
- evaluating novelty from the entire literature;
- executing arbitrary model-generated analysis code;
- ingesting every laboratory file format;
- predicting editor or reviewer decisions;
- replacing formal study-design or statistical review;
- training a proprietary “Nature taste” model.
- claiming that a generated hypothesis is novel, journal-ready, or already
  supported by the current evidence.

## Adoption requirements

### Researchers will use it only if

- raw unpublished data can remain local;
- they can start from plain language rather than an ontology;
- every criticism points to a specific claim and evidence card;
- the system admits uncertainty and disagreements;
- outputs can be edited and reviewed in Git, Markdown, or a notebook;
- the tool remains useful with no paid model API.

### Contributors will join only if

- the core has a small dependency surface;
- plugins have stable contracts and fixtures;
- benchmark licensing and review requirements are explicit;
- domain rules can be added without modifying the core engine;
- maintainers explain why a rule or case is accepted.

## Success measures

The first public pilot should target outcome measures, not stars:

- median time to first report at or below ten minutes;
- at least 80% of surfaced high-severity findings judged useful by project authors;
- zero silently invented evidence IDs or source locators in the golden cases;
- deterministic lint results identical across model providers;
- at least half of pilot users return after adding new evidence;
- at least three independently authored domain plugins or rule packs.

## Product boundaries

The project should use “high-impact scientific story” rather than “Nature story”
as its general positioning. Journal profiles may encode public editorial criteria,
but must remain transparent configurations and must not claim to reproduce an
editorial board or estimate acceptance probability.
