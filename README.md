# ActionDoctor

ActionDoctor is an open-source, offline CLI for finding security, reliability,
cost, and maintainability problems in GitHub Actions workflows.

The CLI currently discovers and validates workflow YAML, then runs five
security rules, five cost-efficiency rules, six reliability rules, and six
maintainability rules through a reusable rule engine. It reports an explainable
health score from 0 to 100 with severity and category breakdowns.

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
actiondoctor scan /path/to/repository --fail-on medium
actiondoctor scan /path/to/repository --no-color
actiondoctor scan /path/to/repository --format json
actiondoctor scan /path/to/repository --format markdown
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
ActionDoc
GitHub Actions Workflow Audit

Repository: /path/to/repository
Workflow files discovered: 3
Successfully parsed: 2
Failed to parse: 1
Total rules executed: 44
Total findings: 1
Rule execution failures: 0
Health score: 99/100
Health rating: Excellent
Status: Incomplete - 1 analysis error

Parsed workflows
  [OK] .github/workflows/ci.yml
  [OK] .github/workflows/release.yaml

Findings

.github/workflows/release.yaml
  [LOW] MAINT001 - Missing Workflow Name
    Description: The workflow should define a non-empty top-level name.
    Remediation: Add a descriptive top-level `name` to the workflow.

Workflow parse errors
  .github/workflows/broken.yml - Invalid YAML at line 8, column 4
```

Exit code `0` means the scan completed without a configured failure condition.
Exit code `1` means a workflow could not be parsed, a rule failed
unexpectedly, or a finding reached the `--fail-on` severity threshold. The
threshold defaults to `high`; choose `critical`, `high`, `medium`, `low`, or
`never`. `never` disables finding-based failure but not parse or rule errors.
Exit code `2`
means the repository path was invalid or an unexpected application error
occurred. A missing or empty workflow directory is a successful empty scan
with exit code `0` and an explanatory message.

## Exporting reports

The default `terminal` format keeps the Rich audit report. JSON and Markdown
can be written to standard output or atomically to a file:

```bash
actiondoctor scan . --format json --fail-on never
actiondoctor scan . --format markdown --fail-on never
actiondoctor scan . --format json --output reports/actiondoc.json
actiondoctor scan . --format markdown --output reports/actiondoc.md
```

File output creates missing parent directories, safely replaces an existing
report, and prints only a short confirmation. Format selection does not change
the health score or exit code. JSON uses public schema version `1.0`; see
[Report formats](docs/REPORT_FORMATS.md) for its fields and compatibility
policy. SARIF is not supported yet.

## Current rules

- `COST001` - Missing Concurrency Cancellation (`medium`)
- `COST002` - Missing Python Dependency Cache (`low`)
- `COST003` - Missing Node Dependency Cache (`low`)
- `COST004` - Unrestricted Push Workflow (`low`)
- `COST005` - Large Unbounded Matrix (`medium`)

- `SEC001` — Overly Broad Workflow Permissions (`high`/`critical`)
- `SEC002` — Missing Explicit Permissions (`medium`)
- `SEC003` — Third-Party Action Not Pinned to Commit SHA (`high`)
- `SEC004` — Untrusted Pull Request Checkout Risk (`critical`)
- `SEC005` — Secret Exposed Through Workflow-Level Environment (`medium`)
- `MAINT001` — Missing Workflow Name (`low`)
- `MAINT002` — Missing Job Name (`low`)
- `MAINT003` — Unnamed Run Step (`low`)
- `MAINT004` — Oversized Job (`medium`)
- `MAINT005` — Duplicate Step Name (`low`)
- `MAINT006` — Long Inline Shell Script (`low`)
- `REL001` — Missing Jobs (`high`)
- `REL002` — Missing Job Timeout (`medium`)
- `REL003` — Mutable Container Image Reference (`medium`)
- `REL004` — Moving Runner Label (`low`)
- `REL005` — Failure Ignored With Continue-on-Error (`medium`/`high`)
- `REL006` — Service Container Without Health Check (`low`)

See [Rule documentation](docs/RULES.md) for behavior, ordering, registry
validation, and contributor instructions.

## Current limitations

- The current security pack is intentionally focused and does not constitute a
  complete GitHub Actions security audit.
- Cost findings identify configurations that may increase runner usage; they
  do not calculate prices or guarantee monetary savings.
- Reliability findings identify deterministic configuration risks; they do
  not guarantee that a workflow will or will not fail.
- Maintainability findings identify structures that may be harder to review;
  they do not imply that every reported structure must be changed.
- SARIF reports are not available.
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
[the development plan](docs/DEVELOPMENT_PLAN.md) for the intended roadmap. The
[scoring policy](docs/SCORING.md) documents every weight, cap, rating, and
completeness rule.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
