from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, cast

import pytest
from mcp import Client
from pydantic import ValidationError
from token_io_decoupling_core.materialization_models import (
    AbsentBaseline,
    DirectoryIdentity,
    FactHeading,
    FactMarkdownTemplate,
    FactOrderingItem,
    FactOrderingPlan,
    LiteralTextTemplate,
    MaterializationApplyRequest,
    MaterializationFileSpec,
    MaterializationInspectRequest,
    MaterializationOperation,
    MaterializationPrepareRequest,
    OutputMaterializationGrant,
    PreparedMaterializationManifest,
    SourceFact,
)
from token_io_decoupling_core.workflow_models import (
    BindingIdentity,
    OutputClass,
    SessionRole,
)
from token_io_decoupling_core.workflow_models import (
    HostCapability as Cap,
)
from token_io_decoupling_core.workflow_models import (
    HostGuard as Guard,
)
from token_io_decoupling_tools.compliance_preflight import CompliancePreflightService
from token_io_decoupling_tools.materialization_storage import MaterializationStorageError
from token_io_decoupling_tools.output_materialization import (
    MaterializationAssignment,
    MaterializationAuthorizationContext,
    OutputMaterializationService,
    OutputMaterializerConfig,
    materialization_assignment_hash,
)

from token_io_decoupling.server import create_tools_server


def _result_text(result) -> str:
    return result.content[0].text


PARENT_CAPS = frozenset(
    {
        Cap.WORKER_WRITE,
    }
)
PARENT_GUARDS = frozenset({Guard.IDENTITY_BOUND, Guard.SESSION_BOUND, Guard.PATH_BOUNDARY})
CHILD_CAPS = frozenset({Cap.WORKER_WRITE})
CHILD_GUARDS = frozenset(
    {
        Guard.IDENTITY_BOUND,
        Guard.SESSION_BOUND,
        Guard.PATH_BOUNDARY,
        Guard.PARENT_CHILD_RELATION,
    }
)


class _GrantProvider:
    def __init__(self) -> None:
        self.grant: OutputMaterializationGrant | None = None

    def current_grant(self) -> OutputMaterializationGrant | None:
        return self.grant


def _workspace(
    tmp_path: Path,
    paths: list[str],
    *,
    allowed_operations: list[MaterializationOperation] | None = None,
    output_class: OutputClass = OutputClass.CODE_CONFIGURATION,
):
    project = tmp_path / "project"
    artifacts = tmp_path / "artifacts"
    project.mkdir()
    artifacts.mkdir(mode=0o700)
    os.chmod(artifacts, 0o700)
    for parent in {str(Path(path).parent) for path in paths}:
        if parent != ".":
            (project / parent).mkdir(parents=True, exist_ok=True)

    worker_id = "worker-materialization"
    binding = BindingIdentity(
        project_id="project-a",
        root_session_id="root-a",
        current_session_id=worker_id,
        parent_session_id="root-a",
        role=SessionRole.WORKER,
        capabilities=CHILD_CAPS,
        guards=CHILD_GUARDS,
    )
    assignment = MaterializationAssignment(
        project_id="project-a",
        root_session_id="root-a",
        worker_session_id=worker_id,
        allocation_id="allocation-a",
        role="Primary Output",
        output_class=cast(Literal["code_configuration", "skill_instructions"], output_class.value),
        slice_id="slice-a",
        authorized_paths=tuple(paths),
    )
    assignment_dict = assignment.model_dump(mode="json")
    assignment_hash = materialization_assignment_hash(assignment)

    class AuthorizationProvider:
        def current_context(self):
            return MaterializationAuthorizationContext(binding, assignment, assignment_hash)

        def current_binding(self):
            return binding

    preflight = CompliancePreflightService(project, {"generic_project"})
    project_stat = project.stat()
    artifact_stat = artifacts.stat()
    grant_provider = _GrantProvider()
    grant_provider.grant = OutputMaterializationGrant(
        grant_id="operator-grant-1",
        revision=1,
        active=True,
        policy_version=1,
        project_id=assignment_dict["project_id"],
        root_session_id=assignment_dict["root_session_id"],
        worker_session_id=assignment_dict["worker_session_id"],
        allocation_id=assignment_dict["allocation_id"],
        role=assignment_dict["role"],
        output_class=assignment_dict["output_class"],
        slice_id=assignment_dict["slice_id"],
        assignment_hash=assignment_hash,
        project_root=DirectoryIdentity(device=project_stat.st_dev, inode=project_stat.st_ino),
        artifact_root=DirectoryIdentity(device=artifact_stat.st_dev, inode=artifact_stat.st_ino),
        policy_scope="generic_project",
        allowed_paths=paths,
        allowed_operations=allowed_operations or ["create", "replace"],
        allowed_templates=["literal_text", "json_document", "fact_markdown"],
        allow_responses_ordering=True,
    )
    provider = AuthorizationProvider()
    config = OutputMaterializerConfig(project, artifacts, grant_provider, provider)
    materializer = OutputMaterializationService(
        authorization_provider=provider,
        compliance_service=preflight,
        config=config,
    )
    assert binding.current_session_id == worker_id
    original_execute = materializer.execute

    def scoped_execute(request, *, expected_binding=None):
        return original_execute(request, expected_binding=expected_binding or binding)

    cast(Any, materializer).execute = scoped_execute
    return project, artifacts, binding, provider, preflight, grant_provider, config, materializer


def _literal_file(path: str, content: str) -> MaterializationFileSpec:
    return MaterializationFileSpec(
        path=path,
        operation="create",
        baseline=AbsentBaseline(state="absent"),
        template=LiteralTextTemplate(kind="literal_text", text=content),
    )


def _literal_prepare(path: str, content: str) -> MaterializationPrepareRequest:
    return MaterializationPrepareRequest(action="prepare", files=[_literal_file(path, content)])


def _string_field(result: dict[str, object], key: str) -> str:
    value = result.get(key)
    assert isinstance(value, str)
    return value


def _apply(
    materializer: OutputMaterializationService,
    prepared: dict[str, object],
    *,
    expected_binding=None,
):
    return materializer.execute(
        MaterializationApplyRequest(
            action="apply",
            prepared_id=_string_field(prepared, "prepared_id"),
            expected_manifest_hash=_string_field(prepared, "manifest_sha256"),
        ),
        expected_binding=expected_binding,
    )


def test_prepare_inspect_apply_and_create_retry_use_real_confirmed_assignment(tmp_path) -> None:
    path = "src/output.txt"
    project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path], allowed_operations=["create"])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "bounded result\n"))
        assert prepared["status"] == "prepared"
        assert not (project / path).exists()
        assert len(list(artifacts.iterdir())) == 1
        manifest_hash = prepared["manifest_sha256"]
        prepared_id = prepared["prepared_id"]
        inspected = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=prepared_id,
                expected_manifest_hash=manifest_hash,
                file_index=0,
                max_chars=5,
            )
        )
        assert inspected["status"] == "inspected"
        assert inspected["content"] == "bound"
        assert inspected["next_offset"] == 5
        assert inspected["complete"] is False

        applied = _apply(materializer, prepared)
        assert applied["status"] == "applied"
        assert applied["fresh_preflight"] == "pass"
        assert (project / path).read_text() == "bounded result\n"
        replay = _apply(materializer, prepared)
        assert replay["status"] == "already_identical"
        assert replay["files"][0]["status"] == "already_identical"
        assert (
            replay["preflight_projection"]
            == "already_identical_files_use_candidate_sha256_baseline"
        )
        assert grant_provider.grant is not None
        assert grant_provider.grant.allowed_operations == ["create"]
    finally:
        materializer.close()
        preflight.close()


def test_primary_output_skill_instructions_materialize_with_real_confirmed_assignment(
    tmp_path,
) -> None:
    path = "docs/skill-output.md"
    project, artifacts, state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(
            tmp_path,
            [path],
            allowed_operations=["create"],
            output_class=OutputClass.SKILL_INSTRUCTIONS,
        )
    )
    try:
        assignment = _provider.current_context().assignment
        assert assignment.role == "Primary Output"
        assert assignment.output_class == "skill_instructions"
        prepared = materializer.execute(_literal_prepare(path, "approved skill text\n"))
        assert prepared["status"] == "prepared"
        assert not (project / path).exists()
        assert len(list(artifacts.iterdir())) == 1

        applied = _apply(materializer, prepared)
        assert applied["status"] == "applied"
        assert (project / path).read_text() == "approved skill text\n"
    finally:
        materializer.close()
        preflight.close()


def test_partial_apply_replay_resumes_pending_file_and_blocks_reverted_applied_file(
    tmp_path, monkeypatch
) -> None:
    paths = ["src/first.txt", "src/second.txt"]
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        request = MaterializationPrepareRequest(
            action="prepare",
            files=[_literal_file(path, f"candidate {index}\n") for index, path in enumerate(paths)],
        )
        prepared = materializer.execute(request)
        store = materializer._storage
        assert store is not None
        original_publish = store.publish_project_file

        def fail_second(path: str, content: bytes, **kwargs):
            if path == paths[1]:
                return "conflict", None
            return original_publish(path, content, **kwargs)

        monkeypatch.setattr(store, "publish_project_file", fail_second)
        first = _apply(materializer, prepared)
        assert first["status"] == "partial"
        assert [item["status"] for item in first["files"]] == ["applied", "conflict"]

        monkeypatch.setattr(store, "publish_project_file", original_publish)
        resumed = _apply(materializer, prepared)
        assert resumed["status"] == "applied"
        assert [item["status"] for item in resumed["files"]] == [
            "already_identical",
            "applied",
        ]

        (project / paths[0]).unlink()
        reverted = _apply(materializer, prepared)
        assert reverted["status"] == "blocked"
        assert reverted["reason_code"] == "materialization_baseline_conflict"
        assert not (project / paths[0]).exists()
    finally:
        materializer.close()
        preflight.close()


def test_successful_replay_then_undo_is_not_reapplied(tmp_path) -> None:
    path = "src/output.txt"
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        assert _apply(materializer, prepared)["status"] == "applied"
        assert _apply(materializer, prepared)["status"] == "already_identical"

        (project / path).unlink()
        replay = _apply(materializer, prepared)
        assert replay["status"] == "blocked"
        assert replay["reason_code"] == "materialization_baseline_conflict"
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_uncertain_publish_then_confirmed_candidate_undo_is_not_reapplied(
    tmp_path, monkeypatch
) -> None:
    path = "src/output.txt"
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        store = materializer._storage
        assert store is not None
        publish = store.publish_project_file

        def publish_but_report_uncertain(*args, **kwargs):
            publish(*args, **kwargs)
            return "uncertain", None

        monkeypatch.setattr(store, "publish_project_file", publish_but_report_uncertain)
        uncertain = _apply(materializer, prepared)
        assert uncertain["files"][0]["status"] == "uncertain"
        assert (project / path).read_text() == "candidate\n"

        monkeypatch.setattr(store, "publish_project_file", publish)
        confirmed = _apply(materializer, prepared)
        assert confirmed["status"] == "already_identical"

        (project / path).unlink()
        replay = _apply(materializer, prepared)
        assert replay["status"] == "blocked"
        assert replay["reason_code"] == "materialization_baseline_conflict"
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_project_readback_failure_returns_uncertain_and_blocks_undo_replay(
    tmp_path, monkeypatch
) -> None:
    paths = ["src/first.txt", "src/second.txt"]
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        prepared = materializer.execute(
            MaterializationPrepareRequest(
                action="prepare",
                files=[
                    _literal_file(path, f"candidate {index}\n") for index, path in enumerate(paths)
                ],
            )
        )
        store = materializer._storage
        assert store is not None
        atomic_write = store._atomic_project_write

        def write_then_break_readback(*args, **kwargs):
            result = atomic_write(*args, **kwargs)
            read_file = store.read_file

            def fail_first_target_read(directory_fd, name, *, limit):
                if name == "first.txt":
                    raise MaterializationStorageError("project_readback_unavailable")
                return read_file(directory_fd, name, limit=limit)

            monkeypatch.setattr(store, "read_file", fail_first_target_read)
            return result

        monkeypatch.setattr(store, "_atomic_project_write", write_then_break_readback)
        uncertain = _apply(materializer, prepared)
        assert uncertain["status"] == "uncertain"
        assert [item["status"] for item in uncertain["files"]] == [
            "uncertain",
            "not_attempted",
        ]
        assert (project / paths[0]).read_text() == "candidate 0\n"

        (project / paths[0]).unlink()
        replay = _apply(materializer, prepared)
        assert replay["status"] == "blocked"
        assert replay["reason_code"] == "materialization_baseline_conflict"
        assert not any((project / path).exists() for path in paths)
    finally:
        materializer.close()
        preflight.close()


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


def test_api_grant_revision_change_prevents_candidate_persistence(tmp_path, monkeypatch) -> None:
    path = "src/output.md"
    _project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )

    class _Client:
        responses = None

        def __init__(self) -> None:
            self.responses = self

        def parse(self, **_kwargs):
            assert grant_provider.grant is not None
            grant_provider.grant = grant_provider.grant.model_copy(update={"revision": 2})
            return SimpleNamespace(
                status="completed",
                model="gpt-6-luna",
                error=None,
                incomplete_details=None,
                output_parsed=FactOrderingPlan(
                    files=[FactOrderingItem(file_index=0, fact_ids=["fact-1"])]
                ),
                output=[],
            )

        def close(self) -> None:
            pass

    try:
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
        monkeypatch.setattr(materializer._renderer, "_make_client", lambda *_args: _Client())
        request = MaterializationPrepareRequest(
            action="prepare",
            outbound_data_permitted=True,
            files=[
                MaterializationFileSpec(
                    path=path,
                    operation="create",
                    baseline=AbsentBaseline(state="absent"),
                    template=FactMarkdownTemplate(
                        kind="fact_markdown",
                        headings=[FactHeading(id="h", title="Facts")],
                        facts=[SourceFact(id="fact-1", heading_id="h", text="source fact")],
                        ordering="responses",
                    ),
                )
            ],
        )
        result = materializer.execute(request)
        assert result["status"] == "blocked"
        assert result["reason_code"] == "worker_or_operator_grant_changed"
        assert not list(artifacts.iterdir())
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
            "operator_grant_assignment_mismatch",
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


def test_concurrent_identical_apply_is_cooperatively_serialized(tmp_path) -> None:
    path = "src/output.txt"
    project, _artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        barrier = threading.Barrier(3)
        results: list[dict[str, object]] = []

        def apply_concurrently() -> None:
            barrier.wait()
            results.append(_apply(materializer, prepared))

        threads = [threading.Thread(target=apply_concurrently) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)

        assert all(not thread.is_alive() for thread in threads)
        assert sorted(str(result["status"]) for result in results) == [
            "already_identical",
            "applied",
        ]
        assert (project / path).read_text() == "candidate\n"
    finally:
        materializer.close()
        preflight.close()


@pytest.mark.parametrize("tamper", ["order", "path", "length", "success_hash"])
def test_apply_rejects_receipts_that_do_not_match_manifest_files(tmp_path, tamper: str) -> None:
    paths = ["src/first.txt", "src/second.txt"]
    project, artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        request = MaterializationPrepareRequest(
            action="prepare",
            files=[
                _literal_prepare(path, f"candidate {index}\n").files[0]
                for index, path in enumerate(paths)
            ],
        )
        prepared = materializer.execute(request)
        prepared_id = str(prepared["prepared_id"])
        manifest_hash = str(prepared["manifest_sha256"])
        manifest = json.loads((artifacts / prepared_id / "manifest.json").read_text())
        files = [
            {
                "file_index": index,
                "path": item["path"],
                "status": "already_identical",
                "actual_sha256": item["content_sha256"],
            }
            for index, item in enumerate(manifest["files"])
        ]
        if tamper == "order":
            files.reverse()
        elif tamper == "path":
            files[0]["path"] = "src/unrelated.txt"
        elif tamper == "length":
            files.pop()
        else:
            files[0]["actual_sha256"] = "0" * 64
        receipt = {
            "version": 1,
            "prepared_id": prepared_id,
            "manifest_sha256": manifest_hash,
            "status": "already_identical",
            "files": files,
        }
        canonical_receipt = (
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            + b"\n"
        )
        (artifacts / prepared_id / "receipt.json").write_bytes(canonical_receipt)

        result = _apply(materializer, prepared)
        assert result["status"] == "blocked"
        assert result["reason_code"] == "materialization_receipt_invalid"
        assert not any((project / path).exists() for path in paths)
    finally:
        materializer.close()
        preflight.close()


def test_apply_rejects_stale_baseline_and_tampered_candidate(tmp_path) -> None:
    path = "src/output.txt"
    project, artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    try:
        prepared = materializer.execute(_literal_prepare(path, "candidate\n"))
        (project / path).write_text("external change\n")
        conflict = _apply(materializer, prepared)
        assert conflict["status"] == "blocked"
        assert conflict["reason_code"] == "materialization_baseline_conflict"
        (project / path).unlink()

        candidate = artifacts / str(prepared["prepared_id"]) / "candidate-00.bin"
        candidate.chmod(0o600)
        candidate.write_text("tampered\n")
        tampered = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=_string_field(prepared, "prepared_id"),
                expected_manifest_hash=_string_field(prepared, "manifest_sha256"),
                file_index=0,
            )
        )
        assert tampered["status"] == "blocked"
        assert tampered["reason_code"] == "prepared_candidate_hash_mismatch"
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_manifest_version_types_and_actual_artifact_batch_bytes_are_strict(tmp_path) -> None:
    paths = [f"src/output-{index}.txt" for index in range(5)]
    project, artifacts, _state, _provider, preflight, _grant_provider, _config, materializer = (
        _workspace(tmp_path, paths)
    )
    try:
        oversized = MaterializationPrepareRequest(
            action="prepare",
            files=[_literal_file(path, "x" * 131_072) for path in paths],
        )
        blocked_prepare = materializer.execute(oversized)
        assert blocked_prepare["status"] == "blocked"
        assert blocked_prepare["reason_code"] == "candidate_batch_byte_limit_exceeded"
        assert not list(artifacts.iterdir())

        unicode_oversized = MaterializationPrepareRequest(
            action="prepare",
            files=[_literal_file(path, "é" * 131_072) for path in paths[:3]],
        )
        blocked_unicode = materializer.execute(unicode_oversized)
        assert blocked_unicode["status"] == "blocked"
        assert blocked_unicode["reason_code"] == "candidate_batch_byte_limit_exceeded"
        assert not list(artifacts.iterdir())

        prepared = materializer.execute(
            MaterializationPrepareRequest(
                action="prepare",
                files=[_literal_file(path, "x") for path in paths],
            )
        )
        assert prepared["status"] == "prepared"
        prepared_dir = artifacts / str(prepared["prepared_id"])
        manifest_path = prepared_dir / "manifest.json"
        manifest_raw = json.loads(manifest_path.read_text())
        manifest_path.chmod(0o600)
        for version_field in ("version", "policy_version"):
            for invalid in (True, 1.0):
                altered = dict(manifest_raw)
                altered[version_field] = invalid
                with pytest.raises(ValidationError):
                    PreparedMaterializationManifest.model_validate(altered, strict=True)

        expanded = b"z" * 131_072
        for index, item in enumerate(manifest_raw["files"]):
            candidate_path = prepared_dir / f"candidate-{index:02d}.bin"
            candidate_path.chmod(0o600)
            candidate_path.write_bytes(expanded)
            item["content_sha256"] = hashlib.sha256(expanded).hexdigest()
            item["content_bytes"] = len(expanded)
            item["content_chars"] = len(expanded)
        canonical = json.dumps(
            manifest_raw,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        manifest_path.write_bytes(canonical)
        tampered_hash = hashlib.sha256(canonical).hexdigest()
        inspected = materializer.execute(
            MaterializationInspectRequest(
                action="inspect",
                prepared_id=_string_field(prepared, "prepared_id"),
                expected_manifest_hash=tampered_hash,
                file_index=0,
            )
        )
        assert inspected["status"] == "blocked"
        assert inspected["reason_code"] == "candidate_batch_byte_limit_exceeded"
        assert not any((project / path).exists() for path in paths)
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


def test_responses_ordering_is_fake_api_only_and_materializes_source_facts(
    tmp_path, monkeypatch
) -> None:
    path = "src/result.md"
    project, _artifacts, _state, _provider, preflight, grant_provider, config, materializer = (
        _workspace(tmp_path, [path])
    )
    client = SimpleNamespace()
    client.closed = False
    client.calls = []
    client.responses = client

    def parse(**kwargs):
        client.calls.append(kwargs)
        return SimpleNamespace(
            status="completed",
            model="gpt-6-luna",
            error=None,
            incomplete_details=None,
            output_parsed=FactOrderingPlan(
                files=[FactOrderingItem(file_index=0, fact_ids=["second", "first"])]
            ),
            output=[],
        )

    def close():
        client.closed = True

    client.parse = parse
    client.close = close
    factory_calls = []

    def factory(key: str, base_url: str) -> object:
        factory_calls.append((key, base_url))
        return client

    try:
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
        config = OutputMaterializerConfig(
            config.project_root,
            config.artifact_root,
            config.grant_provider,
            config.authorization_provider,
        )
        materializer.close()
        from token_io_decoupling_tools.output_materialization import (
            OutputMaterializationService as Service,
        )

        materializer = Service(
            authorization_provider=config.authorization_provider,
            compliance_service=preflight,
            config=config,
        )
        monkeypatch.setattr(materializer._renderer, "_make_client", factory)
        grant_provider.grant = grant_provider.grant.model_copy(
            update={"allow_responses_ordering": True}
        )
        request = MaterializationPrepareRequest(
            action="prepare",
            outbound_data_permitted=True,
            files=[
                MaterializationFileSpec(
                    path=path,
                    operation="create",
                    baseline=AbsentBaseline(state="absent"),
                    template=FactMarkdownTemplate(
                        kind="fact_markdown",
                        headings=[FactHeading(id="h", title="Facts")],
                        facts=[
                            SourceFact(id="first", heading_id="h", text="first source"),
                            SourceFact(id="second", heading_id="h", text="second source"),
                        ],
                        ordering="responses",
                    ),
                )
            ],
        )
        prepared = materializer.execute(request, expected_binding=_state)
        assert prepared["status"] == "prepared"
        assert factory_calls == [("fake-key", "https://mock.invalid/v1")]
        assert client.closed
        assert client.calls[0]["model"] == "gpt-6-luna"
        assert client.calls[0]["max_output_tokens"] == 4_000
        assert client.calls[0]["tools"] == []
        apply = _apply(materializer, prepared, expected_binding=_state)
        assert apply["status"] == "applied"
        result = (project / path).read_text()
        assert result.index("second source") < result.index("first source")
    finally:
        materializer.close()
        preflight.close()


def test_invalid_responses_result_creates_no_candidate_artifact(tmp_path, monkeypatch) -> None:
    path = "src/result.md"
    project, artifacts, _state, _provider, preflight, grant_provider, _config, materializer = (
        _workspace(tmp_path, [path])
    )
    refusal = SimpleNamespace(
        status="completed",
        model="gpt-6-luna",
        error=None,
        incomplete_details=None,
        output_parsed=None,
        output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
    )

    class _Client:
        responses = None

        def __init__(self):
            self.responses = self

        def parse(self, **_kwargs):
            return refusal

        def close(self):
            pass

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.invalid/v1")
    monkeypatch.setattr(materializer._renderer, "_make_client", lambda *_args: _Client())
    request = MaterializationPrepareRequest(
        action="prepare",
        outbound_data_permitted=True,
        files=[
            MaterializationFileSpec(
                path=path,
                operation="create",
                baseline=AbsentBaseline(state="absent"),
                template=FactMarkdownTemplate(
                    kind="fact_markdown",
                    headings=[FactHeading(id="h", title="Facts")],
                    facts=[SourceFact(id="f", heading_id="h", text="source fact")],
                    ordering="responses",
                ),
            )
        ],
    )
    try:
        result = materializer.execute(request)
        assert result["status"] == "blocked"
        assert not list(artifacts.iterdir())
        assert not (project / path).exists()
    finally:
        materializer.close()
        preflight.close()


def test_worker_stdio_exposes_bounded_action_schema_and_applies_only_with_factory(
    tmp_path,
) -> None:
    path = "src/output.txt"
    project, artifacts, state, provider, preflight, grant_provider, config, materializer = (
        _workspace(tmp_path, [path])
    )
    materializer.close()
    server = create_tools_server(
        provider,
        compliance_service=preflight,
        output_materializer_config=config,
    )

    async def run() -> None:
        async with Client(server, mode="auto") as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            assert "materialize_decoupled_output" in tools
            description = tools["materialize_decoupled_output"].description or ""
            assert "1–16 files" in description
            assert "fresh whole-batch 185 result" in description
            assert "Same-service cooperative locking" in description
            request_schema = tools["materialize_decoupled_output"].input_schema["properties"][
                "payload"
            ]["properties"]["request"]
            assert request_schema["discriminator"]["propertyName"] == "action"
            variants = request_schema["oneOf"]
            assert {variant["properties"]["action"]["const"] for variant in variants} == {
                "prepare",
                "inspect",
                "apply",
            }
            prepare_schema = next(
                variant
                for variant in variants
                if variant["properties"]["action"]["const"] == "prepare"
            )
            file_schema = prepare_schema["properties"]["files"]
            assert file_schema["minItems"] == 1
            assert file_schema["maxItems"] == 16
            template_schema = file_schema["items"]["properties"]["template"]
            assert {
                variant["properties"]["kind"]["const"] for variant in template_schema["oneOf"]
            } == {"literal_text", "json_document", "fact_markdown"}
            prepared_result = await client.call_tool(
                "materialize_decoupled_output",
                {
                    "payload": {
                        "request": {
                            "action": "prepare",
                            "files": [
                                {
                                    "path": path,
                                    "operation": "create",
                                    "baseline": {"state": "absent"},
                                    "template": {
                                        "kind": "literal_text",
                                        "text": "stdio result\n",
                                    },
                                }
                            ],
                        }
                    }
                },
            )
            assert not prepared_result.is_error
            prepared = json.loads(_result_text(prepared_result))
            apply_result = await client.call_tool(
                "materialize_decoupled_output",
                {
                    "payload": {
                        "request": {
                            "action": "apply",
                            "prepared_id": prepared["prepared_id"],
                            "expected_manifest_hash": prepared["manifest_sha256"],
                        }
                    }
                },
            )
            assert not apply_result.is_error
            applied = json.loads(_result_text(apply_result))
            assert applied["status"] == "applied"

    try:
        asyncio.run(run())
        assert (project / path).read_text() == "stdio result\n"
        assert any(artifacts.iterdir())
    finally:
        close = getattr(server, "_output_materializer", None)
        if close is not None:
            close.close()
        preflight.close()
