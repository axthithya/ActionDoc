"""Production maintainability rules."""

from actiondoctor.rules.maintainability.maint001_missing_workflow_name import (
    MissingWorkflowNameRule,
)
from actiondoctor.rules.maintainability.maint002_missing_job_name import (
    MissingJobNameRule,
)
from actiondoctor.rules.maintainability.maint003_unnamed_run_step import (
    UnnamedRunStepRule,
)
from actiondoctor.rules.maintainability.maint004_oversized_job import OversizedJobRule
from actiondoctor.rules.maintainability.maint005_duplicate_step_name import (
    DuplicateStepNameRule,
)
from actiondoctor.rules.maintainability.maint006_long_inline_script import (
    LongInlineShellScriptRule,
)

__all__ = [
    "DuplicateStepNameRule",
    "LongInlineShellScriptRule",
    "MissingJobNameRule",
    "MissingWorkflowNameRule",
    "OversizedJobRule",
    "UnnamedRunStepRule",
]
