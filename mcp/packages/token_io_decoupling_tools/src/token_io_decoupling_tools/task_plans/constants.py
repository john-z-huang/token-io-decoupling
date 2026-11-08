"""任务计划的容量、标识符和历史块格式约束。"""

from __future__ import annotations

import re

MAX_PLAN_BYTES = 1_000_000


MAX_RECORDS_PER_OPERATION = 100


MAX_EVENTS = 10_000


_PLAN_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


_RECORD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


_REVISION = re.compile(r"^[a-f0-9]{64}$")


_REPOSITORY_ID = re.compile(r"^git-v1-[a-f0-9]{64}$")


_HEADER_PREFIX = b"~~~json task-plan-header-v1\n"


_HEADER_V2_PREFIX = b"~~~json task-plan-header-v2\n"


_HEADER_SUFFIX = b"\n~~~\n"


_EVENT_PREFIX = b"~~~json task-plan-event-v1\n"


_EVENT_V2_PREFIX = b"~~~json task-plan-event-v2\n"


_EVENT_SUFFIX = b"\n~~~\n"


_KINDS = {
    "goal",
    "criterion",
    "verification",
    "blocker",
    "resolution",
    "result",
    "limitation",
    "constraint",
    "requirement",
    "fact",
    "decision",
    "progress",
}


_OUTCOMES = {"passed", "failed", "assumed", "unavailable"}


_GLOBAL_MEMORY_PREFIX = "global/token-io-decoupling/repos"


_GIT_IDENTITY_DOMAIN = b"token-io-decoupling:git-common-dir:v1\0"


_GIT_IDENTITY_TIMEOUT_SECONDS = 3


_GIT_IDENTITY_MAX_OUTPUT_BYTES = 8192


_GIT_REDIRECT_ENVIRONMENT = ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE")
