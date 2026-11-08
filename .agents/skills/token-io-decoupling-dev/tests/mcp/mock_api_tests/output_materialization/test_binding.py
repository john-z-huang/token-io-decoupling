"""Worker 身份、调用会话及写入能力边界。"""

from __future__ import annotations

import pytest
from support.materialization_workspace import (
    _literal_prepare,
    _workspace,
)

from token_io_decoupling_core.workflow_models import (
    HostGuard as Guard,
)
from token_io_decoupling_tools.output_materialization import (
    MaterializationAuthorizationContext,
    OutputMaterializationService,
)


@pytest.mark.parametrize("caller_binding", [None, "different_worker"])
def test_materialization_requires_matching_current_caller_binding(
    tmp_path, caller_binding: str | None
) -> None:
    path = "src/output.txt"
    project, artifacts, binding, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    materializer.execute = OutputMaterializationService.execute.__get__(materializer)
    try:
        expected = (
            binding.model_copy(update={"current_session_id": "another-worker"})
            if caller_binding == "different_worker"
            else None
        )
        result = materializer.execute(
            _literal_prepare(path, "candidate\n"), expected_binding=expected
        )
        assert result["status"] == "blocked"
        assert result["reason_code"] == "caller_binding_assignment_mismatch"
        assert not (project / path).exists()
        assert not list(artifacts.iterdir())
    finally:
        materializer.close()
        preflight.close()


@pytest.mark.parametrize(
    ("binding_change", "expected_reason"),
    [
        ("missing_write", "worker_write_capability_missing"),
        ("missing_identity_guard", "worker_binding_guards_missing"),
        ("missing_session_guard", "worker_binding_guards_missing"),
        ("missing_path_guard", "worker_binding_guards_missing"),
    ],
)
def test_materialization_requires_write_capability_and_identity_session_path_guards(
    tmp_path, binding_change: str, expected_reason: str
) -> None:
    path = "src/output.txt"
    project, artifacts, binding, provider, preflight, _grant, _config, materializer = _workspace(
        tmp_path, [path]
    )
    materializer.execute = OutputMaterializationService.execute.__get__(materializer)
    original_context = provider.current_context
    if binding_change == "missing_write":
        altered_binding = binding.model_copy(update={"capabilities": frozenset()})
    else:
        missing_guard = {
            "missing_identity_guard": Guard.IDENTITY_BOUND,
            "missing_session_guard": Guard.SESSION_BOUND,
            "missing_path_guard": Guard.PATH_BOUNDARY,
        }[binding_change]
        altered_binding = binding.model_copy(
            update={
                "guards": frozenset(guard for guard in binding.guards if guard != missing_guard)
            }
        )
    provider.current_context = lambda: MaterializationAuthorizationContext(
        altered_binding,
        original_context().assignment,
        original_context().assignment_hash,
    )
    try:
        result = materializer.execute(
            _literal_prepare(path, "candidate\n"), expected_binding=altered_binding
        )
        assert result["status"] == "blocked"
        assert result["reason_code"] == expected_reason
        assert not (project / path).exists()
        assert not list(artifacts.iterdir())
    finally:
        materializer.close()
        preflight.close()
