# ActionDoctor Architecture

## Status and scope

This document defines the target architecture for ActionDoctor, an offline,
deterministic CLI that analyzes GitHub Actions workflow files. It is a design
contract for future implementation; it does not imply that every component
described here exists yet.

The first release should:

- discover `.yml` and `.yaml` files under `.github/workflows/`;
- preserve useful YAML source locations while parsing;
- run independently testable security, cost, reliability, and maintainability
  rules;
- render terminal, JSON, and Markdown reports;
- calculate a stable health score from 0 to 100; and
- provide predictable exit codes for local and CI use.

SARIF, safe automatic fixes, and a packaged GitHub Action are planned extension
points. The MVP remains local, deterministic, offline, and free of AI, cloud,
and database dependencies.

## Design principles

1. **A small pipeline, not a framework.** Keep discovery, parsing, analysis,
   scoring, and presentation separate, but avoid dependency-injection.
   containers, event buses, or elaborate plugin systems.
2. **Rules do not perform I/O.** A rule receives parsed workflow data and
   returns findings. This makes rules deterministic and easy to unit test.
3. **Reports consume one result model.** Terminal, JSON, Markdown, and future
   SARIF output should not rerun rules or contain analysis logic.
4. **Source fidelity matters.** Retain file, line, and column information from
   `ruamel.yaml` so findings are actionable and future fixes can be safe.
5. **Public output is stable.** Rule IDs, severity names, JSON fields, score
   behavior, and exit codes are user-facing contracts.
6. **Failure is explicit.** Invalid YAML, unreadable files, and unsupported
   document shapes become diagnostics; they must not be silently ignored.
7. **Core behavior is typed.** Pydantic models define data that crosses
   component boundaries. Small internal helpers may use dataclasses or typed
   mappings where that is simpler.

## System context

ActionDoctor reads only the selected repository or path and writes only to
stdout/stderr or an explicitly selected report file.

```text
CLI arguments
     |
     v
Workflow discovery -> YAML loader -> Workflow parser
                                        |
                                        v
                                  WorkflowDocument
                                        |
Rule registry -> selected rules -> Rule engine -> findings + diagnostics
                                                   |
                                                   v
                                          Health-score calculator
                                                   |
                                                   v
                                               ScanResult
                                                   |
                         +-------------------------+------------------+
                         |                         |                  |
                    Rich terminal              JSON              Markdown
                                                                  (SARIF later)
```

## Proposed package layout

Use a `src` layout so tests cannot accidentally import the working directory
instead of the installed package.

```text
actiondoctor/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── release.yml
│   └── actiondoctor/               # optional fixtures/config, if needed later
├── docs/
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT_PLAN.md
├── src/
│   └── actiondoctor/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── diagnostics.py
│       ├── models.py
│       ├── discovery.py
│       ├── loading.py
│       ├── parsing.py
│       ├── scoring.py
│       ├── engine.py
│       ├── registry.py
│       ├── rules/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── security/
│       │   │   ├── __init__.py
│       │   │   └── sec001_unpinned_action.py
│       │   ├── cost/
│       │   │   └── __init__.py
│       │   ├── reliability/
│       │   │   └── __init__.py
│       │   └── maintainability/
│       │       └── __init__.py
│       └── reports/
│           ├── __init__.py
│           ├── base.py
│           ├── terminal.py
│           ├── json_report.py
│           ├── markdown.py
│           └── sarif.py             # later phase
├── tests/
│   ├── fixtures/
│   │   └── workflows/
│   ├── unit/
│   │   ├── rules/
│   │   ├── reports/
│   │   ├── test_discovery.py
│   │   ├── test_loading.py
│   │   ├── test_parsing.py
│   │   ├── test_engine.py
│   │   ├── test_registry.py
│   │   └── test_scoring.py
│   └── integration/
│       └── test_cli.py
├── pyproject.toml
├── README.md
├── LICENSE
└── action.yml                       # GitHub Action phase
```

Modules should stay cohesive. If `models.py` or another module becomes hard to
navigate, split it by domain at that point rather than creating many one-class
modules in advance.

## Domain models

Pydantic models are used for boundary data because they provide validation,
serialization, and a clear output schema.

### Severity

`Severity` is a string enumeration with these stable values:

```python
class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

Ordering and default score weights are defined separately so serialization
does not depend on numeric enum values:

| Severity | Rank | Initial score weight |
|----------|-----:|---------------------:|
| info | 0 | 0 |
| low | 1 | 1 |
| medium | 2 | 4 |
| high | 3 | 10 |
| critical | 4 | 20 |

The names are part of the public JSON contract. The weights are policy and may
be configurable in a future version, but must be versioned and tested.

### Finding

A finding describes one rule violation at one source location:

```python
class SourceLocation(BaseModel):
    path: Path
    line: int | None = None       # one-based for users
    column: int | None = None     # one-based for users
    end_line: int | None = None
    end_column: int | None = None

class Finding(BaseModel):
    rule_id: str
    title: str
    message: str
    severity: Severity
    category: RuleCategory
    location: SourceLocation
    help_text: str | None = None
    help_uri: str | None = None
    fingerprint: str | None = None
    fix: FixProposal | None = None  # reserved; populated only in a later phase
```

Findings must contain user-facing messages, not exceptions or raw parser
objects. `fingerprint` can later support deduplication and baseline workflows.
A future `FixProposal` must describe a constrained edit and remain separate
from applying that edit.

### Workflow and scan models

`WorkflowSource` represents loaded text and its path. `WorkflowDocument`
represents a parsed GitHub Actions workflow and preserves the underlying
round-trip YAML tree plus a small normalized view needed by rules. It includes
helpers to retrieve source locations without exposing `ruamel.yaml` details to
every rule.

Suggested boundary models:

- `WorkflowSource`: path, original text, content hash.
- `WorkflowDocument`: path, root mapping, normalized name/triggers/jobs, and
  location lookup helpers.
- `Diagnostic`: path, code, message, optional location, and diagnostic level;
  used for discovery/loading/parsing failures rather than rule violations.
- `ScanSummary`: counts by severity and category, files discovered, files
  analyzed, and rules executed.
- `ScoreResult`: integer score, total penalty, and optional penalty breakdown.
- `ScanResult`: tool/schema version, findings, diagnostics, score, summary, and
  scan metadata that is deterministic (avoid timestamps unless explicitly
  requested).

Use POSIX-style paths relative to the scan root in rendered output even on
Windows. This makes reports stable across machines. Absolute paths may be kept
internally but must not leak into portable output by default.

## Major components

### Workflow discovery

`WorkflowDiscovery` accepts a repository root or explicit path and returns an
ordered sequence of candidate paths.

Responsibilities:

- default to `<root>/.github/workflows`;
- accept a single file or directory when the CLI exposes that option;
- include only regular files with case-insensitive `.yml` or `.yaml`
  extensions;
- avoid following symlinks by default;
- normalize report paths relative to the scan root; and
- sort paths lexicographically for deterministic results.

Discovery does not open or parse files. A missing default workflow directory
is a clear diagnostic and, subject to the CLI contract, a non-zero exit.

### Workflow loader

`WorkflowLoader.load(path) -> WorkflowSource` handles file I/O only.

Responsibilities:

- read UTF-8 text with explicit, predictable error handling;
- reject files that exceed a documented safety limit;
- calculate a content hash if fingerprints or caching need it; and
- convert I/O and decoding failures into typed load errors.

It does not recursively discover paths and does not understand GitHub Actions
keys. Keeping loading separate allows parser tests to use in-memory sources.

### Workflow parser

`WorkflowParser.parse(source) -> WorkflowDocument` uses `ruamel.yaml` in
round-trip mode.

Responsibilities:

- parse exactly one YAML document;
- require a mapping at the root;
- preserve comments, scalar values, key order, and line/column metadata;
- validate the minimum structural shape relevant to analysis, such as `jobs`
  being a mapping when present;
- handle the YAML 1.1/1.2 ambiguity around the GitHub Actions `on` key
  correctly;
- expose safe traversal and source-location helpers; and
- convert syntax/shape errors into typed diagnostics.

The parser should not fully reimplement GitHub's workflow schema. Rules need
to analyze partially valid workflows, and GitHub evolves independently.
Structural checks should therefore be conservative.

The normalized view should not discard the round-trip tree. Rules that need
exact syntax, comments, or future auto-fixes must be able to locate the
original node.

### Rule contract

Each rule is a small class implementing a protocol or abstract base class:

```python
class Rule(Protocol):
    id: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    category: ClassVar[RuleCategory]
    default_severity: ClassVar[Severity]

    def check(
        self,
        workflow: WorkflowDocument,
        context: RuleContext,
    ) -> Iterable[Finding]: ...
```

`RuleContext` contains immutable scan configuration and shared read-only
helpers. It must not become a general service locator. A rule should return
zero or more findings and never print, write files, mutate the workflow, or
calculate the overall score.

Rule metadata is available without executing a rule. This supports `rules`
listing, documentation generation, configuration validation, and future SARIF
rule metadata.

### Rule registry

`RuleRegistry` owns the available rule classes and validates their metadata.
The default registry is built explicitly from category packages:

```python
DEFAULT_RULES = (
    UnpinnedActionRule,
    # new rule classes are added here
)

registry = RuleRegistry.from_rules(DEFAULT_RULES)
```

An explicit list is intentionally preferred over runtime package scanning or
Python entry points for the MVP. It is deterministic, packaging-friendly, and
easy to audit. Registration validates:

- unique IDs;
- ID format and category prefix;
- unique implementation classes;
- non-empty titles and descriptions; and
- valid default severities.

The registry provides selection by ID, category, severity, and configuration.
Unknown configured rule IDs are errors rather than silently ignored.

External third-party rule plugins are out of scope for the MVP. If later
needed, entry-point discovery can construct a registry without changing the
engine or rule contract.

### Rule engine

`RuleEngine.analyze(workflows, rules, context) -> AnalysisResult` coordinates
rule execution.

For each successfully parsed workflow, it runs each selected rule in stable
rule-ID order and collects findings. Findings are then stably sorted by path,
line, column, rule ID, and message.

Responsibilities:

- orchestrate rules without containing rule-specific logic;
- respect enabled/disabled rules and severity overrides;
- isolate unexpected rule exceptions as internal diagnostics when safe to do
  so;
- avoid duplicate findings using a documented identity tuple or fingerprint;
  and
- collect execution counts for the summary.

The initial engine is single-process. Parallelism adds complexity and can
damage deterministic output; it should be introduced only after profiling
shows a need.

### Health-score calculator

`HealthScoreCalculator.calculate(findings) -> ScoreResult` is a pure function
or stateless service. The initial policy is intentionally explainable:

```text
raw rule penalty = sum(weight(finding.severity) for findings of one rule ID)
capped rule penalty = min(raw rule penalty, 20)
score = max(0, 100 - sum(capped rule penalties))
```

An `info` finding contributes no penalty. Each non-info finding contributes
its severity weight, with a 20-point cap per rule ID. No hidden file-count
normalization or category multiplier is applied.

This model limits repetition of a single rule while allowing distinct problem
types to accumulate. Before a 1.0 release, evaluate the policy against
representative repositories. The policy must:

- always produce an integer in `[0, 100]`;
- be deterministic and order-independent;
- expose a penalty breakdown;
- be documented in reports;
- be covered by boundary and invariance tests; and
- have a version so future policy changes are visible.

Diagnostics such as malformed YAML do not silently reduce the score. The
report must prominently show incomplete analysis. A later product decision may
assign explicit diagnostic penalties, but that must not be implicit.

### Report generators

All report generators consume the same immutable `ScanResult`.

```python
class Reporter(Protocol):
    def render(self, result: ScanResult) -> str: ...
```

- `TerminalReporter` uses Rich for grouped, readable output and writes through
  an injected Rich `Console`. Color is disabled automatically for non-TTY
  output unless explicitly forced. Tests use a recording console.
- `JsonReporter` serializes a documented schema with a `schema_version`.
  Ordering is deterministic, and machine output goes to stdout without Rich
  decoration.
- `MarkdownReporter` produces a portable summary, score, counts, and findings
  table/details suitable for job summaries and pull-request artifacts.
- `SarifReporter` is reserved for a later phase and maps the same findings and
  locations to SARIF 2.1.0.

Reporters do not filter findings, change severity, compute the score, or choose
the process exit code. File output is handled by the application/CLI layer so
renderers remain easy to test.

JSON schema version 1.0 is projected through explicit public report models;
reporters never expose raw internal Pydantic serialization. JSON and Markdown
are rendered completely before output. File exports use a temporary file in
the destination directory and atomic replacement so a failed write cannot
leave a partial report. See [`REPORT_FORMATS.md`](REPORT_FORMATS.md) for the
public fields and compatibility policy.

### CLI commands

Typer exposes a thin command layer:

```text
actiondoctor scan [PATH]
actiondoctor rules
actiondoctor version
```

`scan` is the primary command. Current reporting options include
`--format terminal|json|markdown`, `--output PATH`, `--fail-on LEVEL`, and
`--no-color`. Future selection/configuration options include:

- `--min-severity LEVEL` for displayed/failed findings, with clearly defined
  score behavior;
- `--enable RULE_ID` and `--disable RULE_ID`;
- `--category CATEGORY`;
- `--config PATH` when configuration is introduced.

`rules` lists stable rule metadata without scanning. `version` prints only the
installed version.

Recommended exit-code contract:

| Code | Meaning |
|-----:|---------|
| 0 | Scan completed and no finding met the failure threshold |
| 1 | Scan completed and at least one finding met the failure threshold |
| 2 | Usage or configuration error |
| 3 | Scan could not be completed, including fatal discovery/parse errors |
| 4 | Unexpected internal error |

The default `--fail-on` policy must be chosen and documented during CLI
implementation. Machine-readable reports belong on stdout; progress,
diagnostics, and internal errors belong on stderr.

## End-to-end data flow

1. Typer validates CLI syntax and builds `ScanConfig`.
2. Discovery produces a stable list of workflow paths.
3. The loader reads each file into a `WorkflowSource`.
4. The parser creates a `WorkflowDocument` or a typed diagnostic.
5. The registry validates configuration and selects rules.
6. The engine applies selected rules to each valid document.
7. Findings are deduplicated and deterministically ordered.
8. The score calculator produces the score and penalty breakdown.
9. The application layer assembles one `ScanResult`.
10. The selected reporter renders the result.
11. The CLI writes the report and maps the result to a documented exit code.

No reporter calls the engine, and no rule calls a reporter. This one-way data
flow keeps testing and future integrations straightforward.

## Adding a rule

A contributor adds a rule without modifying discovery, parsing, engine,
scoring, reporters, or CLI code:

1. Choose the category and reserve the next rule ID.
2. Add one module under the matching `rules/<category>/` package.
3. Implement the `Rule` contract and use document traversal/location helpers.
4. Add the class to `DEFAULT_RULES` in the registry.
5. Add focused positive, negative, edge-case, and location tests.
6. Add rule documentation and a changelog entry when those files exist.

Adding the class to the explicit registry is the only central wiring change.
The engine remains closed to rule-specific behavior. A registry test prevents
duplicate IDs and invalid metadata.

Rules should detect one coherent problem. If a rule needs modes with different
messages, severities, or remediation, prefer separate IDs so users can
configure and suppress them independently.

## Rule-ID convention

Rule IDs are permanent, uppercase public identifiers:

| Category | Prefix | Example |
|----------|--------|---------|
| Security | `SEC` | `SEC001` |
| Cost | `COST` | `COST001` |
| Reliability | `REL` | `REL001` |
| Maintainability | `MAINT` | `MAINT001` |

The format is `PREFIX` plus a three-digit, zero-padded positive sequence.
IDs are allocated sequentially within a category and are never reused, even
after a rule is retired. The ID does not encode severity because severity may
evolve or be overridden. Experimental rules should use a separate opt-in
status field rather than an unstable ID.

Rule module names use lowercase IDs plus a short description, for example
`sec001_unpinned_action.py`. Finding messages may change, but an ID's semantic
meaning must not change incompatibly.

## Configuration boundary

Configuration is deliberately narrow in the first implementation. A future
local configuration file may support:

- enabling or disabling rule IDs or categories;
- rule severity overrides;
- rule-specific scalar settings with validated schemas;
- path exclusions; and
- failure threshold and report defaults.

Configuration should be represented by Pydantic models and merged in an
explicit precedence order:

```text
built-in defaults < repository config < CLI options
```

Do not execute configuration as Python. Unknown keys and unknown rule IDs
should produce actionable validation errors.

Inline suppressions are deferred until their syntax and auditability are
designed. Broad, invisible suppression mechanisms would undermine trust.

## Future extension points

### SARIF

The `ScanResult` and finding location fields are sufficient to map results to
SARIF 2.1.0. SARIF-specific concepts stay inside `SarifReporter`; rules do not
emit SARIF.

### Safe auto-fixes

Future rules may offer structured `FixProposal` objects containing expected
source content/ranges and replacement content. A separate fix coordinator
will:

- apply only explicitly safe and selected proposals;
- reject overlapping or stale edits;
- preserve YAML formatting through the round-trip representation;
- show a diff or support dry-run behavior; and
- reparse and rescan after changes.

Detection remains side-effect free. No rule writes a workflow directly.

### GitHub Action

The Action invokes the same CLI installed from the package. It does not create
a second scanning implementation. Inputs map to CLI options; outputs include
the health score and finding count. Markdown can be written to
`GITHUB_STEP_SUMMARY`, while SARIF upload remains an explicit later feature.

## Testing strategy

- **Unit tests:** models, discovery, loader errors, parser shapes and
  locations, each rule, registry validation, scoring, and each reporter.
- **Golden tests:** small checked-in expected JSON/Markdown outputs with
  deterministic ordering and normalized paths.
- **CLI integration tests:** Typer's `CliRunner` against fixture repositories,
  asserting stdout, stderr, file output, and exit codes.
- **Property/invariant tests where useful:** score bounds/order independence
  and stable finding sort order. Add a property-testing dependency only if its
  value justifies it.
- **Compatibility fixtures:** valid and malformed workflows, both extensions,
  quoted and unquoted `on`, anchors/aliases, matrix jobs, reusable workflows,
  composite action references, and mixed line endings.

Tests must not call GitHub or the network.

## Observability and error handling

Expected user errors become concise diagnostics with paths and locations.
Unexpected exceptions are caught only at the CLI boundary, reported without a
traceback by default, and mapped to exit code 4. A future `--debug` option may
show tracebacks.

Do not add logging until there is a concrete diagnostic need. When added,
logging must go to stderr and never corrupt JSON output.

## Decisions deferred deliberately

- Exact initial rule catalog and default failure threshold.
- Configuration filename and full schema.
- Score normalization or repeated-finding caps before 1.0.
- Inline suppression format.
- Public third-party rule plugin mechanism.
- SARIF and auto-fix schemas.
- Distribution form for the GitHub Action (for example, Docker versus a
  composite action that installs Python).

These decisions do not block the component boundaries above and should be
resolved with tests and representative user scenarios in their respective
development phases.
