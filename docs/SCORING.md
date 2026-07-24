# Health scoring

ActionDoctor calculates one deterministic health score from rule findings. The
score is local, offline, and independent of repository size, elapsed time, or
network data.

## Formula

Every scan starts at 100. Findings contribute these penalties:

| Severity | Penalty |
|---|---:|
| critical | 20 |
| high | 10 |
| medium | 4 |
| low | 1 |
| info | 0 |

The raw penalty is the sum of all finding penalties. To keep repeated instances
of one problem from dominating the result, the contribution of each rule ID is
capped at 20 points. Penalties from different rule IDs still accumulate.

```text
raw rule penalty = sum(severity weight for findings with that rule ID)
capped rule penalty = min(raw rule penalty, 20)
total capped penalty = sum(capped rule penalties)
health score = max(0, 100 - total capped penalty)
```

The score result exposes the starting score, raw and capped total penalties,
final score, penalties by severity and rule ID, and finding counts by severity
and category. `penalty_by_rule_id` contains the capped contribution used in the
final score; `penalty_by_severity` describes the uncapped raw penalty.

For example, three high `SEC003` findings have a raw penalty of 30 but a
capped contribution of 20, producing a score of 80. One high finding each from
`SEC003` and `REL001` contributes 10 points per rule and also produces 80.

## Ratings

| Score | Rating |
|---:|---|
| 90-100 | Excellent |
| 75-89 | Good |
| 50-74 | Needs attention |
| 0-49 | Poor |

## Completeness

Parse errors and rule execution errors do not change the numeric score. They
instead mark the result `incomplete`, and the terminal report shows the errors
separately. This prevents an operational failure from becoming an undocumented
score penalty while making clear that the score covers only successfully
analyzed workflows and rule evaluations.

## Score and process exit are separate

The score is a summary, not the CLI failure policy. `--fail-on` controls which
finding severity produces exit code 1 and defaults to `high`. Accepted values
are `critical`, `high`, `medium`, `low`, and `never`. Parse or rule execution
errors produce exit code 1 even with `--fail-on never`.

Terminal, JSON, and Markdown reporters consume this same score result. Changing
`--format` or adding `--output` cannot change penalties, ratings, completeness,
or the configured exit threshold.

## Limitations

A numeric score is a prioritization aid, not proof that a workflow is secure,
correct, reliable, inexpensive, or maintainable. ActionDoctor can only score
the enabled deterministic rules against workflows it successfully parses. The
per-rule cap deliberately trades sensitivity to repetition for resistance to
one widespread pattern dominating a large repository, and repositories with
more distinct issue types can still accumulate larger penalties.

The policy is intentionally simple for the current pre-1.0 release. Changes to
weights, caps, or rating boundaries are public behavior and require tests and
documentation updates.
