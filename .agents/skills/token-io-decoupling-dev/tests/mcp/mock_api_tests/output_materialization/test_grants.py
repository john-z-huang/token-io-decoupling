"""操作员 grant 的范围、版本及撤销约束。"""

from __future__ import annotations

from pathlib import Path

import pytest
from support.materialization_workspace import (
    _apply,
    _literal_prepare,
    _string_field,
    _workspace,
)

from token_io_decoupling_core.materialization_models import (
    MaterializationInspectRequest,
)


def test_grant_revision_change_immediately_before_publish_blocks_write(
    tmp_path, monkeypatch
) -> None:
    path = "src/output.txt"
    project, _artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        store = materializer._storage
        assert store is not None
        assert grant_provider.grant is not None
        read_project_file = store.read_project_file
        read_count = 0

        def mutate_grant_after_apply_baseline_read(target_path: str, *, limit: int):
            nonlocal read_count
            content = read_project_file(target_path, limit=limit)
            read_count += 1
            if read_count == 2:
                grant_provider.grant = grant_provider.grant.model_copy(update={"revision": 2})
            return content

        monkeypatch.setattr(store, "read_project_file", mutate_grant_after_apply_baseline_read)
        result = _apply(materializer, prepared)
        assert result["status"] == "blocked"
        assert result["reason_code"] == "worker_or_operator_grant_changed"
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


@pytest.mark.parametrize(
    ("grant_update", "expected_reason"),
    [
        (
            {
                "role": "Documentation/Comments & Git Operations",
                "output_class": "skill_instructions",
            },
            "operator_grant_unavailable_or_invalid",
        ),
        ({"allowed_paths": ["src/other.txt"]}, "materialization_path_not_authorized"),
        ({"allowed_operations": ["replace"]}, "materialization_operation_not_authorized"),
        ({"allowed_templates": ["json_document"]}, "materialization_template_not_authorized"),
    ],
)
def test_prepare_enforces_current_grant_role_class_path_operation_and_template(
    tmp_path, grant_update: dict[str, object], expected_reason: str
) -> None:
    path = "src/output.txt"
    _project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        assert grant_provider.grant is not None
        grant_provider.grant = grant_provider.grant.model_copy(update=grant_update)
        result = materializer.execute(_literal_prepare(path, "candidate\n"))
        assert result["status"] == "blocked"
        assert result["reason_code"] == expected_reason
        assert not list(artifacts.iterdir())
    finally:
        materializer.close()
        preflight.close()


@pytest.mark.parametrize(
    ("grant_update", "expected_reason"),
    [
        (
            {"role": "Documentation/Comments & Git Operations"},
            "operator_grant_unavailable_or_invalid",
        ),
        (
            {"output_class": "ordinary_documentation"},
            "operator_grant_unavailable_or_invalid",
        ),
    ],
)
def test_unsupported_materialization_role_or_class_fails_before_writing(
    tmp_path, grant_update: dict[str, str], expected_reason: str
) -> None:
    path = "src/output.txt"
    project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        assert grant_provider.grant is not None
        invalid_grant = grant_provider.grant.model_dump(mode="python")
        invalid_grant.update(grant_update)
        grant_provider.grant = invalid_grant

        result = materializer.execute(_literal_prepare(path, "must not persist\n"))
        assert result["status"] == "blocked"
        assert result["reason_code"] == expected_reason
        assert not list(artifacts.iterdir())
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_changed_grant_revision_blocks_existing_prepared_artifact(tmp_path) -> None:
    path = "src/output.txt"
    _project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        assert grant_provider.grant is not None
        grant_provider.grant = grant_provider.grant.model_copy(update={"revision": 2})
        inspected = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=_string_field(prepared, "prepared_id"),
                expected_manifest_hash=_string_field(prepared, "manifest_sha256"),
                file_index=0,
            )
        )
        applied = _apply(materializer, prepared)
        assert inspected["status"] == "blocked"
        assert applied["status"] == "blocked"
        assert list(artifacts.iterdir())
        assert not (Path(_config.project_root) / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_revoked_grant_blocks_inspect_and_changed_assignment_hash_does_not_authorize(
    tmp_path,
) -> None:
    path = "src/output.txt"
    _project, _artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        grant_provider.grant = grant_provider.grant.model_copy(
            update={"active": False, "revision": 2}
        )
        blocked = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=_string_field(prepared, "prepared_id"),
                expected_manifest_hash=_string_field(prepared, "manifest_sha256"),
                file_index=0,
            )
        )
        assert blocked["status"] == "blocked"
        assert blocked["reason_code"] == "operator_grant_unavailable_or_invalid"
    finally:
        materializer.close()
        preflight.close()
