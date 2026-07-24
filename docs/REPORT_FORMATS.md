# Report formats

ActionDoc renders terminal, JSON, and Markdown reports from the same immutable
scan result. Selecting a format changes presentation only: it does not rerun
rules, recalculate the health score, change severities, or alter exit policy.

SARIF and GitHub annotations are not supported yet.

## CLI usage

Terminal output is the default:

```bash
actiondoctor scan .
actiondoctor scan . --format terminal
```

Write JSON or Markdown directly to standard output:

```bash
actiondoctor scan . --format json --fail-on never
actiondoctor scan . --format markdown --fail-on never
```

Write a report to a file:

```bash
actiondoctor scan . --format json --output reports/actiondoc.json
actiondoctor scan . --format markdown --output reports/actiondoc.md
```

`--output` is accepted only with `json` or `markdown`. Missing parent
directories are created. ActionDoc renders the complete report first, writes a
temporary file beside the destination, and atomically replaces the destination
only after the write succeeds. Existing reports are replaced. A failure leaves
no partially written destination and returns exit code 2.

Successful file output prints one short confirmation instead of the report.

## JSON schema version 1.0

JSON output is UTF-8, indented, deterministic, and terminated by a newline. It
contains no Rich markup, ANSI escapes, progress messages, or surrounding text.
Optional finding fields are always present and use `null` when unavailable.

The top-level fields are:

| Field | Meaning |
|---|---|
| `schema_version` | Public report schema; currently `1.0` |
| `actiondoctor_version` | ActionDoctor package version |
| `repository` | Repository selected for the scan |
| `completeness` | `complete` or `incomplete` |
| `workflows_discovered` | Candidate workflow count |
| `workflows_parsed` | Successfully parsed workflow count |
| `active_rule_count` | Enabled rules evaluated by the scan |
| `rule_workflow_evaluation_count` | Rule/workflow evaluation count |
| `finding_count` | Total findings |
| `parse_error_count` | Workflow parsing failures |
| `rule_execution_error_count` | Isolated rule execution failures |
| `starting_score` | Score before finding penalties |
| `health_score` | Final score from 0 through 100 |
| `health_rating` | Human-readable rating |
| `raw_penalty` | Penalty before per-rule caps |
| `capped_penalty` | Penalty used by the final score |
| `severity_summary` | Finding counts keyed by severity |
| `category_summary` | Finding counts keyed by category |
| `penalty_by_severity` | Uncapped penalty keyed by severity |
| `penalty_by_rule_id` | Capped contribution keyed by rule ID |
| `findings` | Ordered public finding objects |
| `parse_errors` | Ordered workflow parse diagnostics |
| `rule_execution_errors` | Ordered, safe rule diagnostics |

Each finding includes `rule_id`, `title`, `description`, `severity`,
`category`, `file`, `line`, `column`, `job_id`, `step_index`, `step_name`,
`yaml_path`, `remediation`, and `documentation_url`. Step indices are exposed
when the existing YAML path identifies one. Step names remain `null` until the
finding model carries that information explicitly. Workflow paths use forward
slashes and are relative to the repository whenever possible.

The 1.x contract is additive: fields documented for schema 1.0 will not be
removed or reinterpreted without a schema-version change. Consumers should
ignore unknown fields so compatible additions remain possible. ActionDoc is
pre-1.0 software; any necessary incompatible report change will increment the
report schema and be documented in the changelog.

## Markdown structure

Markdown output is a standalone UTF-8 document ending with a newline. It has:

1. `# ActionDoc Report` header;
2. scan and health summary;
3. a visible incomplete-analysis warning when needed;
4. compact severity and category tables;
5. findings grouped under workflow headings;
6. description, location, job, step, YAML path, and remediation details; and
7. separate parse-error and rule-execution-error sections.

When no findings exist, the findings section says so explicitly. Values that
may originate in workflows are escaped to avoid changing Markdown structure.
No HTML or terminal escape sequences are emitted.

## Exit codes are format-independent

Report format and file destination never determine success or failure:

| Exit code | Meaning |
|---:|---|
| 0 | No configured failure condition |
| 1 | Parse error, rule error, or finding meeting `--fail-on` |
| 2 | Invalid usage, invalid repository, output failure, or application error |

`--fail-on never` disables finding-based failure only. Incomplete analysis
still exits 1 in every format. The numeric health score is never used as an
exit threshold.

## Compatibility expectations

- Output ordering is deterministic for equivalent scan results.
- Workflow paths are portable and do not expose absolute workflow filenames.
- JSON standard output is exactly one document on successful scans.
- Markdown standard output contains no confirmation or terminal formatting.
- Terminal output remains the default and supports `--no-color`.
- Reporters are offline and do not mutate scan data.
- The reusable GitHub Action selects these existing JSON or Markdown outputs;
  see [`GITHUB_ACTION.md`](GITHUB_ACTION.md) for runner and step-summary
  behavior.
