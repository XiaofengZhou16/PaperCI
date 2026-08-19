# Importing evidence from CSV or TSV

`paperci import-table` is a local, deterministic ingestion step. It converts one
table row into one evidence card only after the user maps a statement column. It
does not infer claims, mechanisms, evidence roles, causal direction, or verification.

```bash
paperci import-table study results.csv \
  --statement-column finding \
  --kind-column evidence_type \
  --unit-column unit_of_analysis
```

The command records every item as `status: draft` and explicitly records
`verification: unverified` in `org.paperci.import.v1`. Each source contains the
table's SHA-256 and a precise `row=N` locator unless a locator column is mapped.
The project-level extension records the source, delimiter, complete column mapping,
imported IDs, row count, timestamp, and hash.

Use `--dry-run --format json` to inspect the exact records before writing. An
identical source hash and mapping cannot be imported twice. If a mapped statement,
locator, or evidence kind is invalid, the command refuses the entire import and
does not partially modify the project.

## Boundary

An imported row is not a verified result merely because it came from a structured
table. A human must still inspect source meaning, units, analysis, limitations, and
whether one row is scientifically bounded. Claims are added separately and remain
subject to all PaperCI provenance, scope, statistics, causality, and mechanism rules.
