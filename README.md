# ActionDoctor

ActionDoctor is an open-source, offline CLI for finding security, reliability,
cost, and maintainability problems in GitHub Actions workflows.

The project is currently at the foundation stage. The CLI and domain models
are available, but workflow discovery, parsing, and analysis are not
implemented yet.

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
python -m actiondoctor --help
```

The placeholder scan currently reports:

```text
ActionDoctor scanner foundation is ready. Workflow analysis is not implemented yet.
```

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
