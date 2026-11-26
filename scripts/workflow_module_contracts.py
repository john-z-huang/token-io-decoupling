"""单代理与多代理路线共用的阶段和 Hook 绑定。"""

from pathlib import Path

WORKFLOW_PATH = Path("workflows")
WORKFLOW_SELECTOR = WORKFLOW_PATH / "coding.yaml"
PHASES = ("entry", "definition", "execution", "verification", "delivery")
ROUTE_HOOKS = {
    "coding-single-agent": ("entry", "planning", "execution", "verification", "delivery"),
    "coding-multi-agent": ("entry", "planning", "delegation", "verification", "delivery"),
}
TOP_PREFIXES = {"coding-single-agent": "SM", "coding-multi-agent": "MM"}
