"""Canonical definitions for all independent tools; registration uses one template."""

from __future__ import annotations

from typing import Annotated, Any

from dev_workflow_standards_tools.services import ai_workflow, validation, workflows
from dev_workflow_standards_tools.services.create_branch import create_repository_branch
from dev_workflow_standards_tools.tools import ai_workflow as ai_tools
from dev_workflow_standards_tools.tools import codex_session_facts
from dev_workflow_standards_tools.tools._descriptions import PARAMETER_DESCRIPTIONS
from mcp.types import ToolAnnotations
from pydantic import Field

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.materialization_models import MaterializeDecoupledOutputPayload
from token_io_decoupling_tools.capabilities import capability_report
from token_io_decoupling_tools.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_tools.output_materialization import OutputMaterializationService
from token_io_decoupling_tools.payloads import _COMPLIANCE_PREFLIGHT
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_tools.task_plan_core import TaskPlanService
from token_io_decoupling_tools.task_plan_payloads import (
    TaskPlanArchivePayload,
    TaskPlanCompletePayload,
    TaskPlanUpdatePayload,
)
from token_io_decoupling_transport.tool import ToolDefinition, ToolRegistrar

MemoryPath = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=4096,
        description=(
            "启动目录所绑定项目的 .serena/memories 下的相对名称，可带 mem: 前缀和 .md 后缀。"
        ),
    ),
]
TailLines = Annotated[
    int,
    Field(
        strict=True,
        ge=0,
        le=10000,
        description="最后 N 个逻辑行；零表示仅返回行数元数据，内容为空。",
    ),
]
ChangedContent = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=64000,
        description="在尾部按字面查找的非空文本；不规范化，也不使用正则表达式。",
    ),
]

_LOCAL_READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
_REMOTE_READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)
_AI_READ = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=False, open_world_hint=True
)
_MEMORY_READ = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
_LOCAL_WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
)
_LOCAL_DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False
)
_LOCAL_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
_REMOTE_WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True
)
_REMOTE_DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True
)
_REMOTE_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=True
)

# Import business callbacks, never the upstream server or its registration functions.
# The pinned upstream parameter descriptions retain the existing wire contract.
_UPSTREAM_TOOLS = (
    ToolDefinition(
        name="check_branch_names",
        callback=ai_workflow.check_branch_names,
        annotations=_AI_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["check_branch_names"],
    ),
    ToolDefinition(
        name="check_commit_message",
        callback=ai_workflow.check_commit_message,
        annotations=_AI_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["check_commit_message"],
    ),
    ToolDefinition(
        name="check_staged_changes",
        callback=validation.check_staged_changes,
        annotations=_LOCAL_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["check_staged_changes"],
    ),
    ToolDefinition(
        name="stage_repository_paths",
        callback=workflows.stage_repository_paths,
        annotations=_LOCAL_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["stage_repository_paths"],
    ),
    ToolDefinition(
        name="commit_repository_changes",
        callback=workflows.commit_repository_changes,
        annotations=_LOCAL_DESTRUCTIVE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["commit_repository_changes"],
    ),
    ToolDefinition(
        name="list_repository_worktrees",
        callback=workflows.list_repository_worktrees,
        annotations=_LOCAL_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["list_repository_worktrees"],
    ),
    ToolDefinition(
        name="switch_repository_branch",
        callback=workflows.switch_repository_branch,
        annotations=_LOCAL_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["switch_repository_branch"],
    ),
    ToolDefinition(
        name="create_repository_branch",
        callback=create_repository_branch,
        annotations=_LOCAL_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["create_repository_branch"],
    ),
    ToolDefinition(
        name="pull_origin_branch_fast_forward",
        callback=workflows.pull_origin_branch_fast_forward,
        annotations=_REMOTE_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["pull_origin_branch_fast_forward"],
    ),
    ToolDefinition(
        name="fetch_upstream_branch",
        callback=workflows.fetch_upstream_branch,
        annotations=_REMOTE_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["fetch_upstream_branch"],
    ),
    ToolDefinition(
        name="merge_upstream_branch_fast_forward",
        callback=workflows.merge_upstream_branch_fast_forward,
        annotations=_LOCAL_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["merge_upstream_branch_fast_forward"],
    ),
    ToolDefinition(
        name="rebase_repository_branch",
        callback=workflows.rebase_repository_branch,
        annotations=_LOCAL_DESTRUCTIVE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["rebase_repository_branch"],
    ),
    ToolDefinition(
        name="remove_repository_worktree",
        callback=workflows.remove_repository_worktree,
        annotations=_LOCAL_DESTRUCTIVE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["remove_repository_worktree"],
    ),
    ToolDefinition(
        name="create_repository_worktree",
        callback=workflows.create_repository_worktree,
        annotations=_LOCAL_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["create_repository_worktree"],
    ),
    ToolDefinition(
        name="capture_untracked_file_manifest",
        callback=workflows.capture_untracked_file_manifest,
        annotations=_LOCAL_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["capture_untracked_file_manifest"],
    ),
    ToolDefinition(
        name="copy_untracked_files_to_worktree",
        callback=workflows.copy_untracked_files_to_worktree,
        annotations=_LOCAL_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["copy_untracked_files_to_worktree"],
    ),
    ToolDefinition(
        name="configure_project_hooks_path",
        callback=workflows.configure_project_hooks_path,
        annotations=_LOCAL_IDEMPOTENT,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["configure_project_hooks_path"],
    ),
    ToolDefinition(
        name="audit_issue_pr_policy",
        callback=ai_workflow.audit_issue_pr_policy,
        annotations=_AI_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["audit_issue_pr_policy"],
    ),
    ToolDefinition(
        name="cleanup_merged_pr_local_branch",
        callback=validation.cleanup_merged_pr_local_branch,
        annotations=_REMOTE_DESTRUCTIVE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["cleanup_merged_pr_local_branch"],
    ),
    ToolDefinition(
        name="audit_repository_state",
        callback=workflows.audit_repository_state,
        annotations=_REMOTE_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["audit_repository_state"],
    ),
    ToolDefinition(
        name="list_github_issue_labels",
        callback=workflows.list_github_issue_labels,
        annotations=_REMOTE_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["list_github_issue_labels"],
    ),
    ToolDefinition(
        name="create_github_issue",
        callback=workflows.create_github_issue,
        annotations=_REMOTE_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["create_github_issue"],
    ),
    ToolDefinition(
        name="push_issue_branch_to_origin",
        callback=workflows.push_issue_branch_to_origin,
        annotations=_REMOTE_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["push_issue_branch_to_origin"],
    ),
    ToolDefinition(
        name="create_github_pull_request",
        callback=workflows.create_github_pull_request,
        annotations=_REMOTE_WRITE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["create_github_pull_request"],
    ),
    ToolDefinition(
        name="merge_github_pull_request",
        callback=workflows.merge_github_pull_request,
        annotations=_REMOTE_DESTRUCTIVE,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["merge_github_pull_request"],
    ),
    ToolDefinition(
        name="push_fork_main_fast_forward",
        callback=workflows.push_fork_main_fast_forward,
        annotations=_REMOTE_IDEMPOTENT,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["push_fork_main_fast_forward"],
    ),
    ToolDefinition(
        name="get_codex_session_summary_guidance",
        callback=codex_session_facts.get_codex_session_summary_guidance,
        annotations=_MEMORY_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["get_codex_session_summary_guidance"],
    ),
    ToolDefinition(
        name="order_codex_session_sources",
        callback=codex_session_facts.order_codex_session_sources,
        annotations=_MEMORY_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["order_codex_session_sources"],
    ),
    ToolDefinition(
        name="prepare_codex_session_memory",
        callback=codex_session_facts.prepare_codex_session_memory,
        annotations=_MEMORY_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["prepare_codex_session_memory"],
    ),
    ToolDefinition(
        name="decide_skill_workflow",
        callback=ai_tools.decide_skill_workflow,
        annotations=_AI_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["decide_skill_workflow"],
    ),
    ToolDefinition(
        name="decide_codex_session_action",
        callback=ai_tools.decide_codex_session_action,
        annotations=_AI_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["decide_codex_session_action"],
    ),
    ToolDefinition(
        name="generate_skill_content",
        callback=ai_tools.generate_skill_content,
        annotations=_AI_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["generate_skill_content"],
    ),
    ToolDefinition(
        name="check_api_input",
        callback=ai_tools.check_api_input,
        annotations=_AI_READ,
        structured_output=None,
        parameter_descriptions=PARAMETER_DESCRIPTIONS["check_api_input"],
    ),
)


def register_tools(
    registrar: ToolRegistrar,
    *,
    provider: BindingProvider,
    task_plan_service: TaskPlanService,
    serena_memory_service: SerenaMemoryReadService,
    compliance_service: CompliancePreflightService | None,
    output_materializer: OutputMaterializationService | None,
    output_materialization_details: dict[str, str],
) -> None:
    """使用同一注册模板公开独立操作；注册关系不要求 workflow 调用顺序。"""

    def tools_capabilities() -> dict[str, Any]:
        return capability_report(
            provider,
            task_plan_service=task_plan_service,
            serena_memory_service=serena_memory_service,
            compliance_service=compliance_service,
            output_materialization=output_materialization_details,
        )

    def tail_read(memory_path: MemoryPath, tail_lines: TailLines) -> dict[str, Any]:
        return serena_memory_service.tail_read(memory_path, tail_lines)

    def write_check(
        memory_path: MemoryPath, changed_content: ChangedContent, tail_lines: TailLines
    ) -> dict[str, Any]:
        return serena_memory_service.write_check(memory_path, changed_content, tail_lines)

    def materialize_output(payload: MaterializeDecoupledOutputPayload) -> dict[str, Any]:
        if output_materializer is None:
            return {
                "status": "unavailable",
                "reason_code": "trusted_authorization_context_unavailable",
            }
        return output_materializer.execute(
            payload.request, expected_binding=provider.current_binding()
        )

    registrar.register_all(
        (
            ToolDefinition(
                name="tools_capabilities",
                callback=tools_capabilities,
                bounded_errors=True,
            ),
            ToolDefinition(
                name="serena_memory_tail_read",
                callback=tail_read,
                annotations=_MEMORY_READ,
            ),
            ToolDefinition(
                name="serena_memory_write_check",
                callback=write_check,
                annotations=_MEMORY_READ,
            ),
            ToolDefinition(
                name="task_plan_update",
                callback=lambda payload: task_plan_service.update(
                    payload.request.model_dump(mode="json")
                ),
                payload_type=TaskPlanUpdatePayload,
            ),
            ToolDefinition(
                name="task_plan_complete",
                callback=lambda payload: task_plan_service.complete(
                    payload.request.model_dump(mode="json")
                ),
                payload_type=TaskPlanCompletePayload,
            ),
            ToolDefinition(
                name="task_plan_archive",
                callback=lambda payload: task_plan_service.archive(
                    payload.request.model_dump(mode="json")
                ),
                payload_type=TaskPlanArchivePayload,
            ),
            ToolDefinition(
                name="validate_decoupling_compliance",
                callback=lambda payload: validate_decoupling_compliance(
                    compliance_service, payload.request
                ),
                payload_type=_COMPLIANCE_PREFLIGHT,
            ),
            ToolDefinition(
                name="materialize_decoupled_output",
                callback=materialize_output,
                payload_type=MaterializeDecoupledOutputPayload,
                role="worker",
                codex_guard=True,
            ),
            *_UPSTREAM_TOOLS,
        )
    )
