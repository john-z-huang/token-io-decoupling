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

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Execution Control](execution-control.md) — locate Interaction Slice boundaries.
- [Coding Execution Planning](execution-planning.md) — locate bounded plan and stage outline ownership.
- [Coding Execution Decision Gate](execution-decision-gate.md) — locate high-value decision conditions.
