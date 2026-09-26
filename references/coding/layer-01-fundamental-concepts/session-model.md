# Coding Session Model

[English](session-model.md) | [简体中文](session-model_zh_cn.md)

This module owns Coding Session semantics, Single-Agent and Multi-Agent Session mapping, Primary Execution Session affinity, and reuse/worktree separation boundaries. It consumes role ownership from its owner concept and state from the active workflow; it does not define role responsibilities, the Context Firewall, runtime eligibility, execution parameters, dispatch formatting, context-file transport, or acceptance procedures.

## General rules

### Session semantics

The active workflow supplies mode, topology, role allocation, lifecycle, reuse, replacement, exceptions, and unavailable handling. A role label never authorizes a new Session or topology change.

In Single-Agent Coding, the current Session performs the logical decision, implementation, documentation, Git, and allowed-check phases; logical roles do not imply independent Agents. In Multi-Agent Coding, use only the child execution contexts explicitly supplied by the active workflow; their exact Session isolation depends on the runtime provider:

```text
root parent context → Input-side Reasoning
assigned Primary child context → Primary Output
assigned verifier child context → Change Verification
assigned docs/Git child context → Documentation/Comments & Git Operations
```

An unassigned role is unavailable as an independent child context. Do not simulate independence by relabeling same-context work.

### Primary Execution Session and affinity

Maintain one Primary Execution Session: the assigned Primary Output Session in multi-agent mode, otherwise the current Session. Reuse it for related exploration, implementation, diagnosis, tests, repairs, and local execution to preserve stable context. A Session is sticky but not immortal; lifecycle changes use the active workflow's recorded state.

Session isolation and Git worktree isolation are distinct. Workspace and filesystem isolation requirements belong to [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md); Session reuse alone does not prove cache hits or runtime savings.

## Codex CLI / ChatGPT Desktop optimizations

An allocated Codex child uses an independent child Session and task UI. Report only the isolation actually exposed by the runtime.

### Desktop chat, child and worktree are different identities

In Desktop Codex, the project chat is a root Session and a spawned subagent thread is its child only when a Session-exposed tool reports that parent-child relationship; the visible panel is not itself an Agent tool. A separate chat started in `Worktree` is an independent chat and Git checkout; `Handoff` moves one chat between Local and Worktree, not between parent and child identities. Codex-managed worktrees can be detached-HEAD and disposable; neither workspace reuse nor a pinned chat is proof that a verifier used an independent model context. An ordinary Chat or Work conversation in the same app is not silently the active Codex child. [OpenAI: subagent threads](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: worktree and Handoff](https://learn.chatgpt.com/docs/environments/git-worktrees), [OpenAI: Desktop modes](https://learn.chatgpt.com/docs/use-chatgpt).

## Claude Code CLI / Claude Desktop optimizations

A Claude Code subagent has its own context inside the parent session; it has no identical independent Codex task UI. Treat it as the allocated child context, return only to the parent, and report actual isolation and verification independence. Do not use an agent team or peer channel as a substitute. A Codex-only UI convenience needs no Claude Code equivalent when the parent record and result supply the required evidence.

For a Claude Code subagent, its `Agent` invocation and returned ID identify a child context within the parent Session; the built-in Explore and Plan agents are one-shot and do not return resumable IDs. Preserve the parent identity and the returned ID if a future authorized follow-up may be needed. `/resume` resumes a Claude Code conversation, not an arbitrary previously completed one-shot child. [Anthropic: subagent context and resume](https://code.claude.com/docs/en/sub-agents).

In Claude Desktop's **Code** tab, separate local sessions may be isolated into their own Git worktrees; these are independent desktop sessions, not silently allocated children of the current `Agent` call. Ordinary Desktop Chat has no documented equivalent Code-tab worktree Session control. Never count a separate pane or worktree as the locked child without a verified parent-controlled Agent identity. [Anthropic: Desktop sessions](https://code.claude.com/docs/en/desktop).

## Related concepts

- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibility ownership.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress boundaries.
- [Coding Delegation State Record](delegation-state-record.md) — locate task-control state ownership.
- [Coding Context Exchange](context-exchange.md) — locate file-backed context transport ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice and session-boundary controls.
