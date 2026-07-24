# Contributing to ActionDoctor

Thank you for helping improve ActionDoctor.

## Development environment

ActionDoctor requires Python 3.12 or newer. Create a virtual environment,
activate it, and install the package with its development dependencies:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
```

Run all quality checks before submitting a change:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Scope

Keep the scanner deterministic and offline. New runtime dependencies should
have a clear, documented need. Please keep changes focused and include tests
for public behavior.

Before extending scanning, reporting, or the reusable GitHub Action, review:

- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/RULES.md`
- `docs/REPORT_FORMATS.md`
- `docs/GITHUB_ACTION.md`

## Style

- Target Python 3.12 or newer.
- Add type annotations to production code.
- Use Ruff for formatting and linting.
- Add or update pytest tests with each behavioral change.
- Keep machine-readable stdout free of diagnostics and logging.
- Keep the GitHub Action as a small wrapper around the existing CLI; do not
  duplicate rule, scoring, or report logic in its entry point.
- Pin external GitHub Actions in project workflows to verified full commit
  SHAs, with a nearby version comment when useful.
