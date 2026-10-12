# Planning Intent Plan Memory Lifecycle

[English](planning-intent-plan-memory-lifecycle.md) | [简体中文](planning-intent-plan-memory-lifecycle_zh_cn.md)

This owner defines persistence and lifecycle for concise, task-specific plan Memories when the user’s instruction makes planning, exploration, or producing/updating a plan an explicit task goal. A dedicated planning mode is optional. Incidental mentions of planning, exploration, or plans do not trigger this lifecycle. Ordinary two-level execution outlines and live task-record notes are not Memory plan documents; this owner does not define planning methods, decisions, execution authorization, or authoritative repository documentation.

## General rules

### Scope and trigger

Trigger this lifecycle from user intent: the instruction must make planning, exploration, or producing/updating a plan a task goal. Incidental mentions do not count. A dedicated planning mode may help draft the plan but is not required. Ordinary two-level execution outlines and live task-record notes do not trigger Memory plan creation or archiving.

### Names and storage

Use `plans/PLAN-[short-english-summary]` for an active plan and `archive-plans/PLAN-[short-english-summary]` for its archived form. Do not include `.md` in the Memory name. Serena maps names beneath its configured project data directory; by default the actual files are `<project-root>/.serena/memories/plans/PLAN-[short-english-summary].md` and `<project-root>/.serena/memories/archive-plans/PLAN-[short-english-summary].md`. Follow any configured project data-directory override.

Before creating or updating a plan, use `list_memories` and `read_memory` to check for an existing name and read its contents. Update an active plan only when it represents the same ongoing/incomplete task; otherwise choose a distinct short English summary to avoid collision. Use `write_memory` or `edit_memory` to persist a concise synthesized plan, then use `read_memory` to verify the stored content. Before archiving, check that the target archive name is absent. If it already exists, preserve the immutable archive, report the collision, and do not rename, replace, or overwrite it.

### Archive and immutability

When a user-intent trigger applies, create or update the active plan for that same task; keep it in `plans/` while the task is ongoing or incomplete. At acceptance, archive only the active plan Memory that belongs to the same task being completed; never archive an unrelated active plan. Only after that task is complete, move the plan to the matching `archive-plans/` name with `rename_memory`, then use `list_memories` and `read_memory` to verify that the active name is absent and the archive entry exists with the expected content. Existing archived plans are instruction-level immutable: do not edit, delete, rename, or replace them. Serena does not technically enforce this immutability; follow the rule when using exposed Memory tools.

### Content and boundaries

Store only a concise synthesized plan and its useful stage/evidence outline. Do not store secrets, transcripts, private reasoning, or live parent mode/count/allocation/epoch state. Planning method and reconnaissance ordering belong to [Coding Execution Planning](execution-planning.md); project knowledge, Memory capability, and source/context boundaries belong to [Serena LSP and MCP Tools](LSP-MCP-Tools.md) and [Coding Session Context Firewall](session-context-firewall.md). Serena Memory is the persistence mechanism; never fall back to filesystem files when the required Memory tools are unavailable.

## Codex CLI / ChatGPT Desktop optimizations

When user intent triggers this lifecycle, persist the concise synthesized plan using `list_memories`, `read_memory`, `write_memory`, `edit_memory`, and `rename_memory` as applicable, only when these Serena Memory tools are exposed and authorized in the current Session: list/read before writing, then write or edit the active name and read it back. Codex `/plan` is an optional drafting path; do not treat its transcript as the plan Memory. If required Memory tools or permission are unavailable, report the limitation and block dependent persistence; do not use a filesystem fallback. A tool's visibility alone does not authorize source or Memory changes. [OpenAI: Mastering Codex remote for engineering](https://developers.openai.com/blog/mastering-codex-remote-for-engineering).

## Claude Code CLI / Claude Desktop optimizations

Claude Code `plan` permission mode reads files and runs read-only exploration but does not edit source files. When user intent triggers this lifecycle, persist the plan only if the current Session exposes the needed Serena MCP Memory tools and effective permissions allow each call. Claude Code `plan` mode is an optional drafting path; it is not a trigger requirement. Verify the actual tool and permission; if unavailable, report the limitation and block dependent persistence. Do not bypass permission controls or fall back to filesystem storage. Claude Desktop Agents follow the same actual-tool-and-permission rule.

Official reference: [Claude Code permissions and permission modes](https://code.claude.com/docs/en/permissions).

## Related concepts

- [Coding Execution Planning](execution-planning.md) — locate planning methods and reconnaissance ordering.
- [Serena LSP and MCP Tools](LSP-MCP-Tools.md) — locate Memory operations and project boundaries.
- [Coding Session Context Firewall](session-context-firewall.md) — locate bounded context ingress.
