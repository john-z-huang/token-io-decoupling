# Coding Session Model

[English](session-model.md) | [简体中文](session-model_zh_cn.md)

This module owns Coding Session semantics, Single-Agent and Multi-Agent Session mapping, Primary Execution Session affinity, and reuse/worktree separation boundaries. It consumes role ownership from its owner concept and state from the active workflow; it does not define role responsibilities, the Context Firewall, runtime eligibility, execution parameters, dispatch formatting, context-file transport, or acceptance procedures.

## Session semantics

The active workflow supplies mode, topology, role allocation, lifecycle, reuse, replacement, exceptions, and unavailable handling. A role label never authorizes a new Session or topology change.

In Single-Agent Coding, the current Session performs the logical decision, implementation, documentation, Git, and allowed-check phases; logical roles do not imply independent Agents. In Multi-Agent Coding, use only the child execution contexts explicitly supplied by the active workflow; their exact Session isolation depends on the runtime provider:

```text
root parent context → Input-side Reasoning
assigned Primary child context → Primary Output
assigned verifier child context → Change Verification
assigned docs/Git child context → Documentation/Comments & Git Operations
```

An unassigned role is unavailable as an independent child context. Do not simulate independence by relabeling same-context work. Apply [Runtime and Model Provider Support](runtime-provider-support.md) when describing the actual isolation of a provider's child.

## Primary Execution Session and affinity

Maintain one Primary Execution Session: the assigned Primary Output Session in multi-agent mode, otherwise the current Session. Reuse it for related exploration, implementation, diagnosis, tests, repairs, and local execution to preserve stable context. A Session is sticky but not immortal; lifecycle changes use the active workflow's recorded state.

Session separation and Git worktree separation are distinct. Workers for one development request normally share its primary worktree; an isolated worktree requires an explicitly released isolation scope. Do not claim cache hits or other runtime savings merely from Session reuse.

## Related concepts

- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibility ownership.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress boundaries.
- [Coding Delegation State Record](delegation-state-record.md) — locate task-control state ownership.
- [Coding Context Exchange](context-exchange.md) — locate file-backed context transport ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice and session-boundary controls.
