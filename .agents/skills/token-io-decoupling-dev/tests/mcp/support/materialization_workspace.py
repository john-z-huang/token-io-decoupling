"""物化测试专用的临时工作区、授权协作者及请求准备。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, cast

from token_io_decoupling_core.materialization_models import (
    AbsentBaseline,
    DirectoryIdentity,
    LiteralTextTemplate,
    MaterializationApplyRequest,
    MaterializationFileSpec,
    MaterializationOperation,
    MaterializationPrepareRequest,
    OutputMaterializationGrant,
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
from token_io_decoupling_tools.output_materialization import (
    MaterializationAssignment,
    MaterializationAuthorizationContext,
    OutputMaterializationService,
    OutputMaterializerConfig,
    materialization_assignment_hash,
)


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
        output_class=cast(Literal["code_configuration"], output_class.value),
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
        policy_version=2,
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
