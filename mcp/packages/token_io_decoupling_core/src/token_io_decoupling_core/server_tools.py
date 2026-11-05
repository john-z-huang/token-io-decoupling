"""Fixed tool inventories exposed by the two local Codex MCP servers."""

WORKFLOW_SERVER_NAME = "token-io-decoupling-workflow"
TOOLS_SERVER_NAME = "token-io-decoupling-tools"

WORKFLOW_TOOLS = frozenset(
    {
        "workflow_capabilities",
        "task_plan_update",
        "task_plan_complete",
        "task_plan_archive",
        "serena_memory_tail_read",
        "serena_memory_write_check",
        "rules_get_context",
        "validate_decoupling_compliance",
        "decide_decoupling_workflow",
        "workflow_select_child_effort",
        "workflow_generate_decision_context",
        "workflow_select_child_role",
        "workflow_select_executor",
        "workflow_select_child",
        "workflow_assess_output_tokens",
        "workflow_evaluate",
        "evaluate_control_checkpoint",
    }
)

WORKER_TOOLS = frozenset(
    {
        "materialize_decoupled_output",
    }
)

DEV_WORKFLOW_TOOLS = frozenset(
    {
        "check_branch_names",
        "check_commit_message",
        "check_staged_changes",
        "stage_repository_paths",
        "commit_repository_changes",
        "list_repository_worktrees",
        "switch_repository_branch",
        "create_repository_branch",
        "pull_origin_branch_fast_forward",
        "fetch_upstream_branch",
        "merge_upstream_branch_fast_forward",
        "rebase_repository_branch",
        "remove_repository_worktree",
        "create_repository_worktree",
        "capture_untracked_file_manifest",
        "copy_untracked_files_to_worktree",
        "configure_project_hooks_path",
        "audit_issue_pr_policy",
        "cleanup_merged_pr_local_branch",
        "audit_repository_state",
        "list_github_issue_labels",
        "create_github_issue",
        "push_issue_branch_to_origin",
        "create_github_pull_request",
        "merge_github_pull_request",
        "push_fork_main_fast_forward",
        "get_codex_session_summary_guidance",
        "order_codex_session_sources",
        "prepare_codex_session_memory",
        "decide_skill_workflow",
        "decide_codex_session_action",
        "generate_skill_content",
        "check_api_input",
    }
)

TOOLS_SERVER_TOOLS = WORKER_TOOLS | DEV_WORKFLOW_TOOLS

if len(WORKFLOW_TOOLS) != 17 or len(TOOLS_SERVER_TOOLS) != 34:
    raise RuntimeError("fixed MCP server tool inventories do not match their contract")
