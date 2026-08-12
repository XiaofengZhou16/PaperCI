# Ten-minute PaperCI pilot

This pilot tests whether PaperCI is understandable and useful before it processes
real research material. Use only the bundled synthetic case for the first run. Do
not paste unpublished, identifying, confidential, or proprietary data into a public
issue or discussion.

## 1. Install and run

PaperCI requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install "paperci==0.3.0a2"
paperci --version
paperci demo
cd paperci-demo
paperci doctor .
```

Windows PowerShell uses `.venv\Scripts\Activate.ps1` instead of the `source` line.

## 2. Inspect the decision boundary

```bash
paperci lint --fail-on never
paperci compare
paperci compare-hypotheses
```

Open `paperci-report.md` and answer three questions:

1. Is it clear why `C001` is supportable but `C002` is not?
2. Does comparing three arcs help you decide what deserves human review?
3. Does the proposed gap suggest a useful discriminating experiment without
   pretending that the experiment has been performed?
4. Is it clear that `H001`–`H003` are speculative research directions rather than
   claims supported by the current evidence?

The expected hard failure is `PCI-MECH-001`: motif enrichment alone does not prove
direct regulation. `S001` should be recommended only as the next arc for human
review, not labeled as the scientifically best story.

## 3. Report first-run friction

Use the public [first-run feedback form](https://github.com/XiaofengZhou16/PaperCI/issues/new?template=first_run.yml)
with synthetic excerpts only. Report:

- installation method and operating system;
- approximate time to the first report;
- the first command or concept that was unclear;
- whether the gate and comparison changed your interpretation;
- one improvement that would make you use PaperCI on a sanitized project.

Security or privacy problems belong in a
[private advisory](https://github.com/XiaofengZhou16/PaperCI/security/advisories/new),
not a public issue.

## Pilot success criteria

The design-partner pilot is considered promising when independent users can:

- install and produce the synthetic report without maintainer intervention;
- correctly explain that the mechanism claim failed because of evidence type, not
  because of wording alone;
- identify which files they would need to replace for a sanitized project;
- distinguish a generated candidate story from a human-approved conclusion.
- explain why an unchecked frontier hypothesis must not be marketed as novel or
  journal-ready.

Installation failures and misunderstood boundaries count as product findings. They
must not be removed from pilot reporting to improve an apparent success rate.
