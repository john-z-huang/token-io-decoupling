# Serena LSP and MCP Tools

[English](LSP-MCP-Tools.md) | [简体中文](LSP-MCP-Tools_zh_cn.md)

This owner defines how a Coding Agent uses Serena MCP to navigate code through the active language server and to read or write durable, reusable Agent-facing project knowledge. It does not define authoritative repository-documentation storage or live parent mode/count/allocation/epoch state; Worker memos and Context Exchange records use project Memory under their respective owners.

## General rules

### Activate the project and inspect code structurally

Activate Serena with the exact project root before querying code. The root must be the directory Serena should treat as the project, not an arbitrary nested source folder. Confirm that the intended project is active and that its language server for the relevant language is available. A worktree or a monorepo subproject may require activating its own root.

When first exploring an unfamiliar code file, call `get_symbols_overview` first. Then use the narrowest relevant symbol operation:

- `find_symbol` to locate a class, function, method, or other code entity; request its body only when the implementation is needed.
- `find_declaration` to resolve a declaration from a known use site.
- `find_referencing_symbols` to find callers or other references to a symbol.
- `find_implementations` to locate implementations of an interface or abstract symbol.

Limit each query to the known file or directory when possible, bound result size and match count, and preserve exact paths and symbol names as source pointers. Use `search_for_pattern` only to discover candidate files or text matches; verify code relationships and candidate symbols with the language server before treating them as structural evidence. A text match alone does not establish a declaration, reference, implementation, or call relationship.

If Serena, the relevant language server, or a required LSP operation is unavailable or does not support the needed semantics, state that limitation and fall back to targeted text search and small, path-bounded reads. Do not describe fallback findings as LSP evidence. Keep reads within the authorized project and task scope.

### Read and write durable project memories

For reusable Agent-facing project knowledge, first call `list_memories` and use the returned names to identify relevant notes; then call `read_memory` for the relevant memories before relying on them. Follow the effective memory-maintenance name Serena supplies when available. Use `write_memory` for stable, non-obvious project knowledge that will help future tasks, and for cross-session notes the user explicitly asks to preserve. Keep memories concise, factual, and linked to authoritative source paths where useful.

Serena's default project data directory is `.serena`; project memories are stored under `.serena/memories/`. A memory name such as `architecture/services` maps to `.serena/memories/architecture/services.md`: slash-separated segments create topic subdirectories and Serena supplies the `.md` extension. If project configuration changes the data directory, follow that configured location. Use the `global/` name prefix only when the user explicitly requests a cross-project memory. When preserving an existing Skill's document names and subdirectory intent as memories, use the corresponding basename and slash-separated directory segments as the memory name.

Run onboarding only when Serena indicates that it has not been completed. Before invoking the onboarding tool, ask the user whether to proceed; if they do not authorize it, continue without onboarding. When authorized, follow its returned instructions and read the effective memory-maintenance name it supplies with `read_memory` before writing any onboarding notes. Serena's `ensure_memory_maintenance_memory` may select `global/memory_maintenance` as a configured override; otherwise it uses or creates the project `memory_maintenance` entry. Reading that configured guidance does not authorize writing cross-project memories: write under `global/` only when the user explicitly requests it. Then inspect only the project material needed and write the resulting durable notes with `write_memory`.

Memories are reusable Agent context, not authoritative copies of repository documentation. Do not move README files, normative specifications, or other source-of-truth documents into Memory as their replacement. Do not store secrets, full transcripts, private reasoning, or live parent mode/count/allocation/epoch state. Persist Worker execution memos and Context Exchange capsules/indexes/handoffs as project Memories under [Worker Content Memo](../context-exchange/content-memo.md), [Coding Context Exchange](../context-exchange/context-exchange.md), [Coding Context Exchange Workspace Boundary](../context-exchange/context-exchange-workspace-boundary.md), [Coding Context Exchange Handoff](../context-exchange/context-exchange-handoff.md), and [Session Context Firewall](session-context-firewall.md) when that owner authorizes a durable context record. A memory name expresses logical ownership only; Serena/tool visibility does not enforce Worker-level access isolation, read-only ACLs, or OS/RW/RO/DENY boundaries. Source code and authoritative repository files remain subject to their separately approved access boundaries.

## Codex CLI / ChatGPT Desktop optimizations

### Codex Serena MCP calls

In a Codex Session, invoke Serena only through the Serena MCP tools actually exposed to and authorized for that Session. The table lists the 24 Serena tools exposed in the current Codex Session; it is an observation, not a guarantee for other Sessions, and tool presence does not grant permission to call it. Call a tool by its exposed name and required arguments. If an LSP query operation is absent, report the limitation and use only an authorized bounded text-search/read fallback, without claiming LSP evidence. If `list_memories`, `read_memory`, or `write_memory` is absent for a required record, report the unavailable Memory capability and block dependent work; never fall back to file storage.


| Tool | Category | What it does |
| --- | --- | --- |
| `mcp__serena__activate_project` | Project and LSP query | Activates the selected project context. |
| `mcp__serena__delete_memory` | Memory change | Deletes a named Memory; call only with explicit task instruction and authorization. |
| `mcp__serena__edit_memory` | Memory change | Edits an existing named Memory. |
| `mcp__serena__find_declaration` | Code/LSP query | Finds a declaration from a known use site. |
| `mcp__serena__find_implementations` | Code/LSP query | Finds implementations of a symbol or interface. |
| `mcp__serena__find_referencing_symbols` | Code/LSP query | Finds symbols that reference the selected symbol. |
| `mcp__serena__find_symbol` | Code/LSP query | Locates a symbol and, when requested, its body. |
| `mcp__serena__get_current_config` | Runtime/workflow | Reports the current Serena configuration. |
| `mcp__serena__get_diagnostics_for_file` | Code/LSP query | Retrieves language-server diagnostics for a file. |
| `mcp__serena__get_symbols_overview` | Code/LSP query | Summarizes symbols in a code file. |
| `mcp__serena__initial_instructions` | Runtime/workflow | Provides Serena's initial usage instructions. |
| `mcp__serena__insert_after_symbol` | Source modification | Inserts content after a selected symbol. |
| `mcp__serena__insert_before_symbol` | Source modification | Inserts content before a selected symbol. |
| `mcp__serena__list_memories` | Memory read | Lists available Memory names. |
| `mcp__serena__onboarding` | Runtime/workflow | Runs project onboarding when it is incomplete and the user has authorized it. |
| `mcp__serena__open_dashboard` | Runtime/workflow | Opens the Serena Web dashboard. |
| `mcp__serena__read_memory` | Memory read | Reads the named Memory. |
| `mcp__serena__rename_memory` | Memory change | Renames a named Memory. |
| `mcp__serena__rename_symbol` | Source modification | Renames a code symbol. |
| `mcp__serena__replace_in_files` | Source modification | Replaces text in files and supports dry-run. |
| `mcp__serena__replace_symbol_body` | Source modification | Replaces the body of a symbol whose body has already been retrieved and understood. |
| `mcp__serena__safe_delete_symbol` | Source modification | Deletes a symbol if it has no references; otherwise returns the references. |
| `mcp__serena__search_for_pattern` | Code/text discovery | Searches for candidate text or files; verify structural claims with LSP queries. |
| `mcp__serena__write_memory` | Memory change | Creates or writes the named Memory. |

Source and Memory changes must remain within the task's authorized scope; tool exposure is not authorization. In particular, use `delete_memory` only with explicit instruction and authorization. This table describes available tool roles, not a blanket approval to mutate project files or memories.
`activate_project` confirms project activation and may report available language servers and project memory names. This output helps discover capabilities; it does not prove that every LSP operation or memory is available. Serena tool availability also does not override the Session's filesystem permissions or the task's read/write scope.

### Memory use in Codex

Use the exposed Serena Memory tools for project memories; Codex-local memory and chat compaction do not substitute for `list_memories`, `read_memory`, or an explicitly authorized `write_memory`. If onboarding is incomplete, ask the user before invoking `mcp__serena__onboarding`. Memory state is project-scoped by Serena configuration and is not implicitly shared across Codex Sessions, child Agents, or other runtimes.

## Claude Code CLI / Claude Desktop optimizations

Claude Code supports MCP servers, and its MCP Tool Search defers tool definitions by default and discovers them on demand. When Serena is needed, discover and verify the actual Serena server and tool names in the current Session before relying on them; some configurations load tool definitions upfront instead. Then use only the exposed and authorized Serena tools, following the same project-root, query-bounding, memory, and onboarding rules above. Claude Code Code Intelligence can separately provide language-server navigation and diagnostics when its language plugin is installed; this is distinct from Serena MCP and does not imply Serena's tools or memories are present. Claude Desktop Agents may use Serena only when the relevant MCP tools are actually exposed to that Agent Session. Neither runtime should assume that Serena memories are shared with another Session or product.


## Related concepts

- [Runtime and Model Provider Support](runtime-provider-support.md) — locate runtime and model capability bindings.
- [Session Context Firewall](session-context-firewall.md) — locate bounded project-state ingress rules.
- [Worker Content Memo](../context-exchange/content-memo.md) — locate Worker execution-state ownership.
- [Coding Context Exchange](../context-exchange/context-exchange.md) — locate capsule and authoritative-source rules.
- [Coding Context Exchange Workspace Boundary](../context-exchange/context-exchange-workspace-boundary.md) — locate logical memory naming and authorization.
