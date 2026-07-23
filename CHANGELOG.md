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
