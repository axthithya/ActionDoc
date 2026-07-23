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

### COST001 - Missing Concurrency Cancellation

- Severity: medium.
- Detects `pull_request` and `pull_request_target` workflows without a
  top-level concurrency mapping that has literal `cancel-in-progress: true`.
- Why it may affect runner usage: superseded commits can leave older workflow
  runs executing even though a newer pull-request result is more relevant.

Bad:

```yaml
on: pull_request
jobs:
  test: {}
```

Improved:

```yaml
on: pull_request
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

False-positive considerations: push-only, scheduled-only, and manually
triggered workflows are ignored. Mapping, scalar, and list event syntax are
supported. Expression-based groups are accepted.

Known limitations: an expression-based `cancel-in-progress` value is reported
with uncertain wording because its result cannot be determined statically.
The rule does not evaluate expression semantics or job-level concurrency.

### COST002 - Missing Python Dependency Cache

- Severity: low.
- Detects a job that uses `actions/setup-python`, runs a recognized Python
  dependency installation command, and has no configured setup cache or
  earlier `actions/cache` step.
- Why it may affect runner usage: repeatedly downloading unchanged dependency
  artifacts can lengthen otherwise identical jobs.

Bad:

```yaml
steps:
  - uses: actions/setup-python@0123456789abcdef0123456789abcdef01234567
  - run: python -m pip install -r requirements.txt
```

Improved:

```yaml
steps:
  - uses: actions/setup-python@0123456789abcdef0123456789abcdef01234567
    with:
      cache: pip
  - run: python -m pip install -r requirements.txt
```

False-positive considerations: the rule requires both the setup action and a
recognized install command in the same job. It reports at most once per job.
An `actions/cache` step only suppresses the finding when it precedes the first
recognized installation.

Known limitations: matching is intentionally lexical and recognizes command
segments beginning with `pip install`, `pip3 install`, `python[3] -m pip
install`, `poetry install`, or `pipenv install`. Wrappers, aliases, environment
variable indirection, and custom scripts are not interpreted. An earlier
`actions/cache` is assumed relevant; its path and key are not validated.

### COST003 - Missing Node Dependency Cache

- Severity: low.
- Detects a job that uses `actions/setup-node`, runs a recognized Node
  dependency installation command, and has no configured setup cache or
  earlier `actions/cache` step.
- Why it may affect runner usage: restoring package-manager data can avoid
  repeated dependency downloads across otherwise similar runs.

Bad:

```yaml
steps:
  - uses: actions/setup-node@0123456789abcdef0123456789abcdef01234567
  - run: npm ci
```

Improved:

```yaml
steps:
  - uses: actions/setup-node@0123456789abcdef0123456789abcdef01234567
    with:
      cache: npm
  - run: npm ci
```

False-positive considerations: jobs that only execute Node commands without a
recognized dependency installation are ignored. A cache must be configured
before the first installation, and only one finding is emitted per job.

Known limitations: matching recognizes command segments beginning with `npm
install`, `npm ci`, `yarn install`, or `pnpm install`. It does not interpret
package scripts, wrappers, aliases, or custom cache implementations. An
earlier `actions/cache` is assumed relevant without validating its inputs.

### COST004 - Unrestricted Push Workflow

- Severity: low.
- Detects statically identifiable push triggers without branch, path, or tag
  filters.
- Why it may affect runner usage: some workflows only need to run for selected
  branches or changed paths, although running on every push can be intentional.

Bad:

```yaml
on: push
```

Improved:

```yaml
on:
  push:
    branches: [main]
    paths:
      - "src/**"
```

False-positive considerations: `push: false`, absent push events, and push
events with `branches`, `branches-ignore`, `paths`, `paths-ignore`, `tags`, or
`tags-ignore` are ignored. The finding says filters *may* reduce runs and does
not claim the workflow is wasteful.

Known limitations: dynamic or otherwise unsupported push configurations are
ignored. The rule cannot know whether broad push coverage is a project
requirement or whether downstream job conditions already limit work.

### COST005 - Large Unbounded Matrix

- Severity: medium.
- Detects a matrix whose fully static list-dimension Cartesian product exceeds
  12 combinations.
- Why it may affect runner usage: every generated combination can create a
  separate job, so additional dimensions multiply execution.

Bad:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python: ["3.10", "3.11", "3.12", "3.13", "3.14"]
```

Improved:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    python: ["3.12", "3.13", "3.14"]
```

False-positive considerations: exactly 12 base combinations are accepted.
Dynamic matrices and any matrix with an uncountable non-special dimension are
ignored. `include` and `exclude` are excluded from the base product; a
statically countable `include` list is mentioned separately.

Known limitations: `exclude` entries are not subtracted because partial-match
semantics make a simple static estimate misleading. `include` entries are
reported as declared additions but do not affect the threshold. Expressions
and effective GitHub job limits are not evaluated.

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

- Default severity: low.
- Detects an absent, null, empty, or whitespace-only top-level workflow name.
- Why it matters: a descriptive name makes workflow runs easier to identify in
  the GitHub Actions interface.

Problematic:

```yaml
on: push
jobs: {}
```

Improved:

```yaml
name: Pull request checks
on: pull_request
jobs: {}
```

False-positive considerations: non-empty strings and other non-null scalar
values retain the existing accepted behavior.

Known limitations: the rule checks presence, not whether a name is unique,
accurate, or follows project terminology. It does not fail a scan under the
current high-severity threshold.

### MAINT002 — Missing Job Name

- Default severity: low.
- Detects mapping-shaped ordinary jobs without a non-empty string `name`.
- Why it matters: descriptive job names make workflow runs and failures easier
  to understand in the GitHub Actions interface.

Problematic:

```yaml
jobs:
  unit-tests:
    runs-on: ubuntu-24.04
```

Improved:

```yaml
jobs:
  unit-tests:
    name: Python unit tests
    runs-on: ubuntu-24.04
```

False-positive considerations: job-level reusable workflow calls using `uses`,
malformed job values, and jobs with non-empty string names are ignored.

Known limitations: the rule does not judge whether a supplied name is useful,
unique, or consistent with other workflows. A terse job ID may already be
clear to a small team.

### MAINT003 — Unnamed Run Step

- Default severity: low.
- Detects mapping-shaped steps with scalar `run` content but no non-empty
  string name.
- Why it matters: named run steps make logs and failures easier to locate and
  review.

Problematic:

```yaml
steps:
  - run: pytest
```

Improved:

```yaml
steps:
  - name: Run Python tests
    run: pytest
```

False-positive considerations: unnamed `uses` steps, malformed step entries,
non-string `run` values, and named run steps are ignored. Each finding includes
the job ID and zero-based step index through its YAML path and description.

Known limitations: ActionDoctor does not evaluate whether a supplied step name
accurately describes its command or whether GitHub's generated label is
sufficient for a particular workflow.

### MAINT004 — Oversized Job

- Default severity: medium.
- Threshold: more than 15 mapping-shaped steps in one job.
- Detects jobs with at least 16 valid step mappings and includes the measured
  step count.
- Why it matters: very large jobs can be harder to review, navigate, and debug.

Problematic:

```yaml
jobs:
  build:
    steps:
      # 16 or more mapping-shaped steps
```

Improved when appropriate:

```yaml
jobs:
  test:
    steps:
      - run: ./scripts/test.sh
  package:
    needs: test
    steps:
      - run: ./scripts/package.sh
```

False-positive considerations: exactly 15 valid steps are accepted. Scalar,
null, list, and other malformed step entries are not counted.

Known limitations: step count is only a structural signal. A cohesive 16-step
job may be clearer than an artificial split, so remediation presents focused
jobs, reusable workflows, composite actions, and scripts as options rather
than mandatory changes.

### MAINT005 — Duplicate Step Name

- Default severity: low.
- Detects duplicate non-empty step names within one job and reports every
  occurrence after the first.
- Why it matters: repeated labels make logs and failure summaries harder to
  distinguish.

Problematic:

```yaml
steps:
  - name: Run tests
    run: pytest
  - name: Run Tests
    run: npm test
```

Improved:

```yaml
steps:
  - name: Run Python tests
    run: pytest
  - name: Run Node tests
    run: npm test
```

False-positive considerations: names are trimmed and compared
case-insensitively. Empty names are ignored, and names are never compared
across different jobs.

Known limitations: intentionally repeated labels are still reported. The rule
does not compare shell commands, action references, or semantic step behavior.

### MAINT006 — Long Inline Shell Script

- Default severity: low.
- Threshold: more than 20 non-empty lines in a scalar `run` value.
- Detects run steps with at least 21 non-empty script lines and includes the
  measured line count.
- Why it matters: moving long shell logic into a version-controlled script can
  improve isolated testing, readability, and reuse.

Problematic:

```yaml
steps:
  - name: Build and publish
    run: |
      # more than 20 non-empty lines
      prepare
      build
      publish
```

Improved when appropriate:

```yaml
steps:
  - name: Build and publish
    run: ./scripts/build-and-publish.sh
```

False-positive considerations: exactly 20 non-empty lines are accepted. Blank
lines, including leading and trailing blanks, are excluded. Non-string `run`
values and non-run steps are ignored.

Known limitations: the rule measures lines only and never inspects shell
commands or complexity. Some readable scripts legitimately exceed the
threshold, so extraction is a consideration rather than a requirement.

### REL001 — Missing Jobs

- Default severity: high.
- Detects an absent, empty, or non-mapping top-level `jobs` value.
- Why it may affect reliability: a workflow without a valid job cannot perform
  its intended automation.

Problematic:

```yaml
name: CI
on: push
```

Improved:

```yaml
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - run: pytest
```

False-positive considerations: any non-empty jobs mapping is accepted; job
schema validation belongs to focused rules and GitHub's workflow validator.

Known limitations: REL001 does not determine whether jobs can execute or
whether their dependencies and conditions are reachable. It reaches the
temporary high-severity CLI threshold and makes the scan return exit code 1.

### REL002 — Missing Job Timeout

- Default severity: medium.
- Detects ordinary mapping-shaped jobs without a positive static
  `timeout-minutes` value.
- Why it may affect reliability: an unbounded hung command can occupy a runner
  until the platform terminates it.

Problematic:

```yaml
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - run: pytest
```

Improved:

```yaml
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
      - run: pytest
```

False-positive considerations: reusable-workflow jobs with job-level `uses`
and malformed job values are ignored. Positive numeric values are accepted.
Expression-based values are ignored because their result cannot be evaluated
offline.

Known limitations: ActionDoctor does not infer an ideal timeout. Remediation
intentionally asks maintainers to choose a value based on expected job
duration rather than prescribing one universal number.

### REL003 — Mutable Container Image Reference

- Default severity: medium.
- Detects untagged images and confidently floating tags such as `latest`,
  `stable`, `edge`, and `nightly` in job containers and services.
- Why it may affect reliability: a mutable reference can resolve to different
  container content without a workflow change.

Problematic:

```yaml
container:
  image: postgres:latest
services:
  cache:
    image: redis
```

Improved:

```yaml
container:
  image: postgres:16.3
services:
  cache:
    image: redis@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

False-positive considerations: fixed tags, digest references, dynamic
expressions, empty values, and unsupported container shapes are ignored.
Registry ports are separated from tags using the final path component, so
`localhost:5000/image:1.2` is treated as tagged.

Known limitations: tags other than the documented floating set are accepted,
even though registries can technically move any tag. ActionDoctor does not
query registries, verify digest availability, or inspect images mentioned in
shell commands.

### REL004 — Moving Runner Label

- Default severity: low.
- Detects `ubuntu-latest`, `windows-latest`, and `macos-latest` as scalar
  values or members of a fully static runner-label list.
- Why it may affect reliability: a `*-latest` label may point to a newer
  hosted image in the future and introduce unexpected environment changes.

Problematic:

```yaml
runs-on: ubuntu-latest
```

Improved:

```yaml
runs-on: ubuntu-24.04
```

False-positive considerations: versioned labels, `self-hosted`, unsupported
values, matrix expressions, and lists containing expressions are ignored.

Known limitations: custom labels that organizations repoint are not detected.
The rule does not inspect runner image contents or predict GitHub's image
migration schedule.

### REL005 — Failure Ignored With Continue-on-Error

- Default severity: medium for steps and high for jobs.
- Detects literal boolean `continue-on-error: true` at job or step scope.
- Why it may affect reliability: ignored failures may allow dependent jobs or
  deployments to continue without a required result.

Problematic:

```yaml
jobs:
  deploy:
    continue-on-error: true
    steps:
      - run: ./deploy
```

Improved:

```yaml
jobs:
  deploy:
    steps:
      - run: ./deploy
```

False-positive considerations: literal `false`, strings, and expressions are
ignored. Findings identify the job and, for steps, include the zero-based
index and a non-empty step name when available. Each YAML location is reported
once.

Known limitations: `continue-on-error` can be intentional for experimental or
advisory work. The rule does not claim every use is wrong; remediation asks
maintainers to confirm intent and keep the ignored failure visible. Only a
job-level high finding reaches the current CLI failure threshold.

### REL006 — Service Container Without Health Check

- Default severity: low.
- Detects statically analyzable service containers with an image but without a
  recognizable `--health-cmd` in their Docker options.
- Why it may affect reliability: a health check can help dependent test
  commands wait until a service is ready.

Problematic:

```yaml
services:
  database:
    image: postgres:16.3
```

Improved:

```yaml
services:
  database:
    image: postgres:16.3
    options: >-
      --health-cmd "pg_isready"
      --health-interval 10s
```

False-positive considerations: services without images, malformed service
values, dynamic images, dynamic options, unsupported option types, and options
containing `--health-cmd` are ignored.

Known limitations: the rule recognizes command presence but cannot validate
whether the command accurately represents readiness. GitHub Actions does not
always require a health check, and the finding does not claim otherwise.

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
