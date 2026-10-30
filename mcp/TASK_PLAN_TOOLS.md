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
    store = SerenaMemoryStore(memory_manager, project_root)
    return create_server(profile="workflow", task_plan_service=TaskPlanService(store))
```

For an operator-owned launcher integration, `--task-plan-factory module:callable` loads a zero-argument callable returning a configured `TaskPlanService`. For example:

```sh
token-io-decoupling start-mcp-server --profile workflow --task-plan-factory trusted_adapter:make_service
```

`trusted_adapter` is an operator-provided, reviewed module, not a bundled adapter or a tool argument. Its environment must already contain the compatible Serena dependency and authorized project object. The tool package does not install Serena, load/migrate its configuration, create a project, guess a `.serena` directory, or open another Memory store. Do not execute an invented factory to obtain availability. An unconfigured service returns `unavailable` without inspecting memory paths; invalid explicit configuration fails rather than silently falling back.

Source edits do not update a running MCP process. Follow the development guide's authorized build/install procedure and restart through an actually exposed host control before claiming the new tools are live. Confirm the negotiated tool inventory and configured backend status separately; package tests alone do not establish either result.

## Structured updates

Every tool uses one `payload.request` envelope. Supply the exact absolute `project_root`; it must match the configured backend before any memory effects and cannot switch the service to another checkout. `plan_id` is a bounded lower-case safe slug; its names are `plans/PLAN-<plan_id>` and `archive-plans/PLAN-<plan_id>`. Callers cannot choose arbitrary memory paths or an archive destination. A revision is the SHA-256 of the complete stored UTF-8 bytes.

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

For an explicit local integration check, run `tests/unit_tests/serena_memory_smoke.py` from `mcp/` with the absolute Python executable of an already installed compatible Serena environment. It loads the stdlib-only task-plan core from this checkout, uses the actual `MemoryManager`, and creates only temporary project/data directories. It checks legacy UTF-8/CRLF preservation, readable multi-stage records, supersession, stale versions, completion/archive replay, no resurrection, two-store concurrency, native read-only policy and absence of reference propagation. It is separate from ordinary pytest collection and does not install dependencies or load user configuration.

The development integration was checked against installed `serena-agent 2.1.0`. Other versions must satisfy the adapter's actual interface and path checks; this is not a claim of compatibility with every Serena release.

## Related documents

- [Task-plan lifecycle](../references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md)
- [MCP development](DEVELOPMENT.md)
- [MCP directory instructions](AGENTS.md)
