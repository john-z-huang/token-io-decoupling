# Coding Context Exchange Workspace Boundary

[English](context-exchange-workspace-boundary.md) | [简体中文](context-exchange-workspace-boundary_zh_cn.md)

This module owns the file-backed context workspace layout, directory ownership, filesystem capability boundary, worktree separation, and OS-level isolation requirements. It does not define capsule content, freshness, handoff records, or child reuse/replacement authorization.

## General rules

### Workspace ownership

- Set `CONTEXT_ROOT=<primary-worktree>/.token-io-decoupling/context/`. The parent exclusively maintains `CONTEXT_ROOT/INDEX.md`, mapping each assigned or historical Context ID to its directory and minimal routing state. The canonical layout is `CONTEXT_ROOT/INDEX.md`, `CONTEXT_ROOT/<worker-context-id>/`, `CONTEXT_ROOT/<worker-context-id>/imports/<source-context-id>/` for parent-prepared read-only imports, and, when bootstrap is assigned, `CONTEXT_ROOT/context-bootstrap/`.
- Before an assigned Worker uses file-backed exchange or an enabled file-backed memo, the parent provisions `CONTEXT_ROOT/<worker-context-id>/` and gives the exact path. For a concrete handoff or dependency, the parent provisions and names the relevant `imports/<source-context-id>/` directory and source documents. Imports are read-only and are not Worker-writable generated context; the Worker may write only other permitted content in its own context directory and must not access another Worker's directory unless the parent names specific documents.
- Workers normally share the task's primary worktree. An additional worktree requires a concrete isolation need, such as incompatible snapshots/environments, unredirectable validation writes, a distinct permission/security boundary, or an explicitly isolated audit. Worktree separation alone is not a permission boundary.
- The repository `.gitignore` must ignore `.token-io-decoupling`. This root is runtime coordination state, not a product artifact; do not delete it automatically.

### Capability boundary

When the runtime supports filesystem capabilities, enforce the smallest set before execution:

- **RW**: only the Worker's released code paths and permitted writable content in its own context directory; `imports/` is excluded, and a verifier may write only named verification assets.
- **RO**: only source paths required for the released slice and specifically named documents or imports from another Worker.
- **DENY**: the root `INDEX.md`, unlisted imports, other Worker directories, and every other unlisted path.

If several Workers share one OS identity, ordinary Unix ownership is not reliable isolation; use a real sandbox, container/mount namespace, path allowlist, or equivalent. A Worker must stop when the runtime cannot enforce the required boundary.

## Codex CLI / ChatGPT Desktop optimizations

Current Codex offers custom child-agent `sandbox_mode` and per-agent MCP configuration, and, when hooks are supported/enabled in this runtime, `PreToolUse` for supported `Bash`, `apply_patch`, and MCP calls. Match all actually exposed write-capable paths and test a denied cross-Worker write rather than treating `workspace-write`, a worktree, or `AGENTS.md` as a complete filesystem policy. Some specialized tool paths bypass Codex hooks; where that gap matters, enforce the path boundary through OS/filesystem/container permissions or block the dependent slice. The Claude `permissions.deny` syntax does not transfer to Codex. [OpenAI: subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: hook coverage](https://learn.chatgpt.com/docs/hooks).

### Codex-managed worktree and hard path boundary

When the user authorizes an additional checkout, a Session-exposed Git/worktree tool may create it. Desktop Codex `Worktree` and `Handoff` are human-facing product controls: the Agent must not click or automate them, and must not assume equivalent worktree creation/chat transfer is exposed as a tool. A managed worktree may use detached HEAD and can later be cleaned up; it is **not** a child Agent slot, a guarantee that the parent `CONTEXT_ROOT` is reachable, or an OS-level RW/RO/DENY fence. Verify the physical paths after checkout creation, then separately enforce Worker path rights with available OS/filesystem/container controls and, if trusted/enabled, a tested `PreToolUse` guard for exposed local write tools. Hooks do not cover all specialized paths or undo already executed commands; if required isolation is unavailable, block the slice. [OpenAI: worktree behavior](https://learn.chatgpt.com/docs/environments/git-worktrees), [OpenAI: hook coverage](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

When the task releases worktree isolation or tool restrictions, Claude Code may use `EnterWorktree`/`ExitWorktree` or a custom agent with `isolation: worktree`, and `tools`/`disallowedTools` for tool scope. These controls alone do not enforce named filesystem path permissions. If a required path boundary cannot be enforced, block the dependent slice; otherwise use the ordinary shared worktree and default tools.

### Claude Code worktree and path enforcement

For a genuinely required additional checkout, an authorized custom agent may use `isolation: worktree`; verify the resulting directory and keep the parent-owned Context root and named imports reachable under the approved policy. Claude Code's worktree/isolation feature separates checkouts but is **not** an OS sandbox or a guarantee of Worker-only path access. Where available, pair a real filesystem sandbox/container/path allowlist with a reviewed `PreToolUse` guard matching relevant `Read`/`Write`/`Edit`/shell or MCP filesystem operations; validate canonical paths and the shell's possible indirect writes, not merely a literal string prefix. `PreToolUse` does not intercept every way context can enter the prompt (such as file mentions); do not claim that a Hook alone meets a hard RO/RW/DENY boundary. If required enforcement is absent, block that slice under the general capability rule rather than treating `disallowedTools` or a worktree as security isolation.

Official references: [subagent worktree isolation](https://code.claude.com/docs/en/sub-agents), [PreToolUse coverage and restrictions](https://code.claude.com/docs/en/hooks).

Where authorized and available, combine Claude Code's `permissions.deny` with a deterministic `PreToolUse` guard on *all exposed write-capable paths*, including indirect shell and MCP filesystem writes; test an actual prohibited cross-Worker write before relying on it. `PostToolUse` is too late to prevent the operation, and `SubagentStart` cannot veto creation. A local Desktop Extension runs with its own OS/filesystem permissions; mere installation does not prove it respects Worker RW/RO/DENY. [Anthropic: permissions](https://code.claude.com/docs/en/permissions), [Anthropic: hooks](https://code.claude.com/docs/en/hooks), [Anthropic: local MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

## Related concepts

- [Coding Context Exchange](context-exchange.md) — locate capsule and freshness ownership.
- [Coding Context Exchange Handoff](context-exchange-handoff.md) — locate handoff record ownership.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress ownership.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate named-path dispatch boundaries.
