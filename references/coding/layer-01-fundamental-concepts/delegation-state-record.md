# Coding Delegation State Record

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

This module owns the task-control record used by Coding delegation. It defines the record's canonical location, ownership, shape, field constraints, and staged presence semantics. It does not decide the mode, define Worker read/write boundaries, create children, allocate roles, or define lifecycle transitions.

## General rules

### Ownership

The root parent owns one conversation-level mode/count decision and updates task-specific slices and lifecycle in the same record. The record is task state; it is not stored by editing a policy file. Use a parent-controlled task panel when available; otherwise maintain an explicit structured record in the parent conversation that can be read back before each route release. Do not treat a transient child-status UI as the canonical record.

### Record shape

Before route release, maintain this canonical record:

```text
owner: <root-parent identity>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode_source: unset | explicit | timeout-default
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <locked positive integer>
allocations: [{agent: unbound | <created-agent-identity>, role: unassigned | <role>,
               slice_status: pending | released, interaction_slice, scope, mutations,
               return_conditions, lifecycle, write_content_memo}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<capability names>]
block_reason: <required only when gate_status is blocked>
```

| `gate_status` | Mode and count | Allocations and lifecycle | Additional requirement |
| --- | --- | --- | --- |
| `awaiting-mode` | Unset | `[]`; top-level lifecycle `pending` | Initialize before an unanswered first mode question. |
| `awaiting-count` | Multi-Agent; count unset | `[]`; top-level lifecycle `pending` | Only an invalid explicit count enters this state; an omitted count defaults to one. |
| `released` — Single-Agent | Single-Agent; count `0` | `[]`; top-level lifecycle required | Releases the single route, not an independent Session. |
| `released` — Multi-Agent | Multi-Agent; locked positive count | Exactly `child_count` reserved allocations; each starts `agent: unbound`, `role: unassigned`, `slice_status: pending`, `lifecycle: pending` | Releases the route and count budget, **not** each child or Interaction Slice. |
| `blocked` | Preserve confirmed values | Preserve existing allocations/lifecycle | `unavailable_capabilities` and `block_reason` required; cannot enter a dependent route. |

An allocation's role becomes assigned at Role Allocation. A concrete `slice_status: released` requires `role`, `interaction_slice`, `scope`, `mutations`, `return_conditions`, and an explicit boolean `write_content_memo`; pending slices may leave these fields unset. Before serializing each released Worker bundle, include `write_content_memo: true` or `false`; the Worker never infers a default. Child Creation may bind `agent` and lifecycle only after the target role and slice are released. A later slice may be prepared on the **same** created child without creating or recycling a slot.

`mode_source` records the explicit choice or 15-second default and remains fixed for this conversation. Allocation lifecycle may differ from top-level task lifecycle. Blocking preserves all confirmed values; later directives use the Re-entry owner without changing locked mode/count.

## Codex CLI / ChatGPT Desktop optimizations

In Codex, `AGENTS.md` is an instruction source, not a writable live mode/count record; hook events such as `SessionStart` and `SubagentStart` can refresh approved context only when configured and supported. The actual parent record, allocated identities and epoch must be read back before route release, even if a task UI or hook event reports an Agent as running. [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks), [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Codex `/agent`, the Desktop child panel and `/status` expose useful runtime observations, while `AGENTS.md`, optional local memories and `/compact` serve different purposes: project instructions, recall and chat condensation. None is the authoritative live mode/count/allocation/epoch record. After a CLI resume, compact or Desktop chat handoff, read the retained parent record before any new route release; `SessionStart` on `compact` can add approved context if an enabled/trusted hook actually runs but does not re-lock a count. [OpenAI: subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [OpenAI: memories](https://learn.chatgpt.com/docs/customization/memories), [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

Claude Code has no equivalent durable Codex parent task panel. Maintain the structured mode, count, and slice record in the parent conversation and read it back before route release. `/tasks` is only a temporary subagent status view, not the canonical record.

Claude Code's `/tasks` lists observable current/background subagent work, whereas `/context` inspects loaded instruction/memory files. Neither is the canonical mode/count/allocation record, and `CLAUDE.md` and auto memory are **instruction or learning context**, not a place to rewrite the live task record. If the parent resumes a conversation after compaction or restart, read back its retained task record and validate the locked gate and current epoch before releasing a new slice. A configured `SessionStart` hook may provide approved initial context, but its output alone cannot create an allocation or overwrite the locked count. [Anthropic: memory](https://code.claude.com/docs/en/memory), [Anthropic: hooks](https://code.claude.com/docs/en/hooks), [Anthropic: subagent status](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary.md) — locate Worker snapshot and record access boundaries.
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice field ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle field ownership.
