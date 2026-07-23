# Changelog

All notable changes to ActionDoctor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project intends to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial Python package foundation.
- Typer CLI with version and placeholder scan commands.
- Typed Pydantic models for findings and scan results.
- Ruff, mypy, pytest, and GitHub Actions CI configuration.
- Deterministic discovery of `.yml` and `.yaml` GitHub Actions workflows.
- Safe YAML 1.2 parsing with structured, source-aware errors.
- Repository scan summaries and documented parse-related exit codes.
- Typed, side-effect-isolated rule protocol and deterministic rule engine.
- Explicit rule registry with strict ID and metadata validation.
- `MAINT001` missing-workflow-name demonstration rule.
- `REL001` missing-jobs demonstration rule.
- Finding summaries with a temporary high-severity CLI failure threshold.
- Initial security pack covering broad/missing permissions, mutable action
  references, risky `pull_request_target` checkout, and workflow-level secret
  environments.
- Practical line, column, job, and YAML-path context for step-level findings.
- Engine-level finding deduplication by rule and YAML location.
- Initial cost-efficiency pack covering concurrency cancellation, Python and
  Node dependency caching, unrestricted push triggers, and large static
  matrices.
- Typed cost-rule helpers for job/step traversal, action and shell-command
  matching, and static matrix sizing.
- Initial reliability pack covering missing job timeouts, mutable container
  images, moving runner labels, ignored failures, and missing service health
  checks while preserving `REL001`.
- Typed reliability helpers for jobs, steps, services, source locations,
  container references, runner labels, and static Docker options.
- Initial maintainability pack covering missing job and run-step names,
  oversized jobs, duplicate step names, and long inline scripts while
  preserving `MAINT001`.
- Shared typed job/step traversal and focused maintainability normalization and
  counting helpers.
