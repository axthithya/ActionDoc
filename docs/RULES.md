# ActionDoctor Rules

## Design principles

Rules are deterministic, offline, side-effect free, and independently
testable. A rule receives one parsed `WorkflowFile` and returns zero or more
`Finding` models. Rules do not perform file I/O, print output, calculate
scores, choose exit codes, or know about report formats.

The engine gives each evaluation a deep copy of the workflow model. This
prevents a faulty rule from changing the shared parsed content observed by
another rule.

## Rule interface

Rules structurally implement the `Rule` protocol:

```python
class Rule(Protocol):
    rule_id: str
    title: str
    description: str
    category: RuleCategory
    default_severity: Severity

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]: ...
```

Metadata must be available without evaluating a rule.

## Rule IDs

Rule IDs are permanent public identifiers:

| Category | Prefix | Example |
|----------|--------|---------|
| Security | `SEC` | `SEC001` |
| Cost | `COST` | `COST001` |
| Reliability | `REL` | `REL001` |
| Maintainability | `MAINT` | `MAINT001` |

The suffix is a nonzero, three-digit sequence from `001` through `999`. IDs
are uppercase, must match the declared category, and are never reused for a
different meaning.

## Current rules

### SEC001 — Overly Broad Workflow Permissions

- Severity: critical for `write-all`; high for mappings with at least two
  declared scopes all set to `write`.
- Detects broad top-level write permission grants.
- Why it matters: an unnecessarily powerful `GITHUB_TOKEN` increases the
  impact of a compromised step.

Bad:

```yaml
permissions: write-all
```

Safer:

```yaml
permissions:
  contents: read
  pull-requests: write
```

Known limitations: SEC001 does not determine the permissions a workflow
actually needs. A single explicitly writable scope is treated as narrow to
avoid flagging every legitimate write operation.

### SEC002 — Missing Explicit Permissions

- Severity: medium.
- Detects a missing top-level `permissions` key when at least one job also
  lacks its own declaration.
- Why it matters: explicit permissions avoid relying on repository or
  organization defaults that may change.

Bad:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
```

Safer:

```yaml
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
```

Known limitations: the rule checks declaration presence, not whether the
selected scopes are sufficient or minimal. It emits one workflow-level
finding, even when multiple jobs inherit defaults.

### SEC003 — Third-Party Action Not Pinned to Commit SHA

- Severity: high.
- Detects mutable `uses:` references in mapping-shaped workflow steps.
- Why it matters: tags and branches can move to different code after review.

Bad:

```yaml
- uses: actions/checkout@v4
```

Safer:

```yaml
- uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
```

Known limitations: official GitHub actions are intentionally not exempt.
Local `./` actions, `docker://` references, and job-level reusable workflows
are outside this rule. Action ownership and commit authenticity are not
verified because ActionDoctor does not access GitHub.

### SEC004 — Untrusted Pull Request Checkout Risk

- Severity: critical.
- Detects `pull_request_target` workflows where an `actions/checkout` step has
  an explicit `ref` containing a known pull-request head expression.
- Why it matters: `pull_request_target` runs in the base repository context;
  executing checked-out pull-request code there may expose secrets or write
  permissions.

Bad:

```yaml
on: pull_request_target
steps:
  - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
    with:
      ref: ${{ github.event.pull_request.head.sha }}
```

Safer:

```yaml
on: pull_request
steps:
  - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
```

Known limitations: this rule is intentionally conservative. It recognizes
specific `head.sha`, `head.ref`, and `github.head_ref` expressions and does
not claim that a workflow is exploitable. Indirect data flow, later script
execution, and custom checkout implementations are not analyzed.

### SEC005 — Secret Exposed Through Workflow-Level Environment

- Severity: medium.
- Detects top-level environment values containing direct `secrets.NAME`
  references.
- Why it matters: workflow-level environment variables are broadly available
  to jobs and steps that may not need the secret.

Bad:

```yaml
env:
  TOKEN: ${{ secrets.DEPLOY_TOKEN }}
```

Safer:

```yaml
jobs:
  deploy:
    steps:
      - run: ./deploy
        env:
          TOKEN: ${{ secrets.DEPLOY_TOKEN }}
```

Known limitations: bracket-form secret references and shell-script leakage
are not inspected. Job-level and step-level secret environments are
deliberately not reported by SEC005.

### MAINT001 — Missing Workflow Name

- Category: maintainability
- Severity: low
- Reports when top-level `name` is absent, null, empty, or whitespace-only.
- Does not report a non-empty string or another non-null scalar value.
- Remediation: add a descriptive top-level workflow name.

Because the temporary CLI failure threshold is `high`, MAINT001 alone does not
make a scan fail.

### REL001 — Missing Jobs

- Category: reliability
- Severity: high
- Reports when top-level `jobs` is absent, empty, or not a mapping.
- Does not report a non-empty jobs mapping.
- Remediation: add at least one job under the top-level `jobs` key.

REL001 reaches the temporary CLI failure threshold and makes the scan return
exit code 1.

## Explicit registry

The default registry is a tuple of explicitly constructed rule instances in
`actiondoctor.registry`. There is no package scanning, dynamic import,
entry-point loading, or plugin discovery.

Registry construction validates:

- strict rule-ID syntax;
- unique rule IDs;
- agreement between ID prefix and category;
- valid severity/category enum values; and
- non-empty titles and descriptions.

Registry results are always returned in ascending rule-ID order. Filtering by
category retains that order. Filtering by ID rejects unknown IDs instead of
silently ignoring them.

## Engine behavior and ordering

The engine sorts workflows by portable relative path and rules by rule ID,
then evaluates every rule against every successfully parsed workflow. “Total
rules executed” in CLI output means the number of rule/workflow evaluations.
For example, two rules over three workflows produces six executions.

Findings have this deterministic order:

1. portable workflow path, case-insensitive then exact;
2. one-based line, with unknown lines last;
3. one-based column, with unknown columns last;
4. severity, from critical through info;
5. rule ID; and
6. title, case-insensitive then exact.

If a rule raises an unexpected exception, the engine continues. It records the
rule ID, portable workflow path, exception type, and a fixed safe message. Raw
exception messages are intentionally excluded because they may contain local
paths or environment details. A rule execution failure makes the CLI return
exit code 1 because analysis was incomplete.

## Adding a rule

1. Reserve the next permanent ID in the appropriate category.
2. Add one focused module below `src/actiondoctor/rules/<category>/`.
3. Implement the `Rule` protocol and return typed `Finding` models.
4. Export the implementation from its category package.
5. Add one explicit instance to `DEFAULT_RULES`.
6. Add rule tests and registry-wide validation tests where applicable.
7. Document detection behavior, false-positive boundaries, severity, and
   remediation here.
8. Add a changelog entry.

Adding a rule must not require changes to the engine, parser, scoring, or
reporting code.

## Testing expectations

Each rule needs:

- a minimal positive case;
- a minimal negative case;
- absent, empty, malformed, and dynamic-value edge cases where relevant;
- exact metadata, severity, path, YAML path, and remediation assertions;
- false-positive regression cases; and
- proof that evaluation does not rely on network or filesystem access.

Engine and registry tests cover ordering, filtering, duplicate/invalid IDs,
multi-workflow execution, multiple findings, deduplication, mutation
isolation, and exception isolation.
