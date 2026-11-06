"""Operation descriptions without workflow gates or cross-tool calling order."""

from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS

SERVER_DESCRIPTION = "Independent local Codex MCP development, task-plan and Memory tools."
SERVER_INSTRUCTIONS = (
    "Select any tool directly from its input schema and operation description. "
    "No workflow node, route, mode, plan, prior tool invocation or follow-up tool is required. "
    "Each operation validates its own current inputs, resource state and authorization. "
    "User and repository instructions and host permissions apply. API tools use their configured "
    "process environment; local tools do not require API configuration. "
    "On an uncertain write, inspect current resource state rather than blindly repeating it."
)

TOOL_DESCRIPTIONS = {
    "tools_capabilities": (
        "Report this server's configured task-plan, Memory, preflight and materialization "
        "dependencies. No arguments, mutation or API request. This diagnostic is optional."
    ),
    "task_plan_update": (
        "Create or append bounded records to a task plan using an explicitly configured "
        "backend. The request supplies project_root, plan_id, expected_revision (null for "
        "creation), request_id and records. Current revisions protect existing content; "
        "identical request IDs support replay detection. Returns status, reason, revisions "
        "and readback evidence."
    ),
    "task_plan_complete": (
        "Record completion of an existing task plan in the configured backend. Supply its "
        "current revision, request ID, criterion_evidence and result/limitation records. "
        "Validates the stored criteria, verification outcomes and unresolved blockers as "
        "part of this operation. Returns a completion or conflict receipt; it does not "
        "certify project acceptance."
    ),
    "task_plan_archive": (
        "Archive a completed task plan at its supplied current revision in the configured "
        "store. Checks the actual stored resource and verifies preservation; returns an "
        "archive receipt. Existing plan state may come from any compatible writer."
    ),
    "serena_memory_tail_read": (
        "Read a local Memory file tail. Direct arguments, no payload envelope: memory_path "
        "is relative to the startup project's .serena/memories, with optional mem: and .md; "
        "tail_lines is 0..10000 (zero returns metadata). UTF-8, at most 64000 characters; "
        "symlinks and paths outside the Memory root are rejected. No files, directories or "
        "API requests are created."
    ),
    "serena_memory_write_check": (
        "Read-only literal containment query on a Memory tail. Direct arguments, no payload "
        "envelope: memory_path, nonempty changed_content (at most 64000 characters), and "
        "tail_lines (0..10000). Returns success/reason and window evidence. A match proves "
        "current text presence, not who wrote it or when. Uses the startup project's "
        ".serena/memories."
    ),
    "validate_decoupling_compliance": (
        "Validate a bounded candidate overlay with an explicitly configured read-only "
        "preflight service. Payload request contains generic_project policy_scope and 1..64 "
        "create/replace/delete candidates with absent or SHA-256 baselines. No candidate "
        "script is executed and no write is performed. Missing disk evidence is unknown, "
        "never a passing check."
    ),
    "materialize_decoupled_output": (
        "Prepare, inspect or apply 1–16 files of bounded code_configuration output. The "
        "request identifies file specifications or an existing prepared artifact/receipt; "
        "it cannot supply caller identity, assignment or permission. A trusted per-call "
        "Worker binding and assignment source and independent operator grant authorize the "
        "operation. Pinned roots, allowed paths, current baselines, fresh whole-batch "
        "preflight and write-time authorization protect writes. Same-service cooperative "
        "locking coordinates writes. An existing artifact can be supplied directly; no "
        "workflow checkpoint is used. Without trusted configuration the operation is "
        "unavailable."
    ),
    "check_branch_names": (
        "Check supplied branch names, or a repository's current branch, against the "
        "configured naming policy. Local validation and an API judgment have separate "
        "result fields. No Git write."
    ),
    "check_commit_message": (
        "Check a supplied commit message against the configured policy. Local validation "
        "and an API judgment have separate result fields. No commit is created."
    ),
    "check_staged_changes": (
        "Inspect the repository's actual staged diff for whitespace errors. Purely local, "
        "read-only; no API configuration is needed."
    ),
    "stage_repository_paths": (
        "Stage an exact set of repository-relative paths. Validates current index state and "
        "reads back the staged paths. Writes the local index."
    ),
    "commit_repository_changes": (
        "Commit the actual staged path set using the supplied message and expected_paths. "
        "Validates current state and message policy in this operation; runs normal Git "
        "hooks. Writes Git history."
    ),
    "list_repository_worktrees": (
        "List worktrees for an absolute repository root. Local read-only query without an "
        "API request."
    ),
    "switch_repository_branch": (
        "Switch to an existing local branch after validating the actual checkout state. "
        "Writes the checkout; no network request."
    ),
    "create_repository_branch": (
        "Create a local branch at the current commit and point HEAD to it without changing "
        "worktree content or the index. Optional expected_head_oid protects against a "
        "changed commit. No network or model call."
    ),
    "pull_origin_branch_fast_forward": (
        "Fast-forward the current local branch from origin when the actual checkout and "
        "remote state permit it. Uses the network and writes Git state; never forces an "
        "update."
    ),
    "fetch_upstream_branch": (
        "Fetch the specified upstream branch into local remote-tracking state. Uses the "
        "network and writes Git metadata."
    ),
    "merge_upstream_branch_fast_forward": (
        "Fast-forward the current branch to an existing upstream tracking ref. Uses current "
        "local refs; does not fetch or force an update."
    ),
    "rebase_repository_branch": (
        "Rebase the specified branch onto the supplied base after validating current "
        "repository and publication state. Rewrites local history; conflicts remain "
        "available for inspection."
    ),
    "remove_repository_worktree": (
        "Remove the identified clean worktree after checking its repository and branch "
        "identity. Deletes that worktree directory."
    ),
    "create_repository_worktree": (
        "Create a local branch and a new worktree from an existing local base at an "
        "explicit target path. Validates paths and current refs; does not synchronize "
        "remotes."
    ),
    "capture_untracked_file_manifest": (
        "Read a bounded manifest of current untracked files with paths, sizes and SHA-256 "
        "values. Does not copy or stage files."
    ),
    "copy_untracked_files_to_worktree": (
        "Copy the supplied untracked-file manifest to an explicit worktree, validating "
        "current source hashes and target paths. Reports confirmed copies and partial "
        "failure; does not stage files."
    ),
    "configure_project_hooks_path": (
        "Set the repository hooks path to the supplied directory, validating the target and "
        "current configuration. Writes local Git configuration."
    ),
    "audit_issue_pr_policy": (
        "Read and assess supplied GitHub Issue/PR facts against the configured policy. "
        "Returns local findings and API judgment; does not modify GitHub resources."
    ),
    "cleanup_merged_pr_local_branch": (
        "Verify a merged PR and the supplied branch/OID, then clean up the matching local "
        "branch using current repository state. May synchronize the base; does not merge a "
        "PR."
    ),
    "audit_repository_state": (
        "Read the absolute repository root, current branch, status and remote names, and "
        "query GitHub repository identity. Local ok and github_error are independent; no "
        "write or model call."
    ),
    "list_github_issue_labels": (
        "Read up to 100 labels for the specified GitHub repository. Network read only; no "
        "model call or label creation."
    ),
    "create_github_issue": (
        "Create and read back a GitHub Issue with the supplied title, Markdown body and "
        "existing labels. Assigns the authenticated account. Reports creation and "
        "verification separately."
    ),
    "push_issue_branch_to_origin": (
        "Push the current issue branch to origin after validating the supplied Issue and "
        "current branch facts within this call. Uses the network and never force-pushes."
    ),
    "create_github_pull_request": (
        "Create and read back a PR for explicit head/base refs and the supplied Issue "
        "relationship. Validates actual resource state; reports creation and readback "
        "separately."
    ),
    "merge_github_pull_request": (
        "Merge the identified PR when actual GitHub checks and the configured merge policy "
        "permit it. Requires authorization for this remote write."
    ),
    "push_fork_main_fast_forward": (
        "Fast-forward a fork's origin main using the actual clean checkout and existing "
        "upstream/main relationship. Network write without force."
    ),
    "get_codex_session_summary_guidance": (
        "Return guidance for summarizing supplied session facts. Does not read chats or "
        "Memory, invoke a model or write files."
    ),
    "order_codex_session_sources": (
        "Deduplicate and order supplied session metadata by verified creation time. No "
        "chat, Memory, model or filesystem access."
    ),
    "prepare_codex_session_memory": (
        "Validate supplied session facts and prepare a Memory payload. Does not read chats "
        "or write Memory; returned data grants no write permission."
    ),
    "decide_skill_workflow": (
        "Return optional routing advice from supplied classified facts using the configured "
        "API. Does not select the caller's execution mode or invoke any other tool."
    ),
    "decide_codex_session_action": (
        "Return optional query/storage advice about supplied session facts using the "
        "configured API. Does not read or persist chats or Memory."
    ),
    "generate_skill_content": (
        "Generate an Issue, PR, commit message, plan, handoff or session-summary candidate "
        "from supplied bounded evidence. Uses the configured API; Issue/PR candidates "
        "include a quality review. Returns draft and adoption diagnostics; publishes "
        "nothing."
    ),
    "check_api_input": (
        "Review a complete proposed outbound API purpose and content using configured local "
        "and API checks. Returns passed/status and diagnostics. Does not perform the "
        "proposed business action or authorize publication."
    ),
}

_API_TOOLS = {
    "check_branch_names",
    "check_commit_message",
    "audit_issue_pr_policy",
    "decide_skill_workflow",
    "decide_codex_session_action",
    "generate_skill_content",
    "check_api_input",
}


def tool_description(name: str) -> str:
    description = TOOL_DESCRIPTIONS[name]
    if name in _API_TOOLS:
        description += (
            " API calls use nonblank OPENAI_API_KEY and OPENAI_BASE_URL from the process "
            "environment, fixed gpt-6-luna, and the outbound-input review boundary. "
            "Credentials and endpoints are not tool arguments."
        )
    return description


if set(TOOL_DESCRIPTIONS) != TOOLS_SERVER_TOOLS:
    raise RuntimeError("standalone tool descriptions differ from the public inventory")
