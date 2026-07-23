"""Tests for deterministic health scoring."""

from pathlib import Path

import pytest

from actiondoctor.models import (
    Finding,
    HealthRating,
    RuleCategory,
    ScanCompleteness,
    Severity,
)
from actiondoctor.scoring import HealthScorer, health_rating


def finding(
    rule_id: str,
    severity: Severity,
    category: RuleCategory = RuleCategory.SECURITY,
) -> Finding:
    """Build a focused scoring finding."""
    return Finding(
        rule_id=rule_id,
        title="Test finding",
        description="A test finding.",
        severity=severity,
        category=category,
        file_path=Path(".github/workflows/ci.yml"),
    )


def test_clean_scan_scores_one_hundred() -> None:
    result = HealthScorer().score([])

    assert result.final_score == 100
    assert result.rating is HealthRating.EXCELLENT
    assert result.completeness is ScanCompleteness.COMPLETE


@pytest.mark.parametrize(
    ("severity", "penalty"),
    [
        (Severity.CRITICAL, 20),
        (Severity.HIGH, 10),
        (Severity.MEDIUM, 4),
        (Severity.LOW, 1),
        (Severity.INFO, 0),
    ],
)
def test_severity_weights(severity: Severity, penalty: int) -> None:
    result = HealthScorer().score([finding("SEC001", severity)])

    assert result.raw_penalty == penalty
    assert result.final_score == 100 - penalty


def test_repeated_rule_penalty_is_capped_at_twenty() -> None:
    findings = [finding("SEC001", Severity.HIGH) for _ in range(4)]

    result = HealthScorer().score(findings)

    assert result.raw_penalty == 40
    assert result.penalty_by_rule_id == {"SEC001": 20}
    assert result.capped_penalty == 20
    assert result.final_score == 80


def test_distinct_rule_penalties_accumulate_and_score_floors_at_zero() -> None:
    findings = [
        finding(rule_id, Severity.CRITICAL)
        for rule_id in ("SEC001", "SEC002", "SEC003", "SEC004", "SEC005")
    ]

    result = HealthScorer().score(findings)

    assert result.capped_penalty == 100
    assert result.final_score == 0


@pytest.mark.parametrize(
    ("score", "rating"),
    [
        (100, HealthRating.EXCELLENT),
        (90, HealthRating.EXCELLENT),
        (89, HealthRating.GOOD),
        (75, HealthRating.GOOD),
        (74, HealthRating.NEEDS_ATTENTION),
        (50, HealthRating.NEEDS_ATTENTION),
        (49, HealthRating.POOR),
        (0, HealthRating.POOR),
    ],
)
def test_health_rating_boundaries(score: int, rating: HealthRating) -> None:
    assert health_rating(score) is rating


def test_breakdowns_include_all_severities_and_categories() -> None:
    result = HealthScorer().score(
        [finding("COST001", Severity.MEDIUM, RuleCategory.COST)]
    )

    assert result.finding_count_by_severity[Severity.MEDIUM] == 1
    assert result.penalty_by_severity[Severity.MEDIUM] == 4
    assert result.finding_count_by_category[RuleCategory.COST] == 1
    assert set(result.finding_count_by_severity) == set(Severity)
    assert set(result.finding_count_by_category) == set(RuleCategory)


def test_input_order_does_not_change_result() -> None:
    findings = [
        finding("SEC002", Severity.LOW),
        finding("SEC001", Severity.HIGH),
    ]

    assert HealthScorer().score(findings) == HealthScorer().score(reversed(findings))


@pytest.mark.parametrize(
    ("parse_errors", "execution_errors", "completeness"),
    [
        (0, 0, ScanCompleteness.COMPLETE),
        (1, 0, ScanCompleteness.INCOMPLETE),
        (0, 1, ScanCompleteness.INCOMPLETE),
        (1, 1, ScanCompleteness.INCOMPLETE),
    ],
)
def test_errors_change_completeness_not_numeric_score(
    parse_errors: int,
    execution_errors: int,
    completeness: ScanCompleteness,
) -> None:
    result = HealthScorer().score(
        [],
        parse_error_count=parse_errors,
        execution_error_count=execution_errors,
    )

    assert result.final_score == 100
    assert result.completeness is completeness
