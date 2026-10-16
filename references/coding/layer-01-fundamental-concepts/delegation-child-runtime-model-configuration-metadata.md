# Coding Child Runtime Model Configuration Metadata

[English](delegation-child-runtime-model-configuration-metadata.md) | [简体中文](delegation-child-runtime-model-configuration-metadata_zh_cn.md)

This module owns the per-child runtime model configuration metadata record and its Serena project Memory lifecycle. It stores only the runtime branch, requested and effective model/reasoning controls, their verification evidence, and record status. It does not own task state, project findings, permissions, authorization, child creation, dispatch formatting, or lifecycle decisions.

## General rules

### Purpose and separation

Persist one model-configuration metadata record for every allocated Multi-Agent child. Its purpose is to make the child's model and reasoning controls recoverable after compaction, interruption, or resume without relying on compressed conversation history.

Keep this metadata separate from the parent task-control record, task prompts, content memos, handoff notes, and project knowledge. Do not store a task objective, Contract, source findings, progress, diff, permission grant, secret, or transcript. The parent task-control record remains authoritative for mode, count, allocation, Interaction Slice, scope, mutations, and lifecycle. This metadata never grants any of those.

### Memory name, ownership, and schema

The parent assigns one unique `run_id` to the delegation run and one stable `allocation_id` to each reserved child allocation. Use this exact Serena project Memory name and reference:

~~~text
memory_name: agent-session-context/<run-id>/<allocation-id>
reference: mem:agent-session-context/<run-id>/<allocation-id>
~~~

This is a named Serena Memory, not a workspace Markdown document. The parent owns the record and all writes. Before creating a child, verify that the parent has the required Serena Memory tools and that the configured child runtime is expected to expose access to the same project Memory namespace. After startup, the child must prove access by reading the exact Memory. Memory is not implicitly shared across Sessions. If child access cannot be established before startup, allow only a configuration-verification prompt and block task work until the child read succeeds. If either Session lacks a required read/write tool, block dependent child work; do not use filesystem or another-memory fallback.

For a new allocation, check the name with Serena `list_memories`; if a Memory already exists, read it and verify that it belongs to this exact `run_id` and `allocation_id` before updating it. Never overwrite a conflicting record. Write the initial record with Serena `write_memory`, using `memory_name="agent-session-context/<run-id>/<allocation-id>"` without the `mem:` prefix. Immediately call Serena `read_memory` with the same `memory_name` and verify the stored content. The parent task-control record stores only the `mem:` reference, never a copy of the metadata.

Use this minimal content:

~~~yaml
record_type: child-runtime-model-configuration
schema_version: 1
run_id: <unique delegation run identifier>
allocation_id: <stable parent allocation identifier>
runtime_branch: <verified supported branch>
requested_model: <exact model identifier or supported alias>
requested_reasoning_control: <parameter=value or not_supported>
effective_model: <verified model identifier or supported alias, otherwise unresolved>
effective_reasoning_control: <parameter=value, not_supported, or unresolved>
binding_evidence: <configuration source or runtime observation; no secrets>
verified_at: <timestamp or unresolved>
record_status: prepared | verified | blocked
~~~

Resolve supported models and controls through [Runtime and Model Provider Support](runtime-provider-support.md). Do not infer settings from the parent model, a role name, remembered context, or another allocation. Mark the record `verified` only after resolving all applicable precedence and overrides, or confirming the effective settings through live runtime evidence. If launch settings do not establish the child's effective values, leave them unresolved until the child reports a runtime observation; update the Memory with Serena `write_memory`, then read it back with Serena `read_memory` before releasing task work.

### Startup, compaction, and re-entry

Include the exact `mem:agent-session-context/<run-id>/<allocation-id>` reference in the child's initial prompt and every follow-up. A configuration-only startup prompt may ask the child to read the Memory and report the model configuration it can observe; it must not release task work while the record is unresolved. Before profile-gated work, the child calls Serena `read_memory` with the name without the `mem:` prefix and confirms the `run_id`, `allocation_id`, and `record_status: verified`. After compaction, interruption, or resume, use the verified values from this Memory; do not report a value as `unknown` merely because compressed history no longer contains it. Report a conflict only when the record belongs to another allocation or there is evidence that the effective runtime binding changed. The child reports conflicts to the parent and never writes or repairs this record.

After compaction, interruption, resume, or any follow-up to the same child, the parent reads the reference from its task-control record and includes it again in the actual message. The child calls Serena `read_memory` again before continuing or stating its settings, then uses the saved verified values instead of inferring them from compressed conversation history. A previously loaded summary or injected hook context does not prove that the current Memory was read.

If the Memory is missing, inaccessible, unresolved, or conflicts with live runtime evidence, stop dependent work. The parent may update the same allocation's Memory only after rechecking the active binding, then must read back and verify the updated content. Retain the record while the allocation can resume or receive follow-up. Do not delete it without explicit user authorization.

## Codex CLI / ChatGPT Desktop optimizations

For Local Codex, record the exact child `model` and `model_reasoning_effort` request and their resolved values. Codex resolves each setting from explicit spawn values, then `[agents]` defaults, then the parent; a matching custom agent file's `model` or `model_reasoning_effort` takes precedence over that resolution. If a model is explicitly selected without an effort, record the selected model's verified default effort, not an assumed parent value. Use only bindings allowed by [Runtime and Model Provider Support](runtime-provider-support.md).

Use only Serena Memory tools exposed and authorized in the current parent and child Sessions. Codex child Sessions do not implicitly share Serena Memory; verify the child can read this same project's Memory before releasing work. A configured `SubagentStart` hook can inject the `mem:` reference through `hookSpecificOutput.additionalContext`, but the hook event has no documented reasoning-effort field and `continue: false` does not prevent child creation. A `SessionStart` hook matching `source: "compact"` can add context to that Session's next request after compaction; it is optional and does not replace `read_memory` or prove that the child read the record. [OpenAI: subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks), [Serena Memory tools](LSP-MCP-Tools.md).

## Claude Code CLI / Claude Desktop optimizations

For Local Claude Code, record the exact `Agent` invocation `model` and `effort` controls or the custom subagent frontmatter values, then resolve the effective binding. The invocation model normally precedes frontmatter `model`, `CLAUDE_CODE_SUBAGENT_MODEL`, and the parent model, but an installed `agent.spawn` hook may replace the invocation value; aliases can resolve to another model or fall back when blocked. Frontmatter `effort` is overridden by the invocation `effort` parameter, while `CLAUDE_CODE_EFFORT_LEVEL` takes precedence over both. The invocation `effort` parameter requires Claude Code v2.1.292 or later. Use `/tasks` to verify the running subagent model and effort when supported (display requires v2.1.242 or later). Use only bindings allowed by [Runtime and Model Provider Support](runtime-provider-support.md).

Discover and verify Serena Memory tools in both the parent and child Sessions; Claude Code does not implicitly share a project's Serena Memory with another Session. Before releasing task work, require the child to read this exact Memory with the exposed Serena `read_memory` tool. A configured `SubagentStart` hook can inject the `mem:` reference through `hookSpecificOutput.additionalContext`, including after auto-compaction removes an earlier injection, but the hook cannot veto child creation and does not replace the Memory read. `SessionStart` may omit `model` during recovery, so verify that field exists before using it as evidence. [Anthropic: hooks](https://code.claude.com/docs/en/hooks), [Anthropic: subagents](https://code.claude.com/docs/en/sub-agents), [Serena Memory tools](LSP-MCP-Tools.md).

## Related concepts

- [Coding Delegation State Record](delegation-state-record.md) — locate the parent-owned run, allocation, and Memory reference.
- [Coding Child Creation](delegation-child-creation.md) — locate pre-creation persistence and verification requirements.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate the prompt reference and child-read boundary.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate follow-up and resume boundaries.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child identity and lifecycle state.
- [Coding Session Model](session-model.md) — locate Session semantics.
- [Runtime and Model Provider Support](runtime-provider-support.md) — locate runtime bindings and profile verification.
- [Serena LSP and MCP Tools](LSP-MCP-Tools.md) — locate Serena Memory tool availability and semantics.
