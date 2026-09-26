# Coding Execution Stage Feedback

[English](execution-stage-feedback.md) | [简体中文](execution-stage-feedback_zh_cn.md)

This module defines bounded stages, Progress Signals, and the stage-internal use of Decision Checkpoints. It does not define the Decision Brief, solution selection, Contract updates, Interaction Slice fields, role/session semantics, context transport, or delegation lifecycle.

## General rules

### Bounded stages

For high-uncertainty work, predeclare a short sequence of evidence-producing stages. Each stage ends at an observation or decision boundary, not a command list.

### Progress Signals and stage feedback

At a declared stage boundary, return only the compressed progress signals needed for the next decision: material status, findings, changed scope, verification, issue, and need. Keep ordinary reads, local edits, formatter/lint fixes, straightforward test repairs, and repeated compile/test cycles inside the approved stage. Do not add checkpoints or execution slices merely to report low-value mechanics.

When stage evidence shows that the next stage depends on high-value judgment, route the signal to the Decision Gate. The Decision Gate owns solution selection and Contract updates; this module does not restate those policies.

## Codex CLI / ChatGPT Desktop optimizations

A configured Codex `PostToolUse` or `SubagentStop` hook can supply observed tool or child results for the parent's compressed Progress Signal, while `PreCompact` can mark a pending context-loss boundary. These optional events never prove semantic acceptance and must not trigger a full tool-log or transcript dump. [OpenAI: tool and lifecycle hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

### Hook-assisted compact stage evidence

For a persistent Claude Code child, `SubagentStop` exposes `last_assistant_message`, allowing the parent to consume a short stage result without replaying the child transcript. When a tool execution itself fails, `PostToolUseFailure` can expose its error information for the executor to report at the *existing* stage boundary; do not convert every failed command into a new high-value decision checkpoint. Neither event substitutes for explicit progress evidence, final verification, or the parent Control choice. Use native Hooks only where installed in the current Claude Code runtime, not in an unrelated Desktop Chat conversation.

Official reference: [SubagentStop and PostToolUseFailure event data](https://code.claude.com/docs/en/hooks).

A configured `PostToolUse` can provide actual tool outcomes at a stage boundary but cannot replace the compressed Progress Signal. Desktop Code diff review is evidence of changed lines, not proof of tests or independent verification. [Anthropic: hooks](https://code.claude.com/docs/en/hooks), [Anthropic: Desktop diff review](https://code.claude.com/docs/en/desktop).

## Related concepts

- [Coding Execution Control](execution-control.md) — locate Interaction Slice boundaries.
- [Coding Execution Planning](execution-planning.md) — locate bounded plan and stage outline ownership.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate high-value decision conditions.
