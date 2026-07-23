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
multi-workflow execution, multiple findings, mutation isolation, and exception
isolation.
