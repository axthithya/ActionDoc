# ActionDoc Development Plan

## Purpose

This plan builds ActionDoc in vertical, testable phases while keeping the
MVP local, deterministic, and offline. Each phase should leave the repository
usable and should avoid implementing later features prematurely.

Unless a phase explicitly changes the contract, all work follows
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Phase 1: Project foundation

### Goal

Create an installable Python 3.12+ package with a minimal Typer entry point and
consistent development tooling.

### Tasks

- Add `pyproject.toml` with package metadata and the `src` layout.
- Declare runtime dependencies: Typer, Rich, Pydantic, and `ruamel.yaml`.
- Declare development dependencies: pytest, Ruff, and mypy.
- Add `actiondoctor` and `python -m actiondoctor` entry points.
- Implement only `version` and a placeholder/helpful `scan` command.
- Configure Ruff, mypy, and pytest in `pyproject.toml`..
- Add README, license, changelog, contribution guidance, and a minimal CI
  workflow.
- Establish supported Python versions and a release version source.

### Expected files

- `pyproject.toml`
- `src/actiondoctor/__init__.py`
- `src/actiondoctor/__main__.py`
- `src/actiondoctor/cli.py`
- `tests/integration/test_cli.py`
- `.github/workflows/ci.yml`
- `README.md`
- `LICENSE`
- `CHANGELOG.md`
- `CONTRIBUTING.md`

### Tests required

- Package imports from an installed/editable environment.
- `actiondoctor --help` exits successfully.
- `actiondoctor version` and `python -m actiondoctor version` agree.
- Ruff, mypy, and pytest run successfully in CI on each supported Python
  version.

### Completion criteria

- A clean checkout can be installed using documented commands.
- All tool checks pass.
- The CLI exposes help and version information.
- No scanner behavior is claimed or stubbed with misleading results.

## Phase 2: Workflow discovery and parsing

**Status: Complete (2026-07-23).** All phase acceptance criteria pass,
including deterministic discovery, safe UTF-8 loading, YAML 1.2 parsing,
structured partial failures, source locations, CLI exit behavior, and offline
tests.

### Goal

Reliably discover, load, and parse GitHub Actions workflows while retaining
source locations for later rule findings.

### Tasks

- Define `WorkflowSource`, `WorkflowDocument`, `SourceLocation`, and
  `Diagnostic`.
- Implement discovery for `.github/workflows/*.yml` and `*.yaml`.
- Define behavior for a repository root, explicit directory, and explicit
  file.
- Implement UTF-8 loading, a documented size limit, and typed load failures.
- Configure `ruamel.yaml` round-trip parsing.
- Validate only the minimum root and `jobs` shapes needed for analysis.
- Normalize output paths and file ordering.
- Implement source-location/traversal helpers used by future rules.
- Correctly handle GitHub Actions' `on` key and representative YAML features.

### Expected files

- `src/actiondoctor/models.py`
- `src/actiondoctor/diagnostics.py`
- `src/actiondoctor/discovery.py`
- `src/actiondoctor/loading.py`
- `src/actiondoctor/parsing.py`
- `tests/unit/test_discovery.py`
- `tests/unit/test_loading.py`
- `tests/unit/test_parsing.py`
- `tests/fixtures/workflows/*`

### Tests required

- Both `.yml` and `.yaml` are found; unrelated files are ignored.
- Discovery order and normalized paths are deterministic.
- Missing paths, unreadable files, invalid UTF-8, oversized files, empty
  documents, multiple documents, malformed YAML, and non-mapping roots return
  expected diagnostics.
- `on` remains a string key.
- Comments, anchors/aliases, quoted scalars, and line/column locations survive
  parsing as required.
- Windows and POSIX-style path cases render consistently.

### Completion criteria

- Fixture repositories produce the same ordered documents on repeated runs.
- Parse errors identify the file and source location when available.
- A parsed document exposes jobs, steps, and source positions without rules
  importing `ruamel.yaml` internals for common traversal.
- No network access is needed.

## Phase 3: Rule engine

**Status: Complete (2026-07-23).** The typed rule protocol, explicit validated
registry, deterministic failure-isolating engine, safe execution diagnostics,
two demonstration rules, CLI integration, and offline tests are complete.
Configuration and severity overrides remain deferred as required by this
phase's implementation scope.

### Goal

Provide a small, reusable contract for selecting and executing independent
rules against parsed workflows.

### Tasks

- Define `Severity`, `RuleCategory`, `Finding`, and `RuleContext`.
- Define the `Rule` protocol or abstract base class and metadata contract.
- Implement `RuleRegistry` with ID/metadata validation and stable selection.
- Implement `RuleEngine` with deterministic execution and finding ordering.
- Define deduplication and unexpected rule-error behavior.
- Support selection by rule ID and category.
- Reserve severity overrides in configuration without overbuilding the config
  system.
- Add one private test rule to exercise the engine; do not yet build the rule
  catalog.

### Expected files

- `src/actiondoctor/models.py`
- `src/actiondoctor/engine.py`
- `src/actiondoctor/registry.py`
- `src/actiondoctor/rules/__init__.py`
- `src/actiondoctor/rules/base.py`
- `tests/unit/test_engine.py`
- `tests/unit/test_registry.py`
- `tests/unit/test_models.py`

### Tests required

- Zero, one, and multiple findings are collected correctly.
- Rules execute in stable ID order across multiple workflow files.
- Finding sort order and deduplication are deterministic.
- Duplicate IDs, malformed IDs, prefix/category mismatches, and incomplete
  metadata fail registry validation.
- Rule selection, unknown IDs, category filtering, disabling, and severity
  overrides behave as documented.
- Unexpected exceptions become the agreed diagnostic or fail-fast result
  without corrupting other output.

### Completion criteria

- A test-only rule can be registered and executed without modifying engine
  code.
- Invalid registries cannot be constructed.
- Engine output is identical for equivalent inputs regardless of input
  iteration order.
- Rules perform no I/O and the engine has no rule-specific branches.

## Phase 4: Initial rules

**Status: Complete (2026-07-23).** The initial production security (`SEC001`
through `SEC005`), cost-efficiency (`COST001` through `COST005`), reliability
(`REL001` through `REL006`), and maintainability (`MAINT001` through
`MAINT006`) packs are complete with deterministic detection, practical YAML
locations, false-positive protections, CLI integration, documentation, and
offline tests.

### Goal

Deliver a small, high-confidence rule set spanning security, cost,
reliability, and maintainability.

### Tasks

- Select an initial catalog based on precise, testable behavior.
- Allocate permanent IDs using `SEC###`, `COST###`, `REL###`, and
  `MAINT###`.
- Implement each rule in its category package.
- Register rules explicitly in the default registry.
- Document rationale, examples, severity, limitations, and remediation for
  every rule.
- Avoid rules that require repository-wide GitHub API data or speculation.
- Define handling for expressions, matrices, reusable workflows, local
  actions, and dynamic values on a per-rule basis.

Candidate rules should be confirmed during this phase rather than treated as
already committed. Examples include unpinned third-party actions, overly broad
permissions, missing timeouts, unbounded matrix use, and duplicate step
patterns.

### Expected files

- `src/actiondoctor/rules/security/sec001_*.py`
- `src/actiondoctor/rules/cost/cost001_*.py`
- `src/actiondoctor/rules/reliability/rel001_*.py`
- `src/actiondoctor/rules/maintainability/maint001_*.py`
- `src/actiondoctor/registry.py`
- `docs/rules/SEC001.md`
- `docs/rules/COST001.md`
- `docs/rules/REL001.md`
- `docs/rules/MAINT001.md`
- `tests/unit/rules/test_sec001_*.py`
- `tests/unit/rules/test_cost001_*.py`
- `tests/unit/rules/test_rel001_*.py`
- `tests/unit/rules/test_maint001_*.py`

### Tests required

For every rule:

- a minimal positive case;
- a minimal negative case;
- multiple violations in one workflow;
- exact rule metadata, message, severity, and location;
- expressions or dynamic values;
- malformed or partial structures the parser permits;
- false-positive regression cases identified during review; and
- applicable GitHub-owned, third-party, local, reusable, matrix, and
  container-action variants.

A registry-wide test must enforce ID uniqueness, format, and category prefix.

### Completion criteria

- At least one documented, enabled-by-default rule exists in each category.
- Each finding points to the most useful source location.
- Rules produce no output or side effects.
- Ambiguous cases are documented and favor avoiding false positives.
- The full suite passes offline.

## Phase 5: CLI reporting

**Status:** In progress. Health scoring, the dedicated Rich terminal reporter,
score completeness, `--fail-on`, and `--no-color` are complete. The planned
`rules` command, configuration layer, and filters remain future work.

### Goal

Connect the analysis pipeline to a polished Rich terminal experience and
stable CI exit behavior.

### Tasks

- Implement `ScanConfig` and the application orchestration layer.
- Implement the `scan`, `rules`, and `version` commands.
- Implement `TerminalReporter` using an injected Rich `Console`.
- Group findings by file and show rule ID, severity, source location,
  explanation, and remediation.
- Implement severity/category/rule filters.
- Define and document `--fail-on`, color, stdout/stderr, and exit-code
  behavior.
- Implement the initial health-score calculator and explain its breakdown.
- Show incomplete scans prominently when diagnostics exist.

### Expected files

- `src/actiondoctor/config.py`
- `src/actiondoctor/scoring.py`
- `src/actiondoctor/reports/base.py`
- `src/actiondoctor/reports/terminal.py`
- `src/actiondoctor/cli.py`
- `tests/unit/test_scoring.py`
- `tests/unit/reports/test_terminal.py`
- `tests/integration/test_cli.py`

### Tests required

- Score bounds, severity weights, empty findings, repeated findings, and order
  independence.
- Terminal output with color enabled and disabled.
- TTY and redirected-output behavior.
- All documented exit codes and failure thresholds.
- Filtering and severity overrides.
- No-workflow, malformed-workflow, valid-clean, and finding-producing fixture
  repositories.
- Stdout remains report-only and stderr receives operational errors.

### Completion criteria

- `actiondoctor scan <fixture>` presents an actionable report and health score.
- Exit behavior is reliable enough for CI.
- Repeated scans of unchanged input produce semantically identical output.
- Terminal rendering contains no analysis or score policy.

## Phase 6: Export formats

**Status: Complete (2026-07-24).** Deterministic JSON schema 1.0 and Markdown
reports, portable explicit projections, machine-clean stdout, atomic file
output, format-independent exit behavior, documentation, and offline tests are
complete. SARIF remains explicitly deferred.

### Goal

Provide stable JSON and Markdown reports from the same `ScanResult` used by the
terminal.

### Tasks

- Finalize `ScanResult`, `ScanSummary`, and report schema version fields.
- Implement deterministic JSON serialization.
- Publish a JSON Schema if the output is intended for external automation.
- Implement Markdown summary and finding details.
- Add `--format` and `--output` behavior, including overwrite/error policy.
- Normalize portable paths and omit unstable metadata by default.
- Document machine-consumption guarantees.
- Design the SARIF mapping but defer implementation unless separately scoped.

### Expected files

- `src/actiondoctor/reports/json_report.py`
- `src/actiondoctor/reports/markdown.py`
- `src/actiondoctor/models.py`
- `schemas/actiondoctor-report-v1.json`
- `tests/unit/reports/test_json_report.py`
- `tests/unit/reports/test_markdown.py`
- `tests/golden/*.json`
- `tests/golden/*.md`
- `docs/report-formats.md`

### Tests required

- JSON validates against its schema.
- JSON and Markdown golden outputs are deterministic.
- Unicode, Markdown metacharacters, empty findings, diagnostics, and missing
  locations are handled safely.
- All formats contain equivalent finding IDs, severities, paths, and score.
- `--output` writes the selected format and handles existing/unwritable paths
  according to the documented policy.
- JSON stdout contains no Rich markup, logs, or progress text.

### Completion criteria

- Terminal, JSON, and Markdown are projections of one result model.
- Output schemas and compatibility expectations are documented.
- Golden files are stable across supported operating systems.
- SARIF remains a clean reporter extension rather than leaking into rules.

## Phase 7: GitHub Action integration

**Status: Complete (2026-07-24).** The composite ActionDoc wrapper, validated
inputs, report-path output, Markdown step-summary integration, local-action CI
coverage, full-SHA dependency pins, and user documentation are complete. SARIF
and automatic report uploads remain deferred.

### Goal

Run the published ActionDoctor CLI predictably in GitHub Actions without
duplicating scanner logic.

### Tasks

- Choose and document a distribution approach after comparing startup time,
  reproducibility, supported runners, and release maintenance.
- Add `action.yml` with explicit inputs mapped to CLI options.
- Expose outputs such as health score and finding count.
- Support Markdown output in `GITHUB_STEP_SUMMARY`.
- Document permissions using least privilege.
- Pin third-party actions by full commit SHA in ActionDoctor's own workflows.
- Test invocation in a fixture repository and on pull requests.
- Decide whether SARIF upload is part of a later, separate phase; do not
  require elevated permissions for the basic Action.

### Expected files

- `action.yml`
- `scripts/run-action.*` or a minimal action entry point if required by the
  chosen distribution
- `.github/workflows/action-integration.yml`
- `tests/integration/test_action_contract.py`
- `docs/github-action.md`
- `README.md`

### Tests required

- Metadata/input contract validation.
- Default invocation and custom path, format, and failure threshold.
- Clean and finding-producing fixture repositories.
- Output variables and step summary content.
- Paths containing spaces and both YAML extensions.
- The Action fails only according to the documented CLI threshold.
- A pinned end-to-end workflow runs on supported GitHub-hosted runners.

### Completion criteria

- A consumer can add the Action with documented minimal permissions.
- The Action invokes the released CLI and produces the same findings as local
  execution.
- Inputs, outputs, permissions, and version-pinning guidance are documented.
- Integration tests pass without granting write permissions by default.

## Phase 8: Documentation and release preparation

**Status: Complete (2026-07-24).**

### Goal

Make the project understandable, reproducible, and ready for an initial
open-source release.

### Tasks

- Complete installation, quick-start, CLI, rule, scoring, report-format,
  limitations, and troubleshooting documentation for implemented behavior.
- Review architecture documentation against the implementation.
- Add contributor instructions for creating and testing a rule.
- Add a code of conduct, security policy, issue templates, and release
  checklist.
- Verify package metadata, license inclusion, source distribution, and wheel.
- Run accessibility/readability review for terminal and Markdown output.
- Establish semantic versioning and changelog practices.
- Perform a clean-environment and offline scan smoke test.
- Publish only after a separate explicit release decision; this phase does not
  authorize pushing, merging, or publishing.

### Expected files

- `README.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `docs/SCORING.md`
- `docs/REPORT_FORMATS.md`
- `docs/GITHUB_ACTION.md`
- `docs/RULES.md`
- `docs/ROADMAP.md`
- `docs/RELEASING.md`
- `.github/ISSUE_TEMPLATE/*`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `docs/RELEASE_CHECKLIST.md`
- `.github/workflows/release-validation.yml`

### Tests required

- All unit, integration, and golden tests across supported Python versions.
- Ruff formatting/linting and strict-enough mypy checks.
- Package build plus wheel/source-distribution installation smoke tests.
- CLI documentation examples run successfully against fixtures.
- Broken internal link and documentation build checks, if a documentation
  generator is adopted.
- Clean repository smoke test for local CLI and the GitHub Action contract.

### Completion criteria

- A new user can install, scan a repository, interpret findings and score, and
  select an export format using the documentation alone.
- A contributor can add a rule by following one documented path.
- Built artifacts contain the expected package data and pass smoke tests.
- Security, compatibility, known limitations, and output stability are stated.
- The release checklist is complete, with publishing left as an explicit
  separate action.

## Cross-phase quality gates

Every implementation phase should meet these gates before moving on:

- no network calls in scanner runtime or tests;
- deterministic ordering and portable paths;
- new public behavior is documented;
- new rules include false-positive-focused tests;
- Ruff, mypy, and pytest pass;
- machine-readable stdout is not polluted;
- dependencies are justified and kept minimal; and
- unrelated files are not changed.

## Deferred roadmap

After the eight phases and only with separate designs:

- SARIF 2.1.0 output and GitHub code-scanning integration;
- structured safe auto-fixes with dry-run, conflict detection, and rescan;
- baselines or audited suppressions;
- optional third-party rule entry points; and
- performance work based on measured repositories.

These items should reuse the existing rule, finding, scan-result, and reporter
boundaries rather than create parallel analysis paths.
