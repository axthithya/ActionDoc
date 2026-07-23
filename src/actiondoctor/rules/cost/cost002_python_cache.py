"""COST002: detect uncached Python dependency installation."""

from actiondoctor.rules.cost.dependency_cache import DependencyCacheRule
from actiondoctor.rules.cost.helpers import PYTHON_INSTALL


class MissingPythonCacheRule(DependencyCacheRule):
    """Report setup-python jobs that install dependencies without prior caching."""

    rule_id = "COST002"
    title = "Missing Python Dependency Cache"
    description = "A Python dependency installation has no preceding cache."
    setup_action = "actions/setup-python"
    install_pattern = PYTHON_INSTALL
    ecosystem = "Python"
