# Workflow Rule Context

[English](rule-context.md) | [简体中文](rule-context_zh_cn.md)

This owner defines delivery and bounded consumption of current compiled workflow instructions. It does not own structural checkpoint evaluation, the underlying policy, caller identity, or work authorization.

## General rules

### Consume the current executable instruction

Author owners are the development-time policy source. During execution consume the current step's complete compiled instruction, not author filenames or excerpts that require reconstructing policy. An explicit instruction continuation identifies the next independent unit to obtain before its dependent action; preserve the suspended action and reuse already held units only when their build and language still match. A resource identity, hash or completeness result never proves task facts or checkpoint completion.

Keep consumption bounded to the current judgment. Do not scan the repository or follow original owner links. Resolve only the explicit continuation needed by the current action. Missing, corrupt, incompatible or mixed-build instruction resources block dependent work; do not fall back to author Markdown or infer omitted policy. A same-build generated document-only Skill may supply the corresponding compiled unit when an authorized document path is selected. Record `Not applicable` with a reason when optional navigation is unnecessary.


## Codex CLI / ChatGPT Desktop optimizations

Use `rules_get_context` with `context_version: 2`, the registered `node_id`, one language and any explicit compiled `fragment_ids` requested by the current continuation. Review returned instruction text, build identity, unresolved facts and failure status; a budget failure never permits partial execution. Tool discovery does not establish identity or authority. The server supports local Codex CLI only under its client boundary.

## Claude Code CLI / Claude Desktop optimizations

This project's MCP server has no supported direct Claude counterpart. Mark that MCP optimization `Not applicable` and use the same-build generated document-only Skill's explicit instruction units through actually exposed, authorized document capabilities. This does not add another MCP client or permit author-source fallback. Follow the general evidence and failure boundaries.

## Related concepts

- [Workflow Navigation Availability](navigation-availability.md) — owns the unavailable-navigation branch.
- [Checkpoint Structural Checks](checkpoint-structure-checks.md) — owns deterministic evaluation of caller-supplied checkpoint facts.
- [Workflow Routing Advice](../execution-planning/workflow-routing-advice.md) — owns optional stage suggestions.
- [Coding Execution Control](../execution-control/execution-control.md) — owns Slice and Control decisions.
- [Coding Delegation State Record](../delegation/delegation-state-record.md) — owns the canonical parent-controlled workflow record.
