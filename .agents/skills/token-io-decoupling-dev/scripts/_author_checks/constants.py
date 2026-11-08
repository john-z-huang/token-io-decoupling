"""仓库私有文档校验的容量、语言镜像和层级约束。"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

MAX_CANDIDATES = 64


MAX_PATH_CHARS = 512


MAX_FILE_CHARS = 131_072


MAX_BATCH_UTF8_BYTES = 524_288


MAX_DIRECT_TARGETS = 256


MAX_OUTPUT_CHECKS = 512


MAX_CHECK_MESSAGE_CHARS = 512


POLICY_VERSION = 1


POLICY_SCOPES = frozenset({"skill_maintenance", "generic_project"})


OPERATIONS = frozenset({"create", "replace", "delete"})


STATUS_VALUES = frozenset({"pass", "fail", "unknown", "not_applicable"})


PAIR_ROOTS = (
    "README.md",
    "INSTALL.md",
    ".agents/skills/token-io-decoupling-dev/SKILL.md",
    ".agents/skills/token-io-decoupling-dev/AGENTS.md",
    ".agents/skills/token-io-decoupling-dev/references/MULTI_LINGUAL.md",
    "instruction-compiler/sources/skill/SKILL.md",
    "AGENTS.md",
    "instruction-compiler/sources/skill/workflows/coding.md",
    "instruction-compiler/sources/skill/WORKFLOW_ARCHITECTURE.md",
    ".agents/skills/token-io-decoupling-dev/references/EXTERNAL_REFERENCES.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/AGENTS.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/CODEX_CALLER_CONTEXT.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/CANDIDATE_COMPLIANCE.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/OUTPUT_MATERIALIZATION.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/DEVELOPMENT.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/OPTIMIZATION_BENCHMARK.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/TASK_PLAN_TOOLS.md",
    ".agents/skills/token-io-decoupling-dev/references/mcp/WORKFLOW_ROUTING.md",
)


_PAIR_ROOT_SET = frozenset(PAIR_ROOTS)


ZH_SUFFIX = "_zh_cn.md"


_PAIR_ROOT_ZH_NAMES = frozenset(f"{PurePosixPath(path).stem}{ZH_SUFFIX}" for path in PAIR_ROOTS)


LAYER01_HEADINGS = {
    "en": (
        "General rules",
        "Codex CLI / ChatGPT Desktop optimizations",
        "Claude Code CLI / Claude Desktop optimizations",
    ),
    "zh": (
        "通用规范",
        "Codex CLI / ChatGPT Desktop 特别优化指令",
        "Claude Code CLI / Claude Desktop 特别优化指令",
    ),
}


LAYER01_NAVIGATION = {"en": "Related concepts", "zh": "相关概念"}


_HEADING_RE = re.compile(r"^## (.+?)\s*$")


_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")


_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


_INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")


_MULTILINGUAL_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


_LANGUAGE_SWITCH_LABELS = {"english", "简体中文"}


_MODULES = (
    "entry-readiness",
    "session-readiness",
    "work-definition",
    "single-execution",
    "delegated-execution",
    "verification-repair",
    "documentation",
    "delivery-acceptance",
)


_ROUTE_MODULES = {
    "coding-single-agent": (
        "entry-readiness",
        "session-readiness",
        "work-definition",
        "single-execution",
        "verification-repair",
        "documentation",
        "delivery-acceptance",
    ),
    "coding-multi-agent": (
        "entry-readiness",
        "session-readiness",
        "work-definition",
        "delegated-execution",
        "verification-repair",
        "documentation",
        "delivery-acceptance",
    ),
}
