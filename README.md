# ActionDoctor

ActionDoctor is an open-source, offline CLI for finding security, reliability,
cost, and maintainability problems in GitHub Actions workflows.

The CLI currently discovers and validates workflow YAML, then runs an initial
five-rule security pack plus two demonstration rules through a reusable rule
engine. The full cross-category catalog and final health score are planned but
are not implemented yet.

## Requirements

- Python 3.12 or newer

## Local setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install ActionDoctor and its development tools:

```bash
python -m pip install -e ".[dev]"
```

Try the CLI:

```bash
actiondoctor --help
actiondoctor version
actiondoctor scan --help
actiondoctor scan .
python -m actiondoctor --help
```

## Scanning workflows

Pass the repository root to `scan`:

```bash
actiondoctor scan /path/to/repository
```

When omitted, the repository defaults to the current directory:

```bash
actiondoctor scan
```

ActionDoctor looks directly inside:

```text
.github/workflows/
```

Both `.yml` and `.yaml` files are supported. Files are parsed in deterministic
filename order. Directories, symlinks, nested files, and other extensions are
ignored.

Example output:

```text
ActionDoctor Scan

Repository: /path/to/repository
Workflow files discovered: 3
Successfully parsed: 2
Failed to parse: 1
Total rules executed: 14
Total findings: 1
Rule execution failures: 0

✓ .github/workflows/ci.yml
✗ .github/workflows/broken.yml — Invalid YAML: expected ',' or ']' at line 8, column 4
✓ .github/workflows/release.yaml

Findings

.github/workflows/release.yaml
  [LOW] MAINT001 — Missing Workflow Name
    Remediation: Add a descriptive top-level `name` to the workflow.
```

Exit code `0` means the scan completed without a configured failure condition.
Exit code `1` means a workflow could not be parsed, a rule failed
unexpectedly, or a finding reached the temporary `high` severity threshold.
Low-severity findings are displayed but do not fail the scan. Exit code `2`
means the repository path was invalid or an unexpected application error
occurred. A missing or empty workflow directory is a successful empty scan
with exit code `0` and an explanatory message.

## Current rules

- `SEC001` — Overly Broad Workflow Permissions (`high`/`critical`)
- `SEC002` — Missing Explicit Permissions (`medium`)
- `SEC003` — Third-Party Action Not Pinned to Commit SHA (`high`)
- `SEC004` — Untrusted Pull Request Checkout Risk (`critical`)
- `SEC005` — Secret Exposed Through Workflow-Level Environment (`medium`)
- `MAINT001` — Missing Workflow Name (`low`)
- `REL001` — Missing Jobs (`high`)

See [Rule documentation](docs/RULES.md) for behavior, ordering, registry
validation, and contributor instructions.

## Current limitations

- The current security pack is intentionally focused and does not constitute a
  complete GitHub Actions security audit.
- Cost and broader reliability/maintainability rule packs are not yet
  implemented.
- The health score remains a placeholder and is not shown by `scan`.
- JSON, Markdown, and SARIF reports are not available.
- Only workflow files directly inside `.github/workflows/` are discovered,
  matching GitHub Actions' workflow location.
- Individual workflow files are limited to 1,000,000 bytes.

## Development checks

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Packaging choice

ActionDoctor uses Hatchling as its PEP 517 build backend. Hatchling has concise
configuration, understands the `src` package layout directly, and lets the
package's `__version__` remain the single source of version metadata.

See [the architecture](docs/ARCHITECTURE.md) and
[the development plan](docs/DEVELOPMENT_PLAN.md) for the intended roadmap.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
