# Releasing PaperCI

PaperCI publishes from GitHub Actions with PyPI Trusted Publishing. Do not create
or store a long-lived PyPI token in the repository.

## One-time configuration

1. Secure the PyPI maintainer account with two-factor authentication.
2. Configure the `paperci` PyPI project or pending publisher with:
   - owner: `XiaofengZhou16`;
   - repository: `PaperCI`;
   - workflow: `release.yml`;
   - environment: `pypi`.
3. Create a protected GitHub environment named `pypi` and require manual approval
   before deployment.
4. Protect `main` from force-pushes and deletion, and require the CI workflow before
   merging release changes.

## Release checklist

1. Update `pyproject.toml`, `src/paperci/_version.py`, and `CHANGELOG.md` to the same
   version.
2. Run the full test, lint, build, metadata, wheel-install, and source-install checks
   on the release commit. The normal CI and release workflows perform these checks.
3. Merge the reviewed release change only after CI passes.
4. Create a GitHub release whose tag is exactly `v` followed by the package version.
   Publishing the release triggers `.github/workflows/release.yml`.
5. Review the protected-environment deployment and approve it only if the tested
   commit, tag, version, and generated distributions agree.
6. After publication, verify the PyPI project metadata, Trusted Publisher identity,
   attestations, and artifact hashes. Install the exact release in a new environment
   and run the synthetic demo again.

PyPI files and versions cannot be overwritten. If a published artifact is wrong,
yank it with a clear reason and prepare the next pre-release; do not reuse the
version number.
