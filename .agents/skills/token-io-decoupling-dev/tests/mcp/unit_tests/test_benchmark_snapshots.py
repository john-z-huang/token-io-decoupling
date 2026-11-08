"""当前合成遥测来源清单须包含拆分后的实际实现。"""

from pathlib import Path

import benchmark_cases as cases
import optimization_benchmark as benchmark

REPO_ROOT = Path(__file__).resolve().parents[6]


def test_source_fingerprints_include_modularized_harness():
    paths = benchmark._source_manifest(cases, cases.CASE_IDS, REPO_ROOT)
    prefix = ".agents/skills/token-io-decoupling-dev/tests/mcp/support/benchmark_support/"

    assert prefix + "runner.py" in paths
    assert prefix + "execution.py" in paths
    assert prefix + "snapshots.py" in paths
    assert prefix + "serialization.py" in paths
    assert all((REPO_ROOT / path).is_file() for path in paths)
