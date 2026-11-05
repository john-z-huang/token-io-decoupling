# Workflow Routing Advice

[English](workflow-routing-advice.md) | [简体中文](workflow-routing-advice_zh_cn.md)

This owner defines optional task-level advice for locating the current checkpoint within an already authorized Coding route. It does not own route policy, readiness, mode selection, permission, or execution.

## General rules

### Advice stays advisory

Use this concept only to suggest the current stage or module from reviewed task facts and the locked route. The Coding workflow and selected route remain authoritative for stage order, checkpoint actions, evidence, branches, and acceptance. A suggestion never passes a checkpoint, changes the locked mode or child count, grants permission, creates or dispatches an agent, or calls another tool.

An explicit stage may be mapped locally when the current route and rules are available. Automatic stage selection is optional and may use a semantic decision only when the necessary source facts, current rule context, capability, and outbound-data authorization are available. If facts or rules are missing, stale, over budget, or contradictory, return to direct judgment using the current route owner. Do not turn missing evidence into an assumed stage.

Review the suggested stage against the current route and task state before acting. Treat hashes as change detectors, not source authentication or permission evidence. Refresh advice after relevant facts, route, or rules change. When the optional advice capability is unavailable, record that result. Continue only if an independently authorized Native/direct path applies; if a capability required by the selected path is missing, stop at its owner-defined boundary rather than silently falling back.

### Route boundary

The stage-to-module correspondence is owned by the current Single-Agent or Multi-Agent route. Advice may identify the matching module only after the mode/count is locked. Multi-Agent execution reminders do not replace role, task authorization, memo, Slice, and child lifecycle owners. Verification, repair, documentation, Git, and acceptance remain governed by their direct owners.

## Codex CLI / ChatGPT Desktop optimizations

When the capability is exposed and authorized, `decide_decoupling_workflow` accepts a bounded request under `payload.request`. The schema requires `mode_locked: true` and the canonical `mode_count`, along with all other required fields and bounded caller-supplied evidence; `stage` is `auto` or an explicit supported stage. `source_facts_hash` must match the supplied facts. Populate the complete current schema, including task identifiers and summary, language, capability and constraint records, source-fact references, and outbound-data assertion where applicable; this summary is not an exhaustive payload field list. Explicit stages are resolved locally after bounded rule checks. `auto` may make one Decisions request only when source facts are present, outbound data is permitted, and the configured capability allows it. The tool reloads relevant context and rechecks hashes before returning compact advice.

Only an `available` result is a suggestion; `insufficient_evidence`, `blocked`, and `stale` require direct review or refreshed facts/rules. Returned hashes do not cover the full Layer-04 route or prove it is unchanged; directly read the current selected route before acting. The result does not repeat full rules. The call is stateless and does not perform workflow actions. API failures are bounded and do not expose credentials or raw provider errors. Runtime/model and effort bindings remain in [Runtime and Model Provider Support](../session-runtime/runtime-provider-support.md).

## Claude Code CLI / Claude Desktop optimizations

This repository's MCP Server supports local Codex CLI only. Claude's general MCP support does not make this server a supported direct client, and there is no Claude-specific direct-tool optimization for this owner. Follow the general rules using capabilities actually exposed and authorized in the current Session; otherwise mark this optional advice unavailable and use the authoritative route directly.

## Related concepts

- [Coding Execution Decision Gate](execution-decision-gate.md) — owns execution decision prerequisites.
- [Task Assignment](task-assignment.md) — owns executor selection.
- [Workflow Rule Context](../workflow-navigation/rule-context.md) — owns bounded rule retrieval and completeness.
