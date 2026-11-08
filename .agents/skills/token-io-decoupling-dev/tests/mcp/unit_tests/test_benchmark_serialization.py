"""基准报告脱敏的标量、容器和模型序列化边界。"""

from pathlib import Path

import optimization_benchmark as benchmark
import pytest


class _ReportModel:
    def model_dump(self, *, mode):
        assert mode == "json"
        return {"value": 3, "API_KEY": "must disappear"}


class _BrokenModel:
    def model_dump(self, *, mode):
        raise ValueError("private diagnostic must disappear")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="none"),
        pytest.param(True, True, id="boolean"),
        pytest.param(0, 0, id="zero"),
        pytest.param("text", "text", id="text"),
        pytest.param(1.5, 1.5, id="finite-float"),
        pytest.param(float("nan"), None, id="nan"),
        pytest.param(float("inf"), None, id="infinity"),
        pytest.param(Path("reports/result.json"), "reports/result.json", id="path"),
        pytest.param(
            ValueError("private diagnostic"), {"error_type": "ValueError"}, id="exception"
        ),
        pytest.param(
            {1: (2, {"Authorization": "private", "ok": 4})},
            {"1": [2, {"ok": 4}]},
            id="nested-redaction",
        ),
        pytest.param(_ReportModel(), {"value": 3}, id="model"),
        pytest.param(_BrokenModel(), {"value_type": "_BrokenModel"}, id="broken-model"),
        pytest.param(object(), {"value_type": "object"}, id="unknown-object"),
    ],
)
def test_report_values_are_json_safe_and_redact_private_fields(value, expected):
    assert benchmark._json_safe(value) == expected
