# Workflow Navigation Availability

[English](navigation-availability.md) | [简体中文](navigation-availability_zh_cn.md)

This owner defines how to proceed when optional workflow navigation or structural checking is unavailable. It does not own policy, caller identity, permissions, or checkpoint results.

## General rules

Author owners remain the development-time policy authority; execution consumes their approved compiled instructions. Optional navigation selects bounded instruction units and structural checks inspect supplied input. Their availability does not establish runtime identity, protected-operation capability, permission, or workflow state.

When optional navigation is unavailable, an already available, authorized same-build generated document-only instruction surface may supply the explicit current unit. This is an alternative delivery surface, not author-source fallback. Missing, incomplete, corrupt or incompatible required instruction resources block dependent work; do not search author documents, infer policy or skip requirements. When optional navigation is unnecessary, record `Not applicable` with the reason and consume the corresponding delivered instruction directly.

Stateless structural checks cannot substitute for compiled-instruction review, evidence interpretation, authorization, Slice release, Control, verification, or acceptance. They do not retain canonical workflow state, establish cross-call order, or turn supplied hashes into proof.

## Codex CLI / ChatGPT Desktop optimizations

When `rules_get_context` is unavailable, use only an actually available and authorized same-build generated document-only Skill, retaining explicit unit identity and continuation position. Resource errors block the affected path instead of enabling source fallback. Structural evaluation remains optional unless independently required. Do not invent an alternate persisted workflow backend or treat an unavailable result as a pass.

## Claude Code CLI / Claude Desktop optimizations

There is no supported direct Claude client for this project's MCP server. Use the generated document-only Skill through actually available, authorized document capabilities and follow the general same-build and failure checks; the MCP optimization is `Not applicable`.

## Related concepts

- [Workflow Rule Context](rule-context.md) — owns bounded rule navigation.
- [Checkpoint Structural Checks](checkpoint-structure-checks.md) — owns optional structural checks over supplied facts.
- [Coding Execution Control](../execution-control/execution-control.md) — owns authorization boundaries for Slice and Control.
