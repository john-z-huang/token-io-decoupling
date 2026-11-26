"""Explicit, complete tool definitions for the single tools server."""

from __future__ import annotations

from typing import Any

from dev_workflow_standards_tools.services import ai_workflow, validation, workflows
from dev_workflow_standards_tools.services.create_branch import create_repository_branch
from dev_workflow_standards_tools.tools import ai_workflow as ai_callbacks
from dev_workflow_standards_tools.tools._descriptions import (
    PARAMETER_DESCRIPTIONS,
    TOOL_DESCRIPTIONS,
)
from mcp.types import ToolAnnotations
from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.materialization_models import MaterializeDecoupledOutputPayload
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_tools.compliance_preflight import CompliancePreflightService
from token_io_decoupling_tools.output_materialization import OutputMaterializationService
from token_io_decoupling_tools.payloads import _COMPLIANCE_PREFLIGHT
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_tools.serena_memory_tools import create_memory_callbacks
from token_io_decoupling_tools.tools import create_utility_callbacks
from token_io_decoupling_transport.payloads import _RULE_CONTEXT
from token_io_decoupling_transport.registration import ToolDefinition, ToolRegistrar
from token_io_decoupling_transport.tool_metadata import tool_description


def tool_definitions(
    *,
    compliance_service: CompliancePreflightService | None,
    rules: RuleLoader,
    provider: BindingProvider,
    serena_memory_service: SerenaMemoryReadService | None = None,
    output_materializer: OutputMaterializationService | None = None,
) -> tuple[ToolDefinition, ...]:
    """Bind callbacks per server, without registering or discovering tools implicitly."""
    utility = create_utility_callbacks(
        compliance_service=compliance_service,
        rules=rules,
        provider=provider,
        output_materializer=output_materializer,
    )
    memory = create_memory_callbacks(serena_memory_service or SerenaMemoryReadService())
    read_only = ToolAnnotations(read_only_hint=True, open_world_hint=False)
    remote_read = ToolAnnotations(read_only_hint=True, open_world_hint=True)
    ai_read = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
    local_write = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    )
    destructive = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    )
    remote_write = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
    remote_destructive = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=True,
    )
    memory_read = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )

    def upstream(callback: Any, annotations: ToolAnnotations) -> ToolDefinition:
        name = callback.__name__
        return ToolDefinition(
            name,
            callback,
            TOOL_DESCRIPTIONS[name],
            annotations,
            parameter_descriptions=PARAMETER_DESCRIPTIONS[name],
        )

    def payload(
        name: str, model: Any, *, enhanced: bool = False, role: str | None = None
    ) -> ToolDefinition:
        return ToolDefinition(
            name,
            utility[name],
            tool_description(name),
            payload_type=model,
            enhanced=enhanced,
            role=role,
            structured_output=False,
        )

    return (
        upstream(ai_workflow.check_branch_names, ai_read),
        upstream(ai_workflow.check_commit_message, ai_read),
        upstream(validation.check_staged_changes, read_only),
        upstream(workflows.stage_repository_paths, local_write),
        upstream(workflows.commit_repository_changes, destructive),
        upstream(workflows.list_repository_worktrees, read_only),
        upstream(workflows.switch_repository_branch, local_write),
        upstream(create_repository_branch, local_write),
        upstream(workflows.pull_origin_branch_fast_forward, remote_write),
        upstream(workflows.fetch_upstream_branch, remote_write),
        upstream(workflows.merge_upstream_branch_fast_forward, local_write),
        upstream(workflows.rebase_repository_branch, destructive),
        upstream(workflows.remove_repository_worktree, destructive),
        upstream(workflows.create_repository_worktree, local_write),
        upstream(workflows.capture_untracked_file_manifest, read_only),
        upstream(workflows.copy_untracked_files_to_worktree, local_write),
        upstream(
            workflows.configure_project_hooks_path,
            ToolAnnotations(
                read_only_hint=False,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=False,
            ),
        ),
        upstream(ai_workflow.audit_issue_pr_policy, ai_read),
        upstream(validation.cleanup_merged_pr_local_branch, remote_destructive),
        upstream(workflows.audit_repository_state, remote_read),
        upstream(workflows.list_github_issue_labels, remote_read),
        upstream(workflows.create_github_issue, remote_write),
        upstream(workflows.push_issue_branch_to_origin, remote_write),
        upstream(workflows.create_github_pull_request, remote_write),
        upstream(workflows.merge_github_pull_request, remote_destructive),
        upstream(
            workflows.push_fork_main_fast_forward,
            ToolAnnotations(
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=True,
                open_world_hint=True,
            ),
        ),
        upstream(ai_callbacks.decide_skill_workflow, ai_read),
        upstream(ai_callbacks.generate_skill_content, ai_read),
        upstream(ai_callbacks.check_api_input, ai_read),
        payload("rules_get_context", _RULE_CONTEXT),
        payload("validate_decoupling_compliance", _COMPLIANCE_PREFLIGHT),
        payload(
            "materialize_decoupled_output",
            MaterializeDecoupledOutputPayload,
            enhanced=True,
            role="worker",
        ),
        ToolDefinition(
            "serena_memory_tail_read",
            memory["serena_memory_tail_read"],
            tool_description("serena_memory_tail_read"),
            memory_read,
            structured_output=False,
        ),
        ToolDefinition(
            "serena_memory_write_check",
            memory["serena_memory_write_check"],
            tool_description("serena_memory_write_check"),
            memory_read,
            structured_output=False,
        ),
    )


def register_tools(registrar: ToolRegistrar, **services: Any) -> None:
    definitions = tool_definitions(**services)
    registrar.validate_definitions(definitions)
    for definition in definitions:
        registrar.register(definition)
