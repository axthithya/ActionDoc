<div align="center">

<p aria-label="ActionDoc logo placeholder">🩺</p>

# ActionDoc

**Audit GitHub Actions workflows for security, reliability, cost, and maintainability.**

[![PyPI](https://img.shields.io/badge/PyPI-not%20published-lightgrey)](https://pypi.org/)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue)](LICENSE)
[![CI](https://github.com/axthithya/ActionDoc/actions/workflows/ci.yml/badge.svg)](https://github.com/axthithya/ActionDoc/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/badge/GitHub%20Release-pending-lightgrey)](https://github.com/axthithya/ActionDoc/releases)

</div>

## What is ActionDoc?

GitHub Actions workflows are code that runs with access to your repository,
credentials, and CI budget. They are easy to overlook during review.

ActionDoc scans workflow files in `.github/workflows/` and points out common
security risks, reliability issues, unnecessary CI cost, and maintainability
problems. It runs locally, deterministically, and without sending workflow
data anywhere.

Run one command, get actionable findings, a 0--100 health score, and reports
you can use locally or in CI.

## Why ActionDoc?

| Without ActionDoc | With ActionDoc |
| --- | --- |
| Manual YAML review | One command to audit workflows |
| Easy-to-miss security mistakes | Automatic rule-based detection |
| No shared quality signal | Explainable 0--100 health score |
| Notes scattered across reviews | Terminal, JSON, and Markdown reports |
| No workflow quality gate | Reusable GitHub Action integration |

## Features

| Area | Included today |
| --- | --- |
| Security | Explicit-permission, action-pinning, untrusted-checkout, and secret-environment checks |
| Reliability | Job timeout, container image, runner-label, ignored-failure, and service-health checks |
| Cost | Concurrency, dependency cache, trigger, and static-matrix checks |
| Maintainability | Workflow/job/step names, oversized jobs, duplicate steps, and long-script checks |
| Reports | Rich terminal output plus deterministic JSON and Markdown exports |
| Scoring | Transparent 0--100 score with severity and category breakdowns |
| CLI | `scan` and `version` commands with configurable failure thresholds |
| GitHub Action | A composite action that delegates to the same local CLI |

ActionDoc currently includes **22 built-in rules**: 5 security, 5 cost,
6 reliability, and 6 maintainability rules.

## Installation

ActionDoc requires Python 3.12 or newer. It is not published to PyPI yet, so
install from a checked-out repository for now.

### pip

After the package is published, the install command will be:

```bash
python -m pip install actiondoctor
```

For the current source release, use the source instructions below instead.

### uv

If you use [uv](https://docs.astral.sh/uv/), the future package install will
be:

```bash
uv tool install actiondoctor
```

Until publication, clone the repository and use `uv pip install -e ".[dev]"`.

### From source

```bash
git clone https://github.com/axthithya/ActionDoc.git
cd ActionDoc
python -m venv .venv
python -m pip install -e ".[dev]"
```

Activate the environment with `source .venv/bin/activate` on macOS/Linux or
`./.venv/Scripts/Activate.ps1` in Windows PowerShell.

## Quick start

From a repository that contains `.github/workflows/`, run exactly these three
commands:

```bash
python -m pip install -e "path/to/ActionDoc[dev]"
cd your-repository
actiondoctor scan .
```

```text
ActionDoc
GitHub Actions Workflow Audit

Repository: /path/to/your-repository
Workflow files discovered: 2
Successfully parsed: 2
Total findings: 1
Health score: 90/100
Health rating: Good

.github/workflows/ci.yml
  [HIGH] SEC003 - Third-Party Action Not Pinned to Commit SHA
    Remediation: Pin the action to a full commit SHA.
```

ActionDoc scans `.yml` and `.yaml` files directly inside
`.github/workflows/`. Files are processed in deterministic order; malformed
and unreadable files are reported rather than silently ignored.

## Understanding the output

The health score starts at **100**. Each finding reduces it according to its
severity, with a maximum 20-point penalty per rule ID. Parse and rule errors
are shown as incomplete analysis instead of silently changing the score.

| Severity | What it means |
| --- | --- |
| Critical | A serious workflow risk that needs immediate attention. |
| High | A significant issue worth fixing before relying on the workflow. |
| Medium | A meaningful risk or quality issue to plan and address. |
| Low | A smaller improvement that makes workflows safer or easier to maintain. |

<div align="center">

<em>Terminal output screenshot placeholder</em>

</div>

Read the complete scoring policy in [SCORING.md](docs/SCORING.md).

## Report formats

Terminal output is the default. JSON is useful for scripts and integrations;
Markdown is useful for CI summaries and review artifacts.

```bash
# Rich terminal report
actiondoctor scan .

# Machine-readable JSON
actiondoctor scan . --format json --output reports/actiondoc.json

# Shareable Markdown
actiondoctor scan . --format markdown --output reports/actiondoc.md
```

Use `--fail-on critical`, `high`, `medium`, `low`, or `never` to choose which
finding severity returns exit code `1`. See [REPORT_FORMATS.md](docs/REPORT_FORMATS.md)
for the public JSON schema and output behavior.

## GitHub Action

Use the included composite action to enforce the same checks in a workflow.
Replace `<immutable-release-commit>` with the full commit SHA for the ActionDoc
release you intend to trust.

```yaml
name: Audit workflows

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  actiondoc:
    runs-on: ubuntu-24.04
    steps:
      - name: Check out repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Audit GitHub Actions workflows
        uses: axthithya/ActionDoc@<immutable-release-commit>
        with:
          path: .
          fail-on: high
          report-format: markdown
```

| Input | Default | Purpose |
| --- | --- | --- |
| `path` | `.` | Repository path to scan. |
| `fail-on` | `high` | Lowest severity that fails the Action. |
| `report-format` | `markdown` | `markdown`, `json`, or `none`. |
| `report-path` | generated | Optional destination for the report file. |

Markdown output is added to the GitHub step summary. The report path is also
available as `steps.<id>.outputs.report-path`. See [GITHUB_ACTION.md](docs/GITHUB_ACTION.md)
for local testing, runner requirements, and pinning guidance.

## Rule categories

| Category | Description | Rule count |
| --- | --- | ---: |
| Security | Finds risky permissions, references, checkout patterns, and secret exposure. | 5 |
| Reliability | Finds settings that can make a workflow flaky or hide failures. | 6 |
| Cost | Finds workflow choices likely to consume unnecessary runner time. | 5 |
| Maintainability | Finds structures that make workflows harder to review and change. | 6 |

## Example findings

| Rule | Example | Why it matters |
| --- | --- | --- |
| `SEC003` | Third-party Action Not Pinned to Commit SHA | Mutable tags can change after review; a full SHA makes the revision explicit. |
| `REL005` | Failure Ignored With Continue-on-Error | Ignored failures can allow later steps to proceed without a reliable result. |
| `MAINT004` | Oversized Job | Very large jobs are harder to understand, review, and safely modify. |

See [RULES.md](docs/RULES.md) for all implemented rules, their rationale, and
remediation guidance.

## Project structure

```text
ActionDoc/
├── src/actiondoctor/       # CLI, parsing, rules, scoring, and reports
├── tests/                  # Unit tests and workflow fixtures
├── docs/                   # User, contributor, and release documentation
├── .github/                # CI, release validation, and issue templates
├── action.yml              # Reusable composite GitHub Action
├── scripts/                # Action entry point
└── pyproject.toml          # Package metadata and tool configuration
```

## Documentation

| Topic | Read more |
| --- | --- |
| Architecture | [ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Rules | [RULES.md](docs/RULES.md) |
| Scoring | [SCORING.md](docs/SCORING.md) |
| Reports | [REPORT_FORMATS.md](docs/REPORT_FORMATS.md) |
| GitHub Action | [GITHUB_ACTION.md](docs/GITHUB_ACTION.md) |
| Release guide | [RELEASING.md](docs/RELEASING.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Support | [SUPPORT.md](SUPPORT.md) |

## Roadmap

- [x] Local workflow discovery, parsing, rules, scoring, and reports
- [x] Reusable GitHub Action
- [ ] SARIF output
- [ ] Safe, opt-in auto-fixes
- [ ] Configuration and reviewed suppressions

These are directions, not release promises. See [ROADMAP.md](docs/ROADMAP.md)
for the current scope and limitations.

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) for
the local setup, quality checks, and rule contribution checklist. Please follow
the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

ActionDoc is licensed under the [Apache License 2.0](LICENSE).
