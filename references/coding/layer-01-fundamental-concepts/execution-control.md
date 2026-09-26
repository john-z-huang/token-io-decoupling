# Coding Execution Control

[English](execution-control.md) | [简体中文](execution-control_zh_cn.md)

This module owns Interaction Slice control: slice release fields, boundary behavior, and Control Checkpoint choices. It assumes that planning, decision gates, stage feedback, role/session context, runtime capabilities, context transport, and delegation lifecycle are supplied by their owning concepts. It does not define those policies.

## General rules

### Interaction Slice

Release one **Interaction Slice** at a time for non-simple work. Every slice states:

- `Objective`: the result it must produce;
- `Authorized scope/mutations`: paths, behavior, and writes allowed;
- `Return conditions`: the evidence or milestone that ends it;
- `Unreleased boundary`: the next subsystem, risk domain, semantic choice, or mutation that remains blocked.

A slice is a control unit, not a command-by-command script. The executor may continue through low-decision-density mechanics while the Contract and boundary remain unchanged. It must pause at the return conditions or before crossing the unreleased boundary. A simple fast-path task may remain one slice through implementation and focused checks.

### Slice ordering

Release slices in parallel only when they are independent and non-conflicting. Dependencies, shared write targets, or ordered results require sequential release. Context transport and parent-only feedback follow their respective owner protocols and are not defined here.

### Control Checkpoint

At a material boundary, consume the Progress Signal owned by [execution stage feedback](execution-stage-feedback.md), append the current `Unreleased boundary`, and make one final control choice: `Continue`, `Amend`, or `Stop`. `Continue` releases only the next bounded slice; `Amend` changes the Contract or boundary before work resumes. `Evidence-on-Demand` is an intermediate evidence request that pauses release and returns to this checkpoint; it is not a fourth final authorization outcome. In a Single-Agent route, this is an internal reasoning pause, not a simulated self-message.

## Codex CLI / ChatGPT Desktop optimizations

Where enabled, Codex `PreToolUse` can deny a supported `Bash`, edit, or MCP call before it executes; `PostToolUse` is observation **after** the call. Codex's plan/read-only or other permission modes are tool controls, not this Skill's `Continue` decision. Coverage has exceptions, so do not use a hook as the only proof of a filesystem or semantic authorization boundary. [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks).

### Native approvals and focused review

Before relying on a non-managed Codex hook, inspect and trust its exact definition; in a CLI session that exposes it, run `/hooks` to review or trust configured hooks. A `PreToolUse` command hook denies a supported local call by writing this JSON to stdout:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Explain the blocked operation."
  }
}
```

For this event, `continue: false` is unsupported and the tool call continues after the hook error; `PostToolUse` runs after the effect and cannot retroactively approve it. At a stage boundary, an Agent must inspect the actual working-tree diff with an authorized read-only diff tool, or invoke `/diff` in a Codex CLI session that exposes the command. `/diff` includes staged, unstaged, and untracked changes. The parent still makes the semantic `Continue`/`Amend`/`Stop` choice under the general rules. [OpenAI: PreToolUse output contract](https://learn.chatgpt.com/docs/hooks), [OpenAI: code review](https://learn.chatgpt.com/docs/code-review), [OpenAI: CLI diff](https://learn.chatgpt.com/docs/developer-commands).

## Claude Code CLI / Claude Desktop optimizations

### Tool-boundary guard versus semantic Control

An authorized Claude Code `PreToolUse` hook runs after tool parameters are formed and before the call. It receives JSON on stdin with `tool_name`, `tool_input`, and `tool_use_id`; the hook group's `matcher` filters `tool_name`. To deny a call, write this JSON to stdout:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Explain the blocked operation."
  }
}
```

Exit code 0 with no output leaves the normal permission flow in place; it does not approve the call. A `Stop` hook can request a final evidence check before the current agent finishes. These are *guards*, not an alternate authority for deciding `Continue`, `Amend`, or `Stop`: the parent must still consume the Progress Signal and authorize each new slice under the general rules. Hook decisions or an MCP connector must not silently enlarge the Contract or child budget. Use native Hooks only in a Claude Code runtime where they are actually exposed and authorized.

Official reference: [Claude Code Hooks and decisions](https://code.claude.com/docs/en/hooks).

In Claude Code, `PostToolUse` reports observations after an action; it cannot authorize that action retroactively. [Anthropic: hooks](https://code.claude.com/docs/en/hooks).

## Related concepts

- [Coding Execution Planning](execution-planning.md) — locate bounded planning and reconnaissance-to-implementation relations.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate Decision Brief and decision-release rules.
- [Coding Execution Stage Feedback](execution-stage-feedback.md) — locate bounded-stage feedback rules.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate delegation lifecycle ownership for released slices.
