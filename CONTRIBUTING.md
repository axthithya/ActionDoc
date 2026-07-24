# Contributing to ActionDoc

Thanks for helping improve ActionDoc. The project is an offline, deterministic
GitHub Actions workflow auditor; please keep contributions focused, testable,
and free of network-dependent runtime behavior.

## Development setup

ActionDoc requires Python 3.12 or newer.

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest
```

Review [the architecture](docs/ARCHITECTURE.md),
[rule guidance](docs/RULES.md), and the [development plan](docs/DEVELOPMENT_PLAN.md)
before changing scanner behavior. The GitHub Action wrapper is deliberately
thin; do not duplicate scanner, scoring, or reporting logic in it.

## Contributing a rule

Rules must be small, deterministic, and side-effect free. A new rule should:

1. Reserve the next category-prefixed ID (`SEC`, `COST`, `REL`, or `MAINT`).
2. Implement the typed rule contract under the matching `src/actiondoctor/rules/`
   package.
3. Define concise title, description, category, and default severity metadata.
4. Register the rule in the explicit default registry; do not add runtime
   package scanning.
5. Return findings with stable relative paths and source locations whenever
   the YAML node provides them.
6. Add focused fixtures and tests for positive cases, false positives, unusual
   but valid YAML, multiple workflows, and deterministic ordering.
7. Document detection behavior, rationale, remediation, and known limitations
   in `docs/RULES.md`.
8. Confirm the rule does not mutate workflows, perform I/O, print output, or
   affect scoring outside of its findings.

## Tests and documentation

Every public behavior change needs pytest coverage. Update CLI examples,
reporting documentation, and GitHub Action documentation when they change.
Keep JSON stdout machine-readable and keep diagnostics out of report renderers.
Use checked-in fixtures rather than live repositories or network services.

## Style and pull requests

- Target Python 3.12+ and add type annotations to production code.
- Let Ruff format code; fix lint and mypy issues rather than ignoring them.
- Pin third-party Actions in this repository's workflows to full verified SHAs.
- Keep commits small and use a clear prefix such as `feat:`, `fix:`, `docs:`,
  `test:`, or `chore:`.
- Explain the user impact, tests run, and documentation changes in the pull
  request. Link the relevant issue when there is one.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). For vulnerabilities,
use the private process in [SECURITY.md](SECURITY.md), not a public issue.
