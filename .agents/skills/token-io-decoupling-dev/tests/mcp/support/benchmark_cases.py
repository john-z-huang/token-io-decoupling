"""Read-only registry for retired Issue 182 benchmark protocols.

Historical datasets and reports remain evidence of their original product contract.
They cannot measure or establish comparability with compiled-instruction delivery or
with the generic-only materializer. A separately reviewed protocol is required.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

DEVELOPMENT = Path(__file__).resolve().parents[3]
DATASET_PATH = DEVELOPMENT / "benchmarks/issue_182_cases.json"
DATASET = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
CASE_IDS = tuple(item["case_id"] for item in DATASET["cases"])
_CASES = {item["case_id"]: item for item in DATASET["cases"]}
PROTOCOL_STATUS = "retired"
RETIREMENT_REASON = "retired_benchmark_protocol"
REMOVED_PRODUCT_CASES = frozenset(
    {"skill_cross_language_preflight_fail", "primary_skill_fact_markdown_apply"}
)

# Current harness provenance is used only by synthetic telemetry unit fixtures.
# It does not rebind or update any archived measurement's original fingerprints.
_COMMON_SOURCES = [
    ".agents/skills/token-io-decoupling-dev/benchmarks/issue_182_cases.json",
    ".agents/skills/token-io-decoupling-dev/tests/mcp/support/benchmark_cases.py",
    ".agents/skills/token-io-decoupling-dev/tests/mcp/support/benchmark_metrics.py",
    ".agents/skills/token-io-decoupling-dev/tests/mcp/support/optimization_benchmark.py",
]
_CASE_SOURCES = {
    "rules_current_verification": [
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/rules.py"
    ],
    "multi_auto_work_definition": [
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/events/checks.py"
    ],
    "generic_create_preflight_pass": [
        "mcp/packages/token_io_decoupling_tools/src/token_io_decoupling_tools/compliance_preflight.py"
    ],
    "skill_cross_language_preflight_fail": [
        ".agents/skills/token-io-decoupling-dev/scripts/_compliance_core.py"
    ],
    "primary_skill_fact_markdown_apply": [
        ".agents/skills/token-io-decoupling-dev/tests/mcp/unit_tests/test_output_materialization.py"
    ],
}


def _service_metadata(service: str) -> tuple[dict[str, object], list[str]]:
    return {
        "historical_service": service,
        "protocol_status": PROTOCOL_STATUS,
        "measurement_supported": False,
    }, []


def run_case(
    case_id: str, arm: str, recorder: Any, repo_root: Path, temporary_root: Path
) -> dict[str, object]:
    """Disposition an archived case without clients, temporary projects, or effects."""
    if case_id not in _CASES or arm not in {"baseline", "assisted"}:
        raise ValueError("unknown historical case or arm")
    return {
        "case_id": case_id,
        "arm": arm,
        "execution_status": "not_applicable",
        "protocol_status": PROTOCOL_STATUS,
        "reason": RETIREMENT_REASON,
        "product_capability_removed": case_id in REMOVED_PRODUCT_CASES,
        "semantic_success": None,
        "workflow_completed": None,
        "api_calls": [],
        "http_attempts": 0,
        "token_comparison_valid": False,
        "historical_dataset_sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
    }
