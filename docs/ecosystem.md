# Ecosystem and differentiation

PaperCI should integrate with the AI-for-science ecosystem instead of claiming that
no adjacent work exists.

## Adjacent projects

| Project or standard | Primary role | Relationship to PaperCI |
|---|---|---|
| [data-to-paper](https://github.com/Technion-Kishony-lab/data-to-paper) | End-to-end data analysis and traceable paper generation | Potential upstream evidence/analysis importer and downstream manuscript integration |
| [The AI Scientist](https://github.com/SakanaAI/AI-Scientist) | Autonomous idea, experiment, paper, and review workflows for code-executable domains | Complementary autonomous workflow; PaperCI focuses on user-owned heterogeneous results and claim boundaries |
| [PaperQA](https://github.com/Future-House/paper-qa) | Scientific literature question answering with citations | Optional literature evidence and novelty-review provider |
| [Google Co-Scientist](https://doi.org/10.1038/s41586-026-10644-y) | Hypothesis generation and experimental planning | Primarily upstream of PaperCI's result-to-story workflow |
| [EvidenceBench](https://github.com/EvidenceBench/EvidenceBench) | Biomedical claim-to-evidence extraction benchmark | Useful task design and potential compatible evidence-extraction evaluation |
| [W3C PROV-O](https://www.w3.org/TR/prov-o/) | Interoperable provenance model | Export vocabulary for entity, activity, agent, and derivation relationships |
| [RO-Crate](https://www.researchobject.org/ro-crate/specification/1.2/introduction.html) | Packaging research artifacts and metadata | Export container for a complete PaperCI project |
| [Nanopublications](https://nanopub.net/) | Atomic assertion plus provenance and publication metadata | Potential export for stable, verified atomic claims |

## Narrow differentiation

PaperCI does not compete on producing the longest autonomous workflow. Its core
contribution is a reusable contract at the result-to-story boundary:

```text
heterogeneous project evidence
  -> typed scientific claims
  -> competing paper-level arguments
  -> deterministic boundary checks
  -> discriminating evidence gaps
```

This boundary is often handled today by informal lab meetings, slide rearrangement,
and manuscript rewriting. It is a good open-source wedge because it is useful even
when upstream analysis and downstream writing tools differ.

## Build, integrate, or defer

### Build in core

- EvidenceSpec, ClaimSpec, and StorySpec;
- ID and provenance integrity;
- deterministic claim-boundary rule engine;
- human promotion records;
- provider-neutral model run manifests;
- report and SARIF output.

### Integrate through plugins

- literature retrieval and citation checking;
- notebook, workflow, or analysis-result extraction;
- model providers;
- domain ontologies;
- RO-Crate, PROV, and nanopublication export;
- manuscript authoring systems.

### Defer

- raw-data analysis engines;
- autonomous execution of generated code;
- a new general literature index;
- proprietary journal-decision prediction;
- a hosted collaboration platform before local utility is established.

## Editorial profiles

Nature's public criteria require original research of outstanding scientific
importance and a conclusion interesting to an interdisciplinary readership. Those
criteria can inform an explainable generalist profile, but they do not justify a
calibrated acceptance model or a claim that PaperCI reproduces editorial judgment.
Profiles should cite public criteria, expose their dimensions and weights, and be
versioned independently from hard scientific rules.

## Interoperability test

An integration is valuable when it can exchange stable IDs, exact source locators,
claim type and scope, uncertainty, and derivation history. Passing prose without
those fields is a convenience integration, not evidence interoperability.
