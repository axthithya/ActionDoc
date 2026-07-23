"""Deterministic, explainable health-score calculation."""

from collections import Counter, defaultdict
from collections.abc import Iterable

from actiondoctor.models.enums import (
    HealthRating,
    RuleCategory,
    ScanCompleteness,
    Severity,
)
from actiondoctor.models.finding import Finding
from actiondoctor.models.score import ScoreResult

STARTING_SCORE = 100
PER_RULE_PENALTY_CAP = 20
SEVERITY_WEIGHTS: dict[Severity, int] = {
    Severity.CRITICAL: 20,
    Severity.HIGH: 10,
    Severity.MEDIUM: 4,
    Severity.LOW: 1,
    Severity.INFO: 0,
}


class HealthScorer:
    """Calculate one stable score from rule findings and error counts."""

    def score(
        self,
        findings: Iterable[Finding],
        *,
        parse_error_count: int = 0,
        execution_error_count: int = 0,
    ) -> ScoreResult:
        """Return score, rating, breakdowns, and completeness."""
        ordered_findings = sorted(
            findings,
            key=lambda finding: (
                finding.rule_id,
                finding.severity.value,
                finding.file_path.as_posix(),
                finding.yaml_path or "",
                finding.line or 0,
                finding.column or 0,
            ),
        )
        severity_counts: Counter[Severity] = Counter()
        category_counts: Counter[RuleCategory] = Counter()
        raw_by_rule: defaultdict[str, int] = defaultdict(int)

        for finding in ordered_findings:
            severity_counts[finding.severity] += 1
            category_counts[finding.category] += 1
            raw_by_rule[finding.rule_id] += SEVERITY_WEIGHTS[finding.severity]

        penalty_by_severity = {
            severity: severity_counts[severity] * SEVERITY_WEIGHTS[severity]
            for severity in Severity
        }
        penalty_by_rule_id = {
            rule_id: min(raw_penalty, PER_RULE_PENALTY_CAP)
            for rule_id, raw_penalty in sorted(raw_by_rule.items())
        }
        raw_penalty = sum(raw_by_rule.values())
        capped_penalty = sum(penalty_by_rule_id.values())
        final_score = max(0, STARTING_SCORE - capped_penalty)
        completeness = (
            ScanCompleteness.COMPLETE
            if parse_error_count == 0 and execution_error_count == 0
            else ScanCompleteness.INCOMPLETE
        )

        return ScoreResult(
            starting_score=STARTING_SCORE,
            raw_penalty=raw_penalty,
            capped_penalty=capped_penalty,
            final_score=final_score,
            rating=health_rating(final_score),
            penalty_by_severity=penalty_by_severity,
            penalty_by_rule_id=penalty_by_rule_id,
            finding_count_by_severity={
                severity: severity_counts[severity] for severity in Severity
            },
            finding_count_by_category={
                category: category_counts[category] for category in RuleCategory
            },
            completeness=completeness,
        )


def health_rating(score: int) -> HealthRating:
    """Map a bounded score to its public rating."""
    if not 0 <= score <= 100:
        raise ValueError("Health score must be between 0 and 100")
    if score >= 90:
        return HealthRating.EXCELLENT
    if score >= 75:
        return HealthRating.GOOD
    if score >= 50:
        return HealthRating.NEEDS_ATTENTION
    return HealthRating.POOR


def clean_score_result() -> ScoreResult:
    """Create the default complete score for an empty result."""
    return HealthScorer().score([])


__all__ = [
    "PER_RULE_PENALTY_CAP",
    "SEVERITY_WEIGHTS",
    "STARTING_SCORE",
    "HealthScorer",
    "clean_score_result",
    "health_rating",
]
