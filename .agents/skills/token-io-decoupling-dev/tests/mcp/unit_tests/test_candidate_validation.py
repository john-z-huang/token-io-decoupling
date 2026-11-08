"""候选内容校验的操作契约、错误优先级与批次边界。"""

from copy import deepcopy
from typing import Any

import pytest

from token_io_decoupling_core.compliance_core import (
    MAX_BATCH_UTF8_BYTES,
    ComplianceInputError,
    validate_candidate_list,
)


@pytest.mark.parametrize(
    ("operation", "baseline", "content", "expected_baseline"),
    [
        ("create", {"state": "absent", "value": None}, "新内容", {"state": "absent"}),
        (
            "replace",
            {"state": "sha256", "value": "a" * 64},
            "",
            {"state": "sha256", "value": "a" * 64},
        ),
        (
            "delete",
            {"state": "sha256", "value": "b" * 64},
            None,
            {"state": "sha256", "value": "b" * 64},
        ),
    ],
    ids=["create-omits-null-digest", "replace-allows-empty-content", "delete-has-no-content"],
)
def test_normalization_preserves_input(
    operation: str, baseline: dict[str, Any], content: str | None, expected_baseline: dict[str, Any]
) -> None:
    candidate = {
        "path": "src/result.py",
        "operation": operation,
        "baseline": baseline,
        "content": content,
    }
    original = deepcopy(candidate)

    normalized = validate_candidate_list([candidate])

    assert normalized == [
        {
            "path": "src/result.py",
            "operation": operation,
            "baseline": expected_baseline,
            "content": content,
        }
    ]
    assert candidate == original
    assert normalized[0]["baseline"] is not baseline


@pytest.mark.parametrize(
    ("operation", "baseline", "content", "reason"),
    [
        ("create", {"state": "sha256"}, None, "create_requires_absent_baseline"),
        ("replace", {"state": "absent"}, None, "replace_delete_require_sha256_baseline"),
        ("delete", {"state": "sha256", "value": "a" * 64}, "", "delete_must_not_include_content"),
        ("create", {"state": "absent"}, None, "create_replace_require_content"),
        ("create", {"state": "absent"}, "\ud800", "candidate_content_not_valid_utf8"),
    ],
    ids=[
        "create-baseline-first",
        "replace-baseline-first",
        "delete-content",
        "missing-content",
        "invalid-utf8",
    ],
)
def test_invalid_candidate_keeps_error_reason(
    operation: str, baseline: dict[str, Any], content: str | None, reason: str
) -> None:
    candidate = {
        "path": "src/result.py",
        "operation": operation,
        "baseline": baseline,
        "content": content,
    }

    with pytest.raises(ComplianceInputError, match=f"^{reason}$"):
        validate_candidate_list([candidate])


def test_batch_utf8_limit_includes_all_files_and_allows_delete_at_limit() -> None:
    candidates = [
        {
            "path": f"src/{index}.py",
            "operation": "create",
            "baseline": {"state": "absent"},
            "content": "界" * 43_690 + "ab",
        }
        for index in range(4)
    ]
    candidates.append(
        {
            "path": "src/obsolete.py",
            "operation": "delete",
            "baseline": {"state": "sha256", "value": "a" * 64},
            "content": None,
        }
    )
    assert MAX_BATCH_UTF8_BYTES == 524_288
    assert len(validate_candidate_list(candidates)) == 5

    candidates.append(
        {
            "path": "src/overflow.py",
            "operation": "create",
            "baseline": {"state": "absent"},
            "content": "a",
        }
    )
    with pytest.raises(ComplianceInputError, match="^candidate_batch_byte_limit_exceeded$"):
        validate_candidate_list(candidates)
