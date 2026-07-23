# ActionDoctor

ActionDoctor is an open-source, offline CLI for finding security, reliability,
cost, and maintainability problems in GitHub Actions workflows.

The CLI currently discovers and validates workflow YAML. Analysis rules and
the final health score are planned but are not implemented yet.

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

✓ .github/workflows/ci.yml
✗ .github/workflows/broken.yml — Invalid YAML: expected ',' or ']' at line 8, column 4
✓ .github/workflows/release.yaml
```

Exit code `0` means all discovered workflows parsed successfully. Exit code
`1` means at least one workflow could not be read or parsed. Exit code `2`
means the repository path was invalid or an unexpected application error
occurred. A missing or empty workflow directory is a successful empty scan
with exit code `0` and an explanatory message.

## Current limitations

- Workflow files are parsed but not analyzed for security, reliability, cost,
  or maintainability issues.
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
