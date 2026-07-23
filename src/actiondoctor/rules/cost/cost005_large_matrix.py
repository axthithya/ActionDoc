"""COST005: detect large statically countable job matrices."""

from collections.abc import Mapping
from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.cost.helpers import (
    iter_jobs,
    location_fields,
    static_matrix_size,
)


class LargeMatrixRule:
    """Report static matrix Cartesian products above a configurable threshold."""

    rule_id = "COST005"
    title = "Large Unbounded Matrix"
    description = "A static job matrix generates many combinations."
    category = RuleCategory.COST
    default_severity = Severity.MEDIUM

    def __init__(self, threshold: int = 12) -> None:
        if threshold < 1:
            raise ValueError("Matrix threshold must be positive")
        self.threshold = threshold

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        """Count only fully static list dimensions and ignore exclude reductions."""
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            strategy = job.job.get("strategy")
            if not isinstance(strategy, Mapping):
                continue
            size = static_matrix_size(strategy.get("matrix"))
            if size is None or size.base_combinations <= self.threshold:
                continue
            yaml_path = f"{job.yaml_path}.strategy.matrix"
            include_note = (
                f" The matrix also declares {size.include_additions} static "
                "`include` addition(s)."
                if size.include_additions
                else ""
            )
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    description=(
                        f"Job `{job.job_id}` has an estimated static Cartesian "
                        f"product of {size.base_combinations} combinations."
                        f"{include_note}"
                    ),
                    severity=self.default_severity,
                    category=self.category,
                    file_path=Path(workflow.relative_path),
                    job_id=job.job_id,
                    yaml_path=yaml_path,
                    remediation=(
                        "Reduce static matrix dimensions, split specialized cases, "
                        "or otherwise keep the base product at or below "
                        f"{self.threshold} when practical."
                    ),
                    **location_fields(workflow, yaml_path),
                )
            )
        return findings
