# Workflow Rule Context

[English](rule-context.md) | [简体中文](rule-context_zh_cn.md)

This owner defines bounded navigation to current workflow rules. It does not own structural checkpoint evaluation, the underlying rule, caller identity, or work authorization.

## General rules

### Read only the needed rule context

Use the current workflow owner as the authority. A registry or bounded excerpt can help locate the applicable heading, but its presence, hash, or completeness does not prove that the full task context was read or that a checkpoint passed. If a decision depends on a directly linked owner not included in the returned material, read that owner separately in the same language. Never infer missing policy from an index, excerpt, stale snapshot, or hash.

Keep navigation bounded to the current judgment. Do not scan the whole repository or treat linked references as recursively loaded. Missing required content or an incomplete result means the caller must obtain the authoritative owner directly; if it is unavailable, block only the dependent judgment. Record `Not applicable` with a reason when navigation is unnecessary.


## Codex CLI / ChatGPT Desktop optimizations

Use `rules_get_context` to locate the current registered rule context when useful, then verify any uncovered direct owner. Tool discovery does not establish identity or authority.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific rule-context optimization. Follow the general rules and use only capabilities actually exposed to the current Session; maintain equivalent evidence directly from authoritative owners.

## Related concepts

- [Workflow Navigation Availability](navigation-availability.md) — owns the unavailable-navigation branch.
- [Checkpoint Structural Checks](checkpoint-structure-checks.md) — owns deterministic evaluation of caller-supplied checkpoint facts.
- [Workflow Routing Advice](../execution-planning/workflow-routing-advice.md) — owns optional stage suggestions.
- [Coding Execution Control](../execution-control/execution-control.md) — owns Slice and Control decisions.
- [Coding Delegation State Record](../delegation/delegation-state-record.md) — owns the canonical parent-controlled workflow record.
