# Task plan lifecycle tools

[English](TASK_PLAN_TOOLS.md) | [简体中文](TASK_PLAN_TOOLS_zh_cn.md)

This document owns configuration and use of the three deterministic task-plan MCP tools. The [task-plan lifecycle owner](../references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md) remains authoritative for workflow semantics; this page describes the implementation boundary, not task authorization.

## Configuration and discovery

`task_plan_update`, `task_plan_complete`, and `task_plan_archive` belong to the `workflow` profile and the default public inventory. They are Native operations: an Enhanced database or verified Root binding is not their storage mechanism. Existing host permissions and task authorization remain required.

The backend must be explicitly configured with the actual initialized Serena `MemoryManager` and its authorized project root. `create_server(task_plan_service=...)` supports embedding. The components are:

```python
from token_io_decoupling.server import create_server
from token_io_decoupling_workflow.task_plan_core import SerenaMemoryStore, TaskPlanService


def make_server(project_root, memory_manager):
    # Both arguments come from the host's already authorized Serena project.
    store = SerenaMemoryStore(memory_manager, project_root, storage_scope="global")
    return create_server(profile="workflow", task_plan_service=TaskPlanService(store))
```

For an operator-owned launcher integration, `--task-plan-factory module:callable` loads a zero-argument callable returning a configured `TaskPlanService`. For example:

```sh
token-io-decoupling start-mcp-server --profile workflow --task-plan-factory trusted_adapter:make_service
```

`trusted_adapter` is an operator-provided, reviewed module, not a bundled adapter or a tool argument. Its environment must already contain the compatible Serena dependency and authorized project object. The tool package does not install Serena, load/migrate its configuration, create a project, guess a `.serena` directory, or open another Memory store. Do not execute an invented factory to obtain availability. An unconfigured service returns `unavailable` without inspecting memory paths; invalid explicit configuration fails rather than silently falling back.

## Repository storage scope

The host selects `storage_scope="global"` for shared global plans, as in the embedding example. The constructor's compatibility default remains `"project"`; requests cannot select a storage scope, repository ID, Memory root, or arbitrary namespace. Global mode uses the actual manager's existing canonical global Memory root. Project mode uses its existing project Memory root. No mode initializes or redirects Serena configuration.

| Scope | Active logical Memory name | Corresponding physical path |
| --- | --- | --- |
| `global` | `global/token-io-decoupling/repos/<repository-id>/plans/PLAN-<plan_id>` | `<actual-global-memory-root>/token-io-decoupling/repos/<repository-id>/plans/PLAN-<plan_id>.md` |
| `project` | `plans/PLAN-<plan_id>` | `<actual-project-memory-root>/plans/PLAN-<plan_id>.md` |

For archive names/paths, replace only `plans` with `archive-plans` within the same repository scope. Existing native Serena list/read operations can use the returned `memory_name`; filter global listings to `global/token-io-decoupling/repos/<repository-id>/plans` or its archive topic. The lifecycle tools add no unfiltered list/read endpoint. A raw global listing is not a repository ACL.

The global repository ID is `git-v1-` plus SHA-256 of `b"token-io-decoupling:git-common-dir:v1\0" + os.fsencode(str(canonical_git_common_dir))`. The service verifies the bound absolute checkout root and canonical Git common directory through bounded local Git queries. Main and linked worktrees share that directory, so separately configured services share the same plan files, lock, history, revisions and replay identity. Independent clones and same-named repositories have different IDs. Branch, remote URL, commit and checkout basename do not determine the ID. The ID is local: moving the Git common directory changes it and requires explicit reconciliation of the previous mapping. Reusing the same common-directory path reuses the key, so a newly created repository there requires an ownership/history review before use.

`project_root` in each request must still exactly match that service's configured checkout. A service bound to the main checkout does not accept a worktree path as a substitute; configure that worktree's service with its own authorized manager/root. The service revalidates repository identity before global Memory effects. Missing Git/global root, redirected Git environment, identity changes, unsupported paths or policy denial fail closed; global mode never falls back to project mode. The actual global root must already exist. Intermediate namespace/file symlinks are rejected rather than followed as implicit shared mappings.

Capability and operation receipts report `storage_scope`, `repository_id` when global, and the accurate scoped mapping. Global history version 2 uses an explicit `repository_id` and readable `task-plan-header-v2` / `task-plan-event-v2` JSON fences, allowing updates and exact logical-operation replay from another bound worktree without pretending its `project_root` is unchanged. Project-local version 1 remains checkout-bound with its original v1 framing. A retry from another worktree changes only the checkout binding; the operation ID and logical records/evidence must remain identical. A changed operation needs a new ID and a reviewed revision.

Global mode does not search, move or rewrite old unscoped global plans, project-local plans, or archives, nor automatically convert structured version-1 history. Keep their existing backend/mapping for access. Any separate migration must establish repository ownership, preserve the full source bytes, reject collisions and verify the destination under its own authorization; do not overwrite an archive. Plain legacy Markdown at an already verified scoped name can still be adopted by explicit revision, retaining its original bytes. Project mode remains available for non-Git projects and existing local users, but does not provide worktree sharing.

Source edits do not update a running MCP process. Follow the development guide's authorized build/install procedure and restart through an actually exposed host control before claiming the new tools are live. Confirm the negotiated tool inventory and configured backend status separately; package tests alone do not establish either result.

## Structured updates

Every tool uses one `payload.request` envelope. Supply the exact absolute `project_root`; it must match the configured checkout before any memory effects. `plan_id` is a bounded lower-case safe slug appended to the configured scope's active/archive namespace above. Callers cannot choose arbitrary memory paths, a repository ID, or an archive destination. A revision is the SHA-256 of the complete stored UTF-8 bytes.

Create with an explicitly absent revision:

```json
{
  "request": {
    "project_root": "/absolute/authorized/project",
    "plan_id": "example-task",
    "expected_revision": null,
    "request_id": "create-1",
    "records": [
      {"record_id": "goal-1", "kind": "goal", "text": "Preserve the task history", "sources": ["user:request-1"]},
      {"record_id": "criterion-1", "kind": "criterion", "text": "Prior records remain traceable", "sources": ["user:request-1"]}
    ]
  }
}
```

Pass this JSON as the `payload` argument. Subsequent updates require the returned revision, never an empty string or `null`. An existing corresponding archive prevents creating a new active plan under the same ID. If an existing legacy Markdown plan has no structured history, retain that content as an opaque prefix and append typed records with an explicit current revision. The service does not infer goals or criteria from prose. A revision conflict returns current-state information for review, not permission to retry blindly.

Records carry stable `record_id`, `kind`, `text`, and `sources`. Supported categories include goals, constraints, requirements, facts, decisions, progress, criteria, verification, blockers, resolutions, results and limitations. Supersession names an existing `supersedes_id` and supplies `supersedes_reason`; the old record remains unchanged. A resolution names its `resolves_blocker_id`. Verification records include an explicit outcome. Use the exposed schema for exact enums, bounds and allowed combinations.

The caller cannot submit a replacement document, arbitrary patch or regex. The service appends validated events, retains the complete original bytes and checks the history chain. Update/completion `request_id` values identify exact requests: identical replay is effect-free; reuse with different content is rejected. New content needs a new ID and current reviewed revision.

For an adopted legacy document, its original prose status is historical. The validated latest event and matching receipt provide the current lifecycle state; do not rewrite the legacy header to make it look current.

## Completion and archive

`task_plan_complete` takes `project_root`, `plan_id`, a current `expected_revision`, `request_id`, final result/limitation `records`, and `criterion_evidence` pairs containing `criterion_id` and `verification_id`. Every current criterion must appear exactly once and reference an active `passed` verification record. Missing, failed, assumed or unavailable evidence and unresolved blockers prevent completion. The service appends completion information; it never replaces accumulated content with final results. Completed plans reject further updates; exact completion replay remains effect-free.

This validates the structure of supplied evidence, not its truth, semantic sufficiency, or the Agent's authority to declare acceptance. Those judgments remain with the task's authorized owner.

`task_plan_archive` takes only `project_root`, `plan_id` and the completed plan's `expected_revision`. It preserves the final bytes while moving to the corresponding namespace, verifies destination equality and active-name absence, and rejects an occupied target while the active entry exists. It never uses Serena's reference-propagating rename operation. A repeated request can report an already matching archive only after validating its identity, completed state and exact revision; it cannot replace that archive.

## Protection and recovery boundary

The adapter uses the actual MemoryManager-backed canonical files and enforces its ignored/read-only policies. Strict names and path checks reject traversal and namespace/file symlinks. A POSIX advisory lock serializes cooperating lifecycle-tool calls across service instances. Under that lock, version checks, atomic writes and full readback reject stale or lossy changes. Oversized input/history fails without truncation or summarization.

Archive uses a no-clobber hard link followed by source removal, with identity/content checks. A failure between those steps may leave both names; the service reports reconciliation rather than deleting or overwriting an existing archive. A write followed by a readback failure may already have changed state. Treat an uncertain/reconciliation result as a block, inspect the last confirmed revisions and current names, and resolve it under existing authorization before further dependent work. Do not assume rollback or blindly repeat a changed request.

Raw Serena tools, direct filesystem writers and other processes that ignore the lock remain outside this protection. They can bypass the new tools; the service does not claim a global CAS or filesystem ACL. A host seeking exclusive enforcement must restrict those other write paths. A trusted factory also does not authenticate the caller or verify the truth of its supplied records.

These tools issue no OpenAI or network requests. Configuration and capability checks do not prove a real host integration; tests using temporary stores or injected managers are reported separately from actual installed-Serena checks. Use the [development guide](DEVELOPMENT.md) for locked checks and test classification. Real adapter checks must use a temporary project, never a user's existing memories or configuration.

For an explicit local integration check, run `tests/unit_tests/serena_memory_smoke.py` from `mcp/` with the absolute Python executable of an already installed compatible Serena environment. It loads the stdlib-only task-plan core from this checkout, uses the actual `MemoryManager`, and creates only temporary project/data directories. Alongside legacy preservation, completion/archive replay, concurrency and native policy checks, the global scenario must exercise real temporary Git repositories/worktrees, repository-isolated names and shared history. It is separate from ordinary pytest collection and does not install dependencies or load user configuration. Temporary Git fixtures do not authorize operations on the user's repository history.

The development integration was checked against installed `serena-agent 2.1.0`. Other versions must satisfy the adapter's actual interface and path checks; this is not a claim of compatibility with every Serena release.

## Related documents

- [Task-plan lifecycle](../references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md)
- [MCP development](DEVELOPMENT.md)
- [MCP directory instructions](AGENTS.md)
