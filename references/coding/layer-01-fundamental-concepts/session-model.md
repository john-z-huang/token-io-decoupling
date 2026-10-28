# Coding Session Model

[English](session-model.md) | [简体中文](session-model_zh_cn.md)

This module owns Coding Session semantics, Single-Agent and Multi-Agent Session mapping, Primary Execution Session affinity, and reuse/worktree separation boundaries. It consumes role ownership from its owner concept and state from the active workflow; it does not define role responsibilities, the Context Firewall, runtime eligibility, execution parameters, dispatch formatting, project-context transport, or acceptance procedures.

## General rules

### Session semantics

The active workflow supplies mode, topology, role allocation, lifecycle, reuse, replacement, exceptions, and unavailable handling. A role label never authorizes a new Session or topology change.

Here, a Session means the host-identified Session lifetime, not one user/assistant exchange. Later turns and a compacted or resumed instance of the same Session retain its mode, count, and child identities. A Fork with a new Session identity starts a separate lifetime and must pass fresh re-entry gates.

A Fork starts a new Coding Session with a new root identity. Re-enter fresh mode/count selection before dependent work, even when the source Session used Single-Agent mode. Child identities bound to the source Session are foreign in the Fork: do not adopt them as created children, reuse or resume them, count them toward its capacity, or offer them as current-session candidates. The [Delegation Mode Re-entry](delegation-mode-reentry.md) and [Session State Record](delegation-state-record.md) owners govern the new record.

In Single-Agent Coding, the current Session performs the logical decision, implementation, documentation, Git, and allowed-check phases; logical roles do not imply independent Agents. In Multi-Agent Coding, use only the child execution contexts explicitly supplied by the active workflow; their exact Session isolation depends on the runtime provider:

```text
root parent context → Input-side Reasoning
assigned Primary child context → Primary Output
assigned verifier child context → Change Verification
assigned docs/Git child context → Documentation/Comments & Git Operations
```

An unassigned role is unavailable as an independent child context. Do not infer a role from the number of reserved slots; one slot does not automatically mean Primary Output. Select a role only after current task context and Decision are reviewed, then record it in an unassigned slot under the role-selection and allocation owners. Do not simulate independence by relabeling same-context work.

### Primary Execution Session and affinity

Maintain one Primary Execution Session: the current Session in Single-Agent mode; in Multi-Agent mode, the created child assigned `Primary Output`, when one exists. Until that child exists, the current root Session remains the active decision context, not an implied Primary child. Reuse the assigned Primary Session for related exploration, implementation, diagnosis, tests, repairs, and local execution to preserve stable context. A Session is sticky but not immortal; lifecycle changes use the active workflow's recorded state.

Session isolation and Git worktree isolation are distinct. Workspace and filesystem isolation requirements belong to [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md); Session reuse alone does not prove cache hits or runtime savings.

## Codex CLI / ChatGPT Desktop optimizations

An allocated Codex child uses an independent child Session. Confirm that relationship only through runtime metadata or a directly exposed child/thread tool, and report only the isolation those sources establish.

For Codex, the Session runs from the host Session's start until it ends; it is not reset by each user/assistant turn. Compaction and reopening or resuming the same Session retain its mode/count and child-identity record. A Fork creates a new Session identity and follows the fresh re-entry gate.

### Desktop Session and child identities

In ChatGPT Desktop, count a spawned Codex thread as a child only when a tool exposed to the active Session reports that parent-child relationship. A tool that creates or transfers another Session or worktree does not by itself establish a child identity; Codex-managed worktrees can be detached-HEAD and disposable. A Chat or Work Session is not a Codex child unless an exposed tool reports that relation. [OpenAI: subagent threads](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: worktree behavior](https://learn.chatgpt.com/docs/environments/git-worktrees), [OpenAI: Desktop modes](https://learn.chatgpt.com/docs/use-chatgpt).

## Claude Code CLI / Claude Desktop optimizations

A Claude Code subagent has its own context inside the parent session. Treat it as the allocated child context, return only to the parent, and report actual isolation and verification independence. Do not use an agent team or peer channel as a substitute.

For a Claude Code subagent, its `Agent` invocation and returned ID identify a child context within the parent Session; the built-in Explore and Plan agents are one-shot and do not return resumable IDs. Preserve the parent identity and the returned ID if a future authorized follow-up may be needed. `/resume` resumes a Claude Code conversation, not an arbitrary previously completed one-shot child. [Anthropic: subagent context and resume](https://code.claude.com/docs/en/sub-agents).

In Claude Desktop, use the built-in `Agent` or `SendMessage` tool only when directly exposed to the active Session. A separately identified Session, connector tool call, or worktree is not an allocated child unless the parent-controlled tool result establishes that identity relation. [Anthropic: subagent context and lifecycle](https://code.claude.com/docs/en/sub-agents), [Anthropic: Desktop MCP tools](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

## Related concepts

- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibility ownership.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress boundaries.
- [Coding Delegation State Record](delegation-state-record.md) — locate task-control state ownership.
- [Coding Delegation Mode Re-entry](delegation-mode-reentry.md) — locate fresh mode/count selection for a Fork.
- [Coding Child Role Selection](child-role-selection.md) — locate the decision that supplies a new child's role.
- [Coding Task Assignment](task-assignment.md) — locate Root and existing-child selection.
- [Coding Context Exchange](context-exchange.md) — locate file-backed context transport ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice and session-boundary controls.
