# Coding Child Dispatch

[English](delegation-child-dispatch.md) | [简体中文](delegation-child-dispatch_zh_cn.md)

This module owns material Dispatch Preview and the Worker boundary. It consumes an already authorized child and slice; it does not define child creation, role allocation, reuse or replacement, lifecycle, or Interaction Slice fields.

## General rules

### Dispatch Preview and return boundary

Before assigning or materially dispatching to a child, verify that Input-side Reasoning has completed its prerequisite instruction, environment, and task-defining code-fact confirmations with source pointers, and that a concrete Interaction Slice was released. The parent shows a concise Dispatch Preview of the authorized objective, mutations, and return conditions; a missing prerequisite keeps the slice with the parent. A Worker returns only to its direct parent and cannot create, fork, hand off to, message, replace, or coordinate another Agent or Session, or contact arbitrary threads. Contradictory findings return to the parent for a new decision, not a new mode or count.

### Named paths and slice release

Check each Worker's named-path and directory permissions under [context workspace boundary](context-exchange-workspace-boundary.md); consume the released Interaction Slice under [execution control](execution-control.md). Dispatch one slice at a time unless independent, non-conflicting parallel work is explicitly allowed. Do not redefine directory layout or slice fields here.

## Codex CLI / ChatGPT Desktop optimizations

Codex custom agents can hold role-specific `developer_instructions`; the parent still sends the released objective, named sources, scope, and return conditions through the actual child-task invocation. An `AGENTS.md` file may contribute repository instructions but does not replace this task-specific bundle. If Codex hooks are configured, `SubagentStart` can add small context, but cannot prevent child creation and must not silently expand the authorized slice. [OpenAI: subagent profiles](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: SubagentStart](https://learn.chatgpt.com/docs/hooks).

### Observable dispatch and pre-spawn guard

In interactive Codex CLI, the parent may use `/agent` to inspect the selected Agent thread, but the command is a navigation aid rather than the Dispatch Preview. In ChatGPT Desktop's Codex view, open the subagent thread to inspect its work and the summary returned to the main chat. Before the real spawn, keep the brief task instruction in the parent turn and put objective, authorized paths, source pointers, explicit `write_content_memo` and return conditions in the child's actual task prompt. If a reviewed `PreToolUse` hook matches `spawn_agent`/`Agent`, it can deny a tool invocation missing a released slice; `SubagentStart` is too late to veto creation. Check installed hook trust and coverage rather than claiming this guard exists by default. [OpenAI: subagent surfaces](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: hook tool coverage](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

### Pre-dispatch tool guard

For a locally configured Claude Code host, an authorized `PreToolUse` Hook matching `Agent` may inspect the proposed invocation before it executes and deny a spawn when the parent record does not show the reserved slot, released slice, and approved return path. Use an explicit deny result rather than relying on a `SubagentStart` event, which occurs after spawn and cannot veto it. Keep the human-readable Dispatch Preview in the parent conversation **before** the `Agent` tool call; a Hook alone is not evidence that the parent reviewed or exposed the preview. Guard scripts must read the actual record and fail closed on missing authorization without logging secrets or full prompts. If no reviewed Hook is installed, the semantic pre-dispatch checks remain mandatory.

Official reference: [PreToolUse and SubagentStart semantics](https://code.claude.com/docs/en/hooks).

A Claude Code custom subagent starts with its own context and does not automatically inherit the parent's full conversation history or previously invoked Skills. Put the released objective, limited source pointers and return conditions in the actual `Agent` task prompt. The `skills` frontmatter preloads the **entire named Skill** into that child, so configure it only if the role needs it rather than treating it as a selective concept-loading mechanism. Keep any exposed `SendMessage`/peer control out of Worker tools, preserving authorized parent-to-child follow-up. [Anthropic: subagent context and skills](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state and recovery ownership.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Context Exchange](context-exchange.md) — locate named-path context transport ownership.
- [Coding Execution Control](execution-control.md) — locate Interaction Slice boundary controls.
