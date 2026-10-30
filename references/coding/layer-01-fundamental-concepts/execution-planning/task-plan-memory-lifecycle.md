# Task Plan Memory Lifecycle

[English](task-plan-memory-lifecycle.md) | [简体中文](task-plan-memory-lifecycle_zh_cn.md)

This owner defines the shared task plan's creation, updates, access, and archive lifecycle. It applies by default to Coding work, with or without an Issue. It does not own planning methods, execution authorization, live parent scheduling state, or authoritative repository documentation.

## General rules

### Default task plan

Every current and future Coding route must consume this owner before implementation and throughout execution. An explicit request for a plan or a dedicated planning mode is unnecessary. Respect an explicit user prohibition on persistence or a higher-priority write restriction: record that exception and keep bounded planning in the authorized context; do not silently treat missing tools, uncertain permissions, or a failed write as an exception. If the user requires a persisted plan and a restriction prevents it, stop the dependent work and report the conflict.

For an Issue task, read the Issue and relevant discussion, compare its requirements with current project facts, and synthesize the proposed change before implementation. Without an Issue, use the user's stated problem and current project facts in the same way. Before the initial analysis is complete, a concise provisional plan may capture the goal, known facts, and unanswered questions; it must not claim an implementation direction is released. Persist and read back the concrete plan before implementation or dependent dispatch. New facts discovered during analysis must be recorded before they are reported or used for the next dependent action.

### Names, storage, and initial evidence

Reuse the user's designated active plan for the same task; otherwise use `plans/PLAN-[short-english-summary]`, optionally including a verified Issue number. Do not include `.md`. The corresponding default archive name is `archive-plans/PLAN-[short-english-summary]`; for a user-designated name, agree its archive mapping within the existing task authorization before archiving. Under the default project data directory, the active file is `<project-root>/.serena/memories/plans/PLAN-[short-english-summary].md`. Follow the project's configured data-directory override and Memory tool mapping; do not hardcode a second directory or create a filesystem substitute.

Confirm the exact project/worktree binding and effective memory-maintenance guidance. List Memories and read an existing matching plan before creating or updating it. Reuse only a plan for the same ongoing task; preserve unrelated plans and choose a distinct name on collision. Write the concise plan and read it back to compare with intent before dependent work. Missing required Memory capability, inaccessible required content, or failed write/readback blocks dependent work; report the exact operation and preserve the last confirmed plan.

### Plan content

Keep one concise shared plan with the goal and acceptance conditions; Issue or user-request source; constraints and non-goals; verified project facts and exact source pointers; chosen direction and unresolved questions; bounded steps, dependencies, and verification approach; completed/current/remaining work; actual checks, blockers, and residual risks. Distinguish facts, assumptions, proposals, and accepted decisions. Use compact deltas and useful current evidence rather than transcripts, full diffs, logs, or private reasoning. Concision applies to new entries; it never permits replacing accumulated content with a current-state or final summary. Preserve existing goals, constraints, requirement changes, sourced facts, decision reasons, stage progress, shared contributions, failures, and verification records. Mark a stale conclusion as superseded, retaining its original claim and evidence and adding the replacement, reason, and source; do not silently delete or rewrite its history.

### Preservation checks for every update

1. Immediately before writing, read the complete latest active plan, including every part if the response is paginated or truncated. Retain that readback as the comparison baseline in the authorized context. An incomplete read blocks the update; a remembered outline or earlier snapshot is insufficient.
2. Merge only the authorized local status/step changes and append new facts, results, or evidence to that baseline. Prefer a targeted edit. If only whole-document replacement is available, submit the full merged document, not a newly drafted summary. Preserve all other entries and contributions; apply the supersession rule above to changed conclusions.
3. Read back the complete updated plan and compare it with the baseline: each pre-existing record must remain traceable, with its provenance, reason, and evidence intact; only the authorized status/step changes and explicit supersessions may differ. Confirm new entries separately. A successful write or a spot check of final status alone does not pass preservation.
4. Missing content, conflicting contributions, or uncertain write/readback results block affected reporting, dependent actions, and archiving. Preserve the last confirmed baseline, reread current state, and reconcile under existing authorization before rechecking. Never blindly replay a stale replacement. Keep this comparison within authorized context; do not persist transcripts or private reasoning.

### Update before reporting or dependent action

Every participating Agent, including the parent and any verifier, reads the same current plan on entry/resume and before relying on its contents. After obtaining a new material project fact or changing task progress, persist the concise fact/status, provenance, and next step, then read back the affected entry before a progress report, handoff, or next action that depends on it. Routine unchanged tool output need not produce duplicate entries. Reports may cite the plan but cannot replace updating it.

For a changed user requirement, first record the new instruction and its source as pending analysis. Then analyze its impact on scope, dependencies, acceptance, and the proposed solution; persist and read back that analysis and revised plan. Only afterward may the parent authorize affected changes or dispatch. If the change arrives in a child context, record it within the child's permitted contribution and return it to the parent; the child cannot amend the Contract or release work. Keep unaffected authorized work available only when it does not depend on the pending change.

### Shared access and update coordination

The parent supplies the exact project root, Memory name, relevant source scope, and allowed contributions in every affected dispatch. Verify that each Agent can use the required Memory read/update operations in that project; sharing a name does not establish cross-Session access. If required access is unavailable, stop the dependent assignment and report it instead of silently replacing the Agent's write with an unverified relay or filesystem file.

Serialize updates to the shared plan. The parent coordinates one writer at a time; each writer rereads the latest entry immediately before changing only its permitted facts/status, preserves other contributions, and reads back its change before releasing the write turn. Do not assume atomic compare-and-swap or locks from a Memory tool. On conflict or uncertain write outcome, pause affected reporting/actions, reread and reconcile under the parent's existing authorization; never blindly overwrite or retry a stale full document.

The plan is shared task context, not the live parent mode/count/allocation/epoch record, an execution memo, or a source of authorization. Do not store that live scheduling state in it. Plan read/write access grants no access to other Memories, source files, raw peer context, or new effects. Respect the Context Firewall and each role's released scope; return proposals through the parent. A verifier may update only its named plan contribution and remains read-only for implementation and Git. A false execution-memo flag does not waive shared task-plan updates.

### Completion and archive

Keep the plan active while the task is incomplete or blocked. After every applicable Acceptance criterion passes:

1. Apply the preservation checks above to the complete active plan: update only completion status/steps and append final results, Acceptance evidence, and remaining limitations. Retain the accumulated document; a final summary may be appended but must never replace it. Read back and pass the full preservation comparison before archiving.
2. Retain this verified final active content as the archive baseline and confirm the matching archive target is absent. Archive only this completed task's plan by moving its namespace/name, without changing its content. A collision blocks the move; preserve both entries and report it.
3. Read back the complete archive and compare it with the final active baseline: content must be identical. List Memories to confirm the archive exists and the active name is absent. A missing record, content difference, or update/archive/readback failure blocks completion; preserve the last confirmed state and resolve uncertain effects before proceeding.

Archived plans are instruction-level immutable: never edit, delete, rename, or replace an existing archive, including to repair a failed archive comparison; tool visibility does not technically enforce this rule. Report such a mismatch for a separate authorized recovery decision. Never archive an unrelated or incomplete plan.

### Preservation acceptance scenario

Use a new synthetic plan in an authorized test scope, never an existing user's plan. Include multiple stages, a goal and constraint, a sourced requirement change, a decision with its reason, another contributor's entry, a failed check and later passing check. Include small facts such as “two untracked-file manifests verified” and “no PR template found” so a short final summary cannot accidentally pass. Supersede one conclusion with a reason and source, complete through the checks above, then archive. Verify every original record remains traceable, the superseded claim and its replacement both remain, final results were appended, the archive equals the final active baseline, and the active name disappeared. Also review a summary-only candidate and an occupied archive target: neither may advance to a write/move that loses content or overwrites an archive. Report actual exercised checks separately from scenario review; this does not prove tool-enforced immutability or recover past losses.

## Codex CLI / ChatGPT Desktop optimizations

Use the Serena MCP operations actually exposed and authorized: `list_memories`, `read_memory`, `write_memory` or `edit_memory`, and `rename_memory` for completion. In the observed Codex tool surface, creation takes `{memory_name, content}`, reading takes `{memory_name}`, and rename takes `{old_name, new_name}`; use the active tool schema for exact arguments. Confirm project activation before these operations. This is the concrete MCP-backed task-plan mechanism; native `/plan`, local recall, and chat compaction do not persist or update this shared record. The current Session's successful Memory calls are runtime evidence, not proof that another Agent or Desktop Session exposes the same tools. Check each assigned Agent. [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp).

## Claude Code CLI / Claude Desktop optimizations

The corresponding capability is the same Serena MCP Memory service when connected and actually exposed to that Agent. Discover its tools through the active MCP tool-discovery mechanism, then invoke its `list_memories`/`read_memory`, `write_memory` or `edit_memory`, and `rename_memory` with the discovered schemas and exact project/name. Tool discovery, approval, and availability can differ from Codex; do not assume identical exposed prefixes or inherited connections. Native Plan mode, todo state, and automatic memory are not substitutes for this shared task plan. If the required Serena operations are absent or effective permissions deny them, block dependent persistence/assignment. Claude Desktop follows the same actual-exposure rule and never uses GUI navigation to establish access. [Claude Code MCP tool availability](https://code.claude.com/docs/en/mcp#tool-availability).

## Related concepts

- [Execution Planning](execution-planning.md) — planning method and reconnaissance ordering.
- [Serena LSP and MCP Tools](../session-runtime/LSP-MCP-Tools.md) — project binding and Memory capability.
- [Session Context Firewall](../session-runtime/session-context-firewall.md) — bounded context ingress.
- [Delegation Worker Boundary](../delegation/delegation-worker-boundary.md) — released child scope.
