"""Fixed tool inventory exposed by the single local tools MCP server."""

TOOLS_SERVER_NAME = "token-io-decoupling-tools"

UTILITY_TOOLS = frozenset(
    {
        "serena_memory_tail_read",
        "serena_memory_write_check",
        "rules_get_context",
        "validate_decoupling_compliance",
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
        "decide_skill_workflow",
        "generate_skill_content",
        "check_api_input",
    }
)

TOOLS_SERVER_TOOLS = UTILITY_TOOLS | WORKER_TOOLS | DEV_WORKFLOW_TOOLS

if len(TOOLS_SERVER_TOOLS) != 34:
    raise RuntimeError("fixed MCP server tool inventories do not match their contract")
