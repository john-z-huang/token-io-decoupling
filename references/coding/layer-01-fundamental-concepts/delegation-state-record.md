# Coding Delegation State Record

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

This module owns the task-control record used by Coding delegation. It defines the record's canonical location, ownership, shape, field constraints, and staged presence semantics. It does not decide the mode, define Worker read/write boundaries, create children, allocate roles, or define lifecycle transitions. Per-child model configuration metadata is stored in a separate Serena project Memory; this record stores only its exact `mem:` reference.

## General rules

### Ownership

The root parent owns one conversation-level mode/count decision and updates task-specific slices and lifecycle in the same record. The record is task state; it is not stored by editing a policy file. Maintain an explicit structured record in the parent context that can be read back before each route release. A transient child-status result is not the canonical record.

### Runtime model configuration Memory reference

Each Multi-Agent delegation run has a stable `run_id`, and each reserved child allocation has a stable `allocation_id`. Assign both before preparing the child's model configuration Memory and retain them through resume and follow-up. Single-Agent records keep `run_id: unset`. The allocation's runtime model configuration Memory reference stays unset while the allocation is only reserved. Before creating a child, the parent writes and reads back the Memory at `agent-session-context/<run-id>/<allocation-id>`, then stores only `mem:agent-session-context/<run-id>/<allocation-id>` here. Keep the reference attached while the same child can be resumed or receive follow-up. Do not copy model metadata into the parent task-state record.

### Record shape

Before route release, maintain this canonical record:

```text
owner: <root-parent identity>
run_id: unset | <stable identifier for this Multi-Agent delegation run>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode_source: unset | explicit | timeout-default
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <locked positive integer>
allocations: [{allocation_id: <stable child allocation identifier>,
               agent: unbound | <created-agent-identity>, role: unassigned | <role>,
               slice_status: pending | released, interaction_slice, scope, mutations,
               return_conditions, lifecycle, write_content_memo,
               runtime_model_config_memory: unset | mem:agent-session-context/<run-id>/<allocation-id>}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<capability names>]
block_reason: <required only when gate_status is blocked>
```

| `gate_status` | Mode and count | Allocations and lifecycle | Additional requirement |
| --- | --- | --- | --- |
| `awaiting-mode` | Unset | `[]`; top-level lifecycle `pending` | Initialize before an unanswered first mode question. |
| `awaiting-count` | Multi-Agent; count unset | `[]`; top-level lifecycle `pending` | Only an invalid explicit count enters this state; an omitted count defaults to one after an explicit Multi-Agent selection. |
| `released` — Single-Agent | Single-Agent; count `0` | `[]`; top-level lifecycle required | Releases the single route, not an independent Session. |
| `released` — Multi-Agent | Multi-Agent; locked positive count | Exactly `child_count` reserved allocations; `run_id` is set; each has a unique stable `allocation_id` and starts `agent: unbound`, `role: unassigned`, `slice_status: pending`, `lifecycle: pending` | Releases the route and count budget, **not** each child or Interaction Slice. |
| `blocked` | Preserve confirmed values | Preserve existing allocations/lifecycle | `unavailable_capabilities` and `block_reason` required; cannot enter a dependent route. |

An allocation's role becomes assigned at Role Allocation. A concrete `slice_status: released` requires `role`, `interaction_slice`, `scope`, `mutations`, `return_conditions`, and an explicit boolean `write_content_memo`; pending slices may leave these fields unset. Before serializing each released Worker bundle, include `write_content_memo: true` or `false`; the Worker never infers a default. Child Creation may bind `agent` and lifecycle only after the target role and slice are released. A later slice may be prepared on the **same** created child without creating or recycling a slot.

`mode_source` records the explicit choice or 15-second default and remains fixed for this conversation. Allocation lifecycle may differ from top-level task lifecycle. Blocking preserves all confirmed values; later directives use the Re-entry owner without changing locked mode/count.

When `mode_source: timeout-default`, the released record must be Single-Agent with `child_count: 0` and `allocations: []`. The directive-related work remains in the current Session; no child may be inferred or created from the timeout.

## Codex CLI / ChatGPT Desktop optimizations

In Codex, `AGENTS.md` is an instruction source, not a writable live mode/count record; hook events such as `SessionStart` and `SubagentStart` can refresh approved context only when configured and supported. Read back the actual parent record, allocated identities and epoch before route release; runtime status and hook events are not the canonical record. [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks), [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Codex `/agent` and `/status`, when exposed to the active Agent Session, provide runtime observations; `AGENTS.md`, optional local memories and `/compact` serve different purposes: project instructions, recall and chat condensation. None is the authoritative live mode/count/allocation/epoch record. After a Session resume, compact, or tool-mediated thread transfer, read the retained parent record before any new route release; `SessionStart` on `compact` can add approved context if an enabled/trusted hook actually runs but does not re-lock a count. [OpenAI: subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [OpenAI: memories](https://learn.chatgpt.com/docs/customization/memories), [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

Maintain the structured mode, count, and slice record in the parent context and read it back before route release. `/tasks` output is only a temporary subagent status signal, not the canonical record.

Claude Code's `/tasks` lists observable current/background subagent work, whereas `/context` inspects loaded instruction/memory files. Neither is the canonical mode/count/allocation record, and `CLAUDE.md` and auto memory are **instruction or learning context**, not a place to rewrite the live task record. If the parent resumes a conversation after compaction or restart, read back its retained task record and validate the locked gate and current epoch before releasing a new slice. A configured `SessionStart` hook may provide approved initial context, but its output alone cannot create an allocation or overwrite the locked count. [Anthropic: memory](https://code.claude.com/docs/en/memory), [Anthropic: hooks](https://code.claude.com/docs/en/hooks), [Anthropic: subagent status](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary.md) — locate Worker snapshot and record access boundaries.
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Child Runtime Model Configuration Metadata](delegation-child-runtime-model-configuration-metadata.md) — locate the per-child model configuration Memory schema and read/write checks.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice field ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle field ownership.
