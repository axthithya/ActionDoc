# ActionDoc

[![CI](https://github.com/axthithya/ActionDoc/actions/workflows/ci.yml/badge.svg)](https://github.com/axthithya/ActionDoc/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

ActionDoc is a local, deterministic CLI that audits GitHub Actions workflows
for security, cost-efficiency, reliability, and maintainability concerns. It
reads workflow files from `.github/workflows/`; it does not send source code
or workflow data to a service.

## What it does

- Discovers and safely parses `.yml` and `.yaml` workflow files.
- Runs 22 built-in rules: 5 security, 5 cost, 6 reliability, and 6
  maintainability rules.
- Produces a transparent 0--100 health score with severity and category
  breakdowns.
- Renders Rich terminal output and deterministic JSON or Markdown reports.
- Works as a reusable composite GitHub Action using the same CLI.

## Install from source

ActionDoc requires Python 3.12 or newer. Until a package index release is
published, install a checked-out copy locally:

```bash
git clone https://github.com/axthithya/ActionDoc.git
cd ActionDoc
python -m venv .venv
python -m pip install -e ".[dev]"
```

On macOS or Linux, activate the environment with
`source .venv/bin/activate`. On Windows PowerShell, use
`./.venv/Scripts/Activate.ps1`.

## Quick start

```bash
actiondoctor scan .
actiondoctor scan . --fail-on medium
actiondoctor scan . --format json --output reports/actiondoc.json
```

ActionDoc scans only files directly inside `.github/workflows/`. It supports
both `.yml` and `.yaml`, processes them in deterministic order, and reports
invalid or unreadable files instead of silently skipping them.

```text
ActionDoc
GitHub Actions Workflow Audit

Repository: /path/to/repository
Workflow files discovered: 2
Successfully parsed: 2
Total findings: 1
Health score: 96/100
Health rating: Excellent

.github/workflows/ci.yml
  [HIGH] SEC003 - Third-Party Action Not Pinned to Commit SHA
```

## CLI and exit codes

```bash
actiondoctor --help
actiondoctor version
actiondoctor scan --help
python -m actiondoctor scan .
```

`scan` defaults to the current directory and fails on `high` findings. Use
`--fail-on critical`, `high`, `medium`, `low`, or `never` to set the threshold.
`never` disables only finding-threshold failures; parse and rule errors still
fail the scan.

| Code | Meaning |
| ---: | --- |
| 0 | Scan completed and no finding reached the selected threshold. |
| 1 | A finding reached the threshold, or parsing/rule execution was incomplete. |
| 2 | Invalid CLI input, repository path, or unexpected application error. |

A missing or empty workflow directory is a successful empty scan with a clear
message.

## Health score

The score starts at 100. Findings subtract severity weights (`low` 1,
`medium` 4, `high` 10, `critical` 20), with a maximum 20-point penalty per
rule ID. Diagnostics do not silently affect the score; reports mark an
incomplete scan explicitly. See the full [scoring policy](docs/SCORING.md).

## Reports

Terminal output is the default. JSON and Markdown contain the same scan result
and can go to stdout or an atomically written file:

```bash
actiondoctor scan . --format json --fail-on never
actiondoctor scan . --format markdown --output reports/actiondoc.md
```

The public JSON schema is versioned as `1.0`. See
[report formats](docs/REPORT_FORMATS.md) for fields and compatibility rules.
SARIF is planned, but not currently available.

## GitHub Action

The repository includes a composite action. Pin it to the immutable commit of
a released ActionDoc version rather than a mutable tag:

```yaml
- name: Audit workflows
  uses: axthithya/ActionDoc@<immutable-release-commit>
  with:
    path: .
    fail-on: high
    report-format: markdown
```

Markdown is appended to the GitHub step summary. JSON and Markdown report
paths are available through `steps.<id>.outputs.report-path`. Read the
[GitHub Action guide](docs/GITHUB_ACTION.md) before using it in CI.

## Rules

The built-in packs cover explicit permissions, action SHA pinning, untrusted
checkout patterns, concurrency, dependency caches, matrices, timeouts,
container references, runner labels, ignored failures, workflow/job/step
naming, oversized jobs, duplicate step names, and long scripts. See the
[rule reference](docs/RULES.md) for each rule's behavior and remediation.

## Limitations and roadmap

ActionDoc is a focused static audit, not a complete GitHub Actions security
review or pricing model. It makes no network requests, does not apply fixes,
and currently has no SARIF output or suppression/configuration file support.
The [roadmap](docs/ROADMAP.md) describes planned work without making release
date promises.

## Contributing and support

Read [CONTRIBUTING.md](CONTRIBUTING.md) for local checks and the rule
contribution checklist. Please report vulnerabilities privately under the
[security policy](SECURITY.md), and use [SUPPORT.md](SUPPORT.md) for usage
questions. Community expectations are in the [code of conduct](CODE_OF_CONDUCT.md).

## License

Licensed under the [Apache License 2.0](LICENSE).
