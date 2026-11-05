# Workflow Navigation Availability

[English](navigation-availability.md) | [简体中文](navigation-availability_zh_cn.md)

This owner defines how to proceed when optional workflow navigation or structural checking is unavailable. It does not own policy, caller identity, permissions, or checkpoint results.

## General rules

The workflow's current owner documents remain authoritative. Navigation tools and their registries are optional aids for locating bounded current rule text and checking supplied input structure. Their availability does not establish runtime identity, capability for protected operations, permission, or workflow state.

If navigation is unavailable or incomplete, read the relevant authoritative owner directly when its source is available through the current Session's authorized capabilities. Keep the reading bounded to the current judgment. If a required owner cannot be obtained, block only work that depends on it; do not infer its policy or skip the requirement. If optional navigation is not needed, record `Not applicable` with the reason.

Stateless structural checks cannot substitute for direct-owner review, evidence interpretation, authorization, Slice release, Control, verification, or acceptance. They do not retain a canonical workflow state, establish cross-call order, or turn caller-supplied hashes into proof.

## Codex CLI / ChatGPT Desktop optimizations

When `rules_get_context` or a structural evaluation tool is unavailable, continue by reading the current owner documents directly if that content is accessible; record the limitation. If the authoritative owner is unavailable, block the dependent judgment. Do not select an alternate persisted workflow backend or assume the unavailable result is a pass.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific navigation optimization. Follow the general rules using capabilities actually exposed to the current Session.

## Related concepts

- [Workflow Rule Context](rule-context.md) — owns bounded rule navigation.
- [Checkpoint Structural Checks](checkpoint-structure-checks.md) — owns optional structural checks over supplied facts.
- [Coding Execution Control](../execution-control/execution-control.md) — owns authorization boundaries for Slice and Control.
