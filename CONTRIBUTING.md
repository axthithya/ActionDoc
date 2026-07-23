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

The scanner and rule engine are not implemented in the foundation phase.
Before adding those features, review:

- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_PLAN.md`

## Style

- Target Python 3.12 or newer.
- Add type annotations to production code.
- Use Ruff for formatting and linting.
- Add or update pytest tests with each behavioral change.
- Keep machine-readable stdout free of diagnostics and logging.
