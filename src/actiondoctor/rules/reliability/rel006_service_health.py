"""REL006: detect service containers without a static Docker health check."""

from pathlib import Path

from actiondoctor.models import Finding, RuleCategory, Severity, WorkflowFile
from actiondoctor.rules.reliability.helpers import (
    has_health_check,
    iter_jobs,
    iter_services,
    location_fields,
)


class ServiceWithoutHealthCheckRule:
    """Report analyzable service containers missing `--health-cmd`."""

    rule_id = "REL006"
    title = "Service Container Without Health Check"
    description = "A service container has no recognizable Docker health check."
    category = RuleCategory.RELIABILITY
    default_severity = Severity.LOW

    def evaluate(self, workflow: WorkflowFile) -> list[Finding]:
        findings: list[Finding] = []
        for job in iter_jobs(workflow):
            for service in iter_services(job):
                health_check = has_health_check(service.service.get("options"))
                if health_check is not False:
                    continue
                yaml_path = f"{service.yaml_path}.options"
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        description=(
                            f"Service `{service.service_id}` in job `{job.job_id}` "
                            "has no recognizable `--health-cmd` option."
                        ),
                        severity=self.default_severity,
                        category=self.category,
                        file_path=Path(workflow.relative_path),
                        job_id=job.job_id,
                        yaml_path=yaml_path,
                        remediation=(
                            "When readiness matters, add an appropriate Docker "
                            "`--health-cmd` so dependent commands can wait for a "
                            "healthy service."
                        ),
                        **location_fields(
                            workflow,
                            yaml_path,
                            fallback_path=service.yaml_path,
                        ),
                    )
                )
        return findings
