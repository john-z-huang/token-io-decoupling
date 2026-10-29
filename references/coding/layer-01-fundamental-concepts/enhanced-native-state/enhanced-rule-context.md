# Enhanced Rule Context

[English](enhanced-rule-context.md) | [简体中文](enhanced-rule-context_zh_cn.md)

This module owns bounded loading of a current registered rule node and its mapped owner heading. It does not own the underlying rule, authorize work, or establish identity or permission.

## General rules

### Select and qualify current rule context

Use the stable node mapping only to locate the existing authoritative owner path and exact heading. Load only the node needed for the current checkpoint; do not scan the repository or treat a returned excerpt as a recursive load of linked owners. If the judgment needs another directly linked owner, read that authoritative document separately and verify its current version and language. If a required owner is unavailable, block the dependent judgment rather than infer its contents.

Read the registry and owner heading from one source and one language for each request. Each request rereads the current mapping and heading and binds a hash to that node structure, language, and text. Ordinary prose edits become visible on the next read. A structural change to supported node IDs, facts, evidence, branches, or other program-checked shape requires a compatible implementation and tests; reject unsupported structure instead of interpreting it with an older contract.

The installed package uses its generated read-only owner excerpts. Source development uses a repository root that is explicitly configured by the caller; do not infer a checkout from the installed package location. Editing source Markdown does not alter an already installed package snapshot. Never combine a registry from one source with owner text from another, or English mapping with Chinese text.

Public rule-context access is read-only and may be used on the Native route. It does not prove trusted host identity, operation guards, Enhanced state availability, or authorization. A complete required heading whose source, language, and hash are verified counts as reading that heading. It does not show that unreturned sections or directly linked owners were read, and the mapped owner remains authoritative for meaning.

When selected rule context is not needed, record `Not applicable` with the reason and still read the required authoritative owner directly. If bounded loading fails but the authoritative owner is available, use that owner directly and record the limitation. If the mapping is incompatible or the required authoritative content cannot be obtained, block only the judgment that depends on it.

## Codex CLI / ChatGPT Desktop optimizations

The public `rules_get_context` surface returns the current registered node context without opening Root or Worker state. Use it only for the selected node and verify its owner, language, and hash. A successful public read is not evidence that protected state or a real host binding is available. Source development must explicitly select the repository root; an installed runtime reads its packaged snapshot.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific rule-context optimization. Follow the general rules and obtain the current authoritative owner content through capabilities actually exposed to the current Session.

## Related concepts

- [Enhanced State Store](enhanced-state-store.md) — locate the separate protected state and identity boundary.
- [Coding Delegation Mode Confirmation](../delegation/delegation-mode-confirmation.md) — locate the mode-selection owner mapped by the output-class node.
- [Coding Execution Control](../execution-control/execution-control.md) — locate Slice and Control node ownership.
