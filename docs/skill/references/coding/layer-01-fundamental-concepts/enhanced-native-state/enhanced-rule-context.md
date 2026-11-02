# Enhanced Rule Context

[English](enhanced-rule-context.md) | [简体中文](enhanced-rule-context_zh_cn.md)

This module owns legacy bounded loading of a current registered rule node and its mapped owner heading, plus the explicitly versioned fragment-bundle read contract. It does not own the underlying rule, authorize work, or establish identity or permission.

## General rules

### Select and qualify current rule context

Read only the authoritative rule context needed for the current judgment. Preserve the existing legacy read contract. Select bounded fragments only through an explicitly versioned index and include their declared dependency closure; do not scan the repository or treat a bundle as a recursive load of linked owners. Measure the budget in Unicode characters and never truncate content to fit. Missing required content or an insufficient budget means the result is incomplete. Completeness means only that the requested index dependency closure was assembled; it does not prove that all task rules or linked owners have been read. If the judgment needs another directly linked owner, read that authoritative document separately and verify its current version and language. If a required owner is unavailable or not covered, block the dependent judgment rather than infer its contents.

Read the registry and owner heading from one source and one language for each request. Each request rereads the current mapping and heading and binds a hash to that node structure, language, and text. Ordinary prose edits become visible on the next read. A structural change to supported node IDs, facts, evidence, branches, or other program-checked shape requires a compatible implementation and tests; reject unsupported structure instead of interpreting it with an older contract.

The installed package uses its generated read-only owner excerpts. Source development uses a repository root that is explicitly configured by the caller; do not infer a checkout from the installed package location. Editing source Markdown does not alter an already installed package snapshot. Never combine a registry from one source with owner text from another, or English mapping with Chinese text.

Public rule-context access is read-only and may be used on the Native route. It does not prove trusted host identity, operation guards, Enhanced state availability, or authorization. A complete required heading whose source, language, and hash are verified counts as reading that heading. It does not show that unreturned sections or directly linked owners were read, and the mapped owner remains authoritative for meaning.

When selected rule context is not needed, record `Not applicable` with the reason and still read the required authoritative owner directly. If bounded loading fails but the authoritative owner is available, use that owner directly and record the limitation. If the mapping is incompatible or the required authoritative content cannot be obtained, block only the judgment that depends on it.

## Codex CLI / ChatGPT Desktop optimizations

The public `rules_get_context` surface returns the current registered node context without opening Root or Worker state. A call without `context_version` retains the legacy request, output, and hash. Fragment-bundle fields, including `fragment_ids` or `max_chars`, require explicit `context_version: 1`; unversioned extensions are rejected. For a bundle, verify owner/source, language, fragment coverage, completion status, `index_sha256`, context hash, and the truncation flag. `max_chars` counts Unicode characters in fragment text, not tokens; it defaults to 12,000 and accepts 256–60,000. Content is never truncated to fit. Review `remaining_owner_refs` and read any relevant uncovered owner directly. A complete bundle covers only its requested index closure. A successful public read is not evidence that protected state or a real host binding is available. Source development must explicitly select the repository root; an installed runtime reads its packaged snapshot.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific rule-context optimization. Follow the general rules and obtain the current authoritative owner content through capabilities actually exposed to the current Session.

## Related concepts

- [Workflow Routing Advice](../execution-planning/workflow-routing-advice.md) — owns optional task-level stage suggestions and requires direct review of the current route.
- [Candidate Compliance Preflight](../execution-planning/candidate-compliance.md) — owns read-only candidate structure checks.
- [Enhanced State Store](enhanced-state-store.md) — locate the separate protected state and identity boundary.
- [Coding Delegation Mode Confirmation](../delegation/delegation-mode-confirmation.md) — locate the mode-selection owner mapped by the output-class node.
- [Coding Execution Control](../execution-control/execution-control.md) — locate Slice and Control node ownership.
