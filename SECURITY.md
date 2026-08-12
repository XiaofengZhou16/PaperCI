# Security and privacy policy

PaperCI commonly operates on unpublished scientific results. Treat privacy failures,
unexpected network transmission, provenance corruption, path disclosure, and unsafe
artifact handling as security issues.

## Supported versions

During pre-alpha development, only the latest tagged pre-release receives fixes.
This policy will be revised before a stable `1.0` release.

## Reporting a vulnerability

Do not attach unpublished data, credentials, identifiable participant information,
or proprietary artifacts to a public issue.

Use GitHub's [private vulnerability-reporting form](https://github.com/XiaofengZhou16/PaperCI/security/advisories/new).
Include only:

- affected PaperCI version;
- operating system and Python version;
- minimal synthetic reproduction;
- expected and observed behavior;
- whether data may have left the machine;
- suggested mitigation, if known.

Maintainers should acknowledge a report within seven days. A public disclosure
timeline will be agreed with the reporter after scope and mitigation are understood.

## Current security boundary

All currently shipped commands are offline and do not import a network client.
PaperCI does not execute model-generated code.

Local evidence paths are resolved relative to the project file. Remote and logical
URIs are recorded but not fetched. Hash validation reads only the explicitly named
local source.

Future model integrations must add an outbound-data preview, exact artifact
allowlist, redaction, provider/run identity, and a hard `--offline` enforcement layer
before becoming eligible for release.
