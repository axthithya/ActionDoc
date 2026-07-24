# Roadmap

ActionDoc is intentionally local, deterministic, and offline. This roadmap
describes direction, not dates or release promises.

## Released in v0.1.0

- Workflow discovery and safe YAML parsing for `.github/workflows`.
- Twenty-two security, cost, reliability, and maintainability rules.
- Deterministic health scoring and Rich terminal reporting.
- JSON schema 1.0 and Markdown reports.
- A reusable composite GitHub Action.
- Python package, CI, release validation, and contributor documentation.

## Planned next

- Additional focused rules and false-positive safeguards.
- SARIF output and optional GitHub code-scanning integration.
- Configurable rule selection and severity policy.
- Audited suppressions or baselines.
- GitHub annotations where they add actionable value.

## Longer-term possibilities

- Safe, constrained auto-fixes with dry runs and rescans.
- Optional third-party rule plugins.
- GitHub API-backed analytics as an opt-in integration.
- More report formats and ecosystem integrations.

Future work must preserve ActionDoc's deterministic local scanning path and
must not turn optional integrations into required services.
