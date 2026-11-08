"""输出文件保护与退役协议禁止创建真实客户端。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import benchmark_cases as cases
import optimization_benchmark as benchmark
import pytest
from benchmark_support.fixtures import (
    _runner_case_module,
)


def test_live_cli_rejects_existing_output_before_loading_cases_or_creating_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "existing.json"
    output.write_text("preserve this report", encoding="utf-8")
    monkeypatch.setattr(benchmark, "_suppress_sdk_logs", lambda: None)

    def fail_load() -> Any:
        raise AssertionError("cases loaded before the output collision was rejected")

    def fail_recorder(**_kwargs: object) -> Any:
        raise AssertionError("a recorder was created before output validation")

    monkeypatch.setattr(
        benchmark,
        "_load_case_module",
        fail_load,
    )
    monkeypatch.setattr(
        benchmark,
        "Recorder",
        fail_recorder,
    )

    status = benchmark.main(["--live", "--output", str(output)])
    captured = capsys.readouterr()

    assert status == 2
    assert output.read_text(encoding="utf-8") == "preserve this report"
    assert "benchmark_output_rejected" in captured.err
    assert "preserve this report" not in captured.err


def test_retired_historical_protocol_stops_before_recorder_credentials_or_case(
    tmp_path, monkeypatch
):
    output = tmp_path / "retired-report.json"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    def forbidden_recorder(**_kwargs):
        raise AssertionError("retired protocol created a recorder")

    report = benchmark.run_benchmark(
        output,
        repo_root=Path(__file__).resolve().parents[7],
        case_module=cases,
        recorder_factory=forbidden_recorder,
    )
    assert report["status"] == "retired"
    assert report["blocking_reason"] == "retired_benchmark_protocol"
    assert report["api_calls"] == [] and report["http_attempts"] == 0
    assert report["validation"]["measurement_valid"] is False
    assert report["validation"]["token_comparison_valid"] is False
    assert json.loads(output.read_text())["protocol_status"] == "retired"


def test_synthetic_fixture_cannot_use_the_live_recorder(tmp_path):
    case_module = _runner_case_module(
        lambda *_: (_ for _ in ()).throw(AssertionError("case executed"))
    )
    report = benchmark.run_benchmark(
        tmp_path / "synthetic-blocked.json",
        repo_root=Path(__file__).resolve().parents[7],
        case_module=case_module,
    )
    assert report["status"] == "blocked"
    assert report["blocking_reason"] == "no_supported_live_benchmark_protocol"
    assert report["api_calls"] == [] and report["http_attempts"] == 0
