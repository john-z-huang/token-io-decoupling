# Coding Output Token Routing

[English](output-token-routing.md) | [简体中文](output-token-routing_zh_cn.md)

This module owns the independent decision about whether Root's direct output would be large in Output Token terms and the resulting Root-versus-child execution boundary. It does not select the executor or a specific child.

## General rules

### Independent output-size decision

Assess the requested output itself from the task, deliverable shape, and expected output volume. Do not use unrelated transcript size, an arbitrary numeric threshold, or a claim about measured token use. When evidence does not support a yes/no choice, stop for Root review.

An explicit user instruction about who should produce the output or whether it should be produced takes precedence over advice and skips the corresponding request. Use this independent assessment immediately before Root would produce each direct output whose shape or volume could be large, only when the user's instruction has not settled that output route. The assessment does not require a prior executor choice or an already available child; it evaluates the direct output itself. A `no` permits Root to produce the requested output subject to every other gate. A `yes` in an unresolved route means Root must not immediately materialize the large output: in Multi-Agent mode, select an already existing, idle, suitable current-session child; if none is idle, wait or hold until one is. This assessment never creates a child. In Single-Agent mode, do not invent a child or task-reframing route; hold and report that the requested output cannot proceed under the available Session topology.

When no explicit user instruction settles the route, the yes/no assessment is separate from executor selection. If a downstream advice request depends on a generated decision context that is missing or unusable, do not fabricate one or send the request anyway; Root may assess this owner directly from verified facts when they suffice, otherwise hold for review. A suggestion is advisory and cannot override an explicit user direction, dispatch work, or authorize an effect.

### Output-token Decisions instructions

If an explicit user execution instruction or output-route instruction settles the action, skip this advice and follow the instruction subject to higher-priority gates. Otherwise, decide whether the requested direct Root output would be large in Output Token terms. Use only the requested output shape, expected output volume, reviewed task context, current mode, and this owner's rules. Do not invent a numeric threshold or treat unrelated input size as a proxy. Choose `yes`, `no`, or `insufficient_evidence`. If the facts conflict, omit the requested output description, or cannot support a yes/no assessment, choose `insufficient_evidence` for Root review. A `yes` in an unresolved route does not imply that a child exists or is idle.

### Output-token choice descriptions

#### yes

The requested direct output would create a large Output Token burden for Root. When no explicit user instruction settles the route, Root must use an idle suitable current-session child or wait/hold. If the current mode is Single-Agent, hold and report the topology boundary; do not invent a child or task-reframing behavior.

#### no

The requested direct output is not large in Output Token terms under the supplied task facts. Root may execute only after checking all other applicable gates.

#### insufficient_evidence

The requested output shape, expected volume, or task evidence is too incomplete or conflicting to support a yes/no choice. Root reviews the facts and current owner; do not default to either yes or no.

### Action boundary

Before using advice, Root compares its fact, context, and policy hashes with current evidence and checks the current mode. After a `yes`, Root separately checks the selected child's current identity, suitability, permission, and idle availability before any dispatch. A busy child is not dispatch-ready. When no suitable idle child exists, retain a wait/hold state; do not create a child to satisfy this output route. Advice never changes an explicit user execution instruction.

## Codex CLI / ChatGPT Desktop optimizations

When exposed and the user has not explicitly settled the output route, call `workflow_assess_output_tokens` as a separate public Decisions request with bounded, current task facts and explicit per-call outbound permission. A `yes` routes to idle-child selection or wait/hold; a `no` permits Root to continue through the ordinary gates. The request does not perform either action and its result cannot override an explicit user instruction.

## Claude Code CLI / Claude Desktop optimizations

There are currently no concept-specific optimizations for this concept; follow the General rules.

## Related concepts

- [Task Assignment](task-assignment.md) — owns Root/child executor and current-child selection.
- [Session Model](session-model.md) — owns Session identity and topology semantics.
- [Delegation Count Gate](delegation-mode-count-gate.md) — owns locked child capacity and explicit expansion.
- [Delegation Mode Re-entry](delegation-mode-reentry.md) — owns fresh mode selection for a Fork.
- [Delegation State Record](delegation-state-record.md) — owns current allocation identity and status.
- [Decision Context Generation](decision-context-generation.md) — owns generation and review of bounded decision context.
