"""COST003: detect uncached Node dependency installation."""

from actiondoctor.rules.cost.dependency_cache import DependencyCacheRule
from actiondoctor.rules.cost.helpers import NODE_INSTALL


class MissingNodeCacheRule(DependencyCacheRule):
    """Report setup-node jobs that install dependencies without prior caching."""

    rule_id = "COST003"
    title = "Missing Node Dependency Cache"
    description = "A Node dependency installation has no preceding cache."
    setup_action = "actions/setup-node"
    install_pattern = NODE_INSTALL
    ecosystem = "Node"
