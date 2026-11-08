"""Context Exchange 胶囊格式、Git 快照及来源指纹类型。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

IGNORE_RULE = ".token-io-decoupling"


EXCHANGE_DIR = Path(".token-io-decoupling")


CAPSULE_DIR = EXCHANGE_DIR / "context" / "context-bootstrap"


MAX_CONTEXT_BYTES = 64 * 1024


SOURCE_ROW_RE = re.compile(
    r"(?m)^\|\s*`?([^|`]+?)`?\s*\|\s*`?([0-9a-f]{40})`?\s*\|\s*$", re.IGNORECASE
)


class SourceEntry(NamedTuple):
    name: str
    recorded_hash: str
    path: Path | None


class _CapsuleWorktreeSnapshot(NamedTuple):
    """用于核对胶囊新鲜度的当前 Git 快照。"""

    head: str
    tree: str
    diff: str
    status: str
