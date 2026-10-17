# Coding Child Runtime Model Configuration Metadata

[English](delegation-child-runtime-model-configuration-metadata.md) | [简体中文](delegation-child-runtime-model-configuration-metadata_zh_cn.md)

This module owns the per-child runtime model configuration metadata record and its Serena project Memory lifecycle. It stores only the runtime branch, requested and effective model/reasoning controls, their verification evidence, and record status. It does not own task state, project findings, permissions, authorization, child creation, dispatch formatting, or lifecycle decisions.

## General rules

### Purpose, timing, and ownership

Model and reasoning-effort binding checks are permitted only as part of creating a child. The parent must select and set the role-required model and effort in the child-creation operation, applying the supported runtime bindings. Block creation if the operation cannot set or establish these required controls. If the operation accepts the required controls but exposes no additional runtime-resolved observation, that optional observation may be recorded as unresolved and task work may proceed. The child must never inspect, read, or report its own model or effort, at startup or later.

After creation, any per-child metadata record is parent-owned informational audit data. It may document creation inputs and the evidence available at that time, but it does not gate startup, task work, dispatch, follow-up, repair, compaction, wake, or resume. The parent does not re-check or require confirmation of model/effort in any later operation on that child. Metadata does not grant task scope, permissions, authorization, or lifecycle state.

### Optional metadata record

If the parent maintains this record as part of child creation, store it in Serena project Memory under the stable run and allocation identifiers:

~~~text
memory_name: agent-session-context/<run-id>/<allocation-id>
reference: mem:agent-session-context/<run-id>/<allocation-id>
~~~

The parent owns the record and all writes. Memory is optional audit storage, not a prerequisite for creating the child or releasing work. Do not include the Memory reference in child prompts or ask the child to read it. If available, parent-side readback may confirm the audit record was saved; missing or unavailable metadata never blocks the child.

~~~yaml
record_type: child-runtime-model-configuration
schema_version: 1
run_id: <delegation run identifier>
allocation_id: <parent allocation identifier>
runtime_branch: <supported branch used at creation>
requested_model: <exact model identifier or supported alias>
requested_reasoning_control: <parameter=value or not_supported>
effective_model: <resolved value or unresolved>
effective_reasoning_control: <resolved value, not_supported, or unresolved>
binding_evidence: <parent-controlled creation configuration or runtime evidence; no secrets>
recorded_at: <timestamp>
record_status: informational | unavailable
~~~

Resolve supported models and controls through [Runtime and Model Provider Support](runtime-provider-support.md). Do not infer settings from a role name or another allocation. The required model and effort must be set or established by the creation operation; unresolved metadata cannot substitute for this requirement. If that operation accepted the required controls but provides no additional runtime-resolved observation, retain the observation as `unresolved` informational metadata and proceed with task work. This does not authorize a later child-side check and does not gate work. Keep any audit record while useful; deletion follows the applicable user authorization and data-retention rules.

## Codex CLI / ChatGPT Desktop optimizations

For Local Codex, the parent must set the role-required model and effort in the creation operation, applying explicit spawn values and applicable profile/runtime precedence. Block creation if required controls cannot be set or established. If the operation accepts them but exposes no additional runtime-resolved observation, that observation may remain unresolved. Record the parent-accessible creation evidence. Do not ask the child to inspect `/agent`, `/status`, Memory, or any other source to report model or `model_reasoning_effort`. Serena Memory hooks and compaction context do not change this boundary. [OpenAI: subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks), [Serena Memory tools](LSP-MCP-Tools.md).

## Claude Code CLI / Claude Desktop optimizations

For Local Claude Code, the parent must set the role-required model and effort through the creation operation, applying `Agent` controls, custom-subagent frontmatter, environment overrides, and applicable hooks. Block creation if required controls cannot be set or established. If the operation accepts them but exposes no additional runtime-resolved observation, that observation may remain unresolved. Record only parent-accessible creation evidence. Do not ask the child to inspect `/tasks`, Session fields, Memory, or any other source to report model or effort. A later resume or `SessionStart` event is not a reason to re-check these settings. [Anthropic: hooks](https://code.claude.com/docs/en/hooks), [Anthropic: subagents](https://code.claude.com/docs/en/sub-agents), [Serena Memory tools](LSP-MCP-Tools.md).

## Related concepts

- [Coding Delegation State Record](delegation-state-record.md) — locate the parent-owned run/allocation identifiers and task-control record.
- [Coding Child Creation](delegation-child-creation.md) — locate the required creation-time model/effort settings; audit metadata is optional.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate the dispatch boundary: it does not read or verify this metadata.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate follow-up and resume boundaries.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child identity and lifecycle state.
- [Coding Session Model](session-model.md) — locate Session semantics.
- [Runtime and Model Provider Support](runtime-provider-support.md) — locate runtime bindings and profile verification.
- [Serena LSP and MCP Tools](LSP-MCP-Tools.md) — locate Serena Memory tool availability and semantics.
