# Releasing ActionDoc

This guide prepares a release; it does not authorize publishing, tagging, or
uploading distributions by itself.

## Version and changelog

The authoritative package version is `__version__` in
`src/actiondoctor/__init__.py`. Hatchling reads it dynamically for
`pyproject.toml`, and the CLI reads the same value. For a release, update that
one version source, move completed work from `Unreleased` into a dated
changelog section, then verify the version with the CLI and built wheel.

## Validation

Run [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md): quality checks, self-scan,
package build, Twine validation, clean wheel installation, and local GitHub
Action smoke test. The tag-triggered release-validation workflow repeats these
checks and uploads artifacts only; it never publishes to PyPI or creates a
GitHub Release.

## After approval

Only after maintainers explicitly approve publication, create and push the
reviewed release tag, create a GitHub Release from it, and optionally publish
the already validated distributions through a separate trusted-publishing
workflow. Never place tokens or personal access tokens in repository files,
workflow YAML, or documentation.
