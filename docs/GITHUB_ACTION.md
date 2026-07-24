# GitHub Action

ActionDoc is a composite GitHub Action that installs the ActionDoc source from
the exact checked-out action reference and invokes the existing Python CLI. It
does not contain another scanner, upload artifacts, call GitHub APIs, create
annotations, or use SARIF.

## Use in a workflow

Check out the repository being audited, then use an immutable ActionDoc commit:

```yaml
permissions:
  contents: read

jobs:
  actiondoc:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Check out repository
        # actions/checkout v4.2.2
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Audit workflows
        # Replace with the immutable release commit that contains action.yml.
        uses: axthithya/ActionDoc@79b223ff6ae0a53440e51cea9e35fe7833aecf2b
        with:
          path: .
          fail-on: high
          report-format: markdown
```

The shown ActionDoc SHA is the verified `main` commit available while this
integration was developed. Before publishing this action, replace it with the
immutable release commit that includes `action.yml`; a moving tag is more
convenient but less immutable. The repository includes the same template at
[`examples/actiondoc-workflow.yml`](../examples/actiondoc-workflow.yml).

## Inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Repository path passed to `actiondoctor scan`. |
| `fail-on` | `high` | `critical`, `high`, `medium`, `low`, or `never`. |
| `report-format` | `markdown` | `markdown`, `json`, or `none`. |
| `report-path` | empty | Optional generated-report destination. |

For Markdown and JSON, an omitted `report-path` becomes
`$RUNNER_TEMP/actiondoc-report.md` or `$RUNNER_TEMP/actiondoc-report.json`.
`report-path` cannot be used with `report-format: none`.

## Output

| Output | Description |
|---|---|
| `report-path` | Generated report path; empty for `none` or when report creation fails. |

Use it from a later step, for example:

```yaml
- id: audit
  uses: axthithya/ActionDoc@<immutable-release-sha>

- run: test -f "${{ steps.audit.outputs.report-path }}"
```

The action does not expose health-score output. Parsing a public JSON report is
the stable option when a workflow needs score data.

## Reports and step summaries

`report-format: markdown` writes a Markdown report and appends that exact
report to `$GITHUB_STEP_SUMMARY` when GitHub provides it. `json` writes a JSON
report but does not append to the summary. `none` uses the normal terminal
report and creates no exported report.

Reports are written through ActionDoc's atomic output path. The action never
uploads reports: use the `report-path` output with a separate artifact step if
you need retention.

## Exit codes

The wrapper preserves the existing CLI result:

| Exit code | Meaning |
|---:|---|
| 0 | No configured failure condition. |
| 1 | Parse error, isolated rule error, or finding at `fail-on`. |
| 2 | Invalid action input, invalid repository path, report failure, or application failure. |

`fail-on: never` disables only finding-based failure. It does not hide parse
or rule execution errors.

## Runner assumptions and local testing

The composite action expects a runner with `python` available; GitHub-hosted
Ubuntu runners provide it. It installs the package from `$GITHUB_ACTION_PATH`
using that exact action checkout, then installs only runtime dependencies.

The repository CI tests the local action using `uses: ./`. You can exercise the
entry point locally with temporary GitHub files:

```bash
export GITHUB_OUTPUT="$(mktemp)"
export GITHUB_STEP_SUMMARY="$(mktemp)"
export RUNNER_TEMP="$(mktemp -d)"
python scripts/github_action_entrypoint.py
```

On PowerShell, create equivalent temporary files/directories and set the same
environment variables. Local execution without `GITHUB_OUTPUT` or
`GITHUB_STEP_SUMMARY` is supported; it simply skips those integrations.

The CI's expected-failure fixture uses `continue-on-error` intentionally so a
following assertion can verify that ActionDoc preserved exit code 1. This is a
test harness exception, not a recommendation for consumer workflows.

## Limitations

- The action does not install Python for self-hosted runners.
- It does not upload, retain, or annotate reports.
- It does not make GitHub API calls.
- SARIF is not supported.
- The action source must be pinned to a release commit that contains its
  metadata; update the example SHA as part of release preparation.
