# Runtime instruction compiler contract

[English](compiler-contract.md) | [简体中文](compiler-contract_zh_cn.md)

This reference owns the development compiler's input, provenance, validation, and publication contract. The fixed manifest and versioned resource contain the currently reviewed mapping. Root must approve future mapping changes before publication.

## Versions and source units

The manifest format is `token-io-runtime-instructions-manifest/v1`; the resource format is `token-io-runtime-instructions/v1`, with integer `compiler_version` 1, policy contract 2, and legacy context-index 1. Unknown versions fail. An entry is keyed by `(tool_id, node_id, stage_id, locale)`; a stage may recur for another tool or node.

Each bilingual SourceUnit binds a stable ID to a repository-relative Markdown path, a unique heading, raw-source SHA-256, and extracted-excerpt SHA-256. Runtime entries select units and provide exact source quote selectors for actions and each branch's trigger, actions, pass, and failure. Quote occurrence is zero-based. A SourceUnit is source material and does not invent a callable branch. Real-project branches also bind the exact original `legacy_branch` value; the project gate checks complete legal-branch coverage for each node and locale.

`legacy_bindings.fragments` and `legacy_bindings.owners` map stable legacy IDs to canonical units. Multiple declared aliases may point to the same bilingual path and heading; duplicate IDs or unexplained duplicate source selectors fail. The real-project gate verifies all 17 nodes, 44 fragments, 8 owners, 3 optional bindings, default fragments, original legal branches, and the actual index dependency graph. The artifact retains validated registry node metadata, index defaults and fragment dependencies, owner paths, optional bindings, and their source hashes for future consumers. It does not switch the product loader.

The [node and branch mapping](node-mapping.md) records source-backed trigger, action, pass and failure criteria for the stable context nodes. It maps existing authority and never turns a read-only lookup into an effect. Original policy materials and provenance remain in each applicable closure.

Each callable `rules_get_context` entry independently covers its node's full original legal-branch set and defaults; branches cannot be combined across entries. `owner_views` separately binds each of the five legacy delegation policy owners and both locales to explicit source roots. These views are not callable tools and carry no invented actions or branches. Each view precomputes its full dependency closure, source provenance and content hash under the same version, source-hash, budget, provider-section and internal-back-reference checks as an entry. An owner or entry must explicitly include required definition roots; the compiler never adds them automatically.

## References and semantic dependencies

Every actual Markdown link in an excerpt must be classified once using its raw token and occurrence. `required` and `conditional` links enter the full execution closure; conditional links include a stable condition ID and an exact sourced trigger. `navigation` locates material without entering the closure. `internal_already_included` is a definition back-reference whose target and `included_in` unit must already occur in the final entry closure. Navigation may cycle; required and conditional edges may not. No cycle is folded or silently reclassified.

A separate `semantic_dependencies` array represents execution dependencies without a Markdown link. A Markdown-sourced edge uses `provenance.kind: markdown_quote` and an exact selector in its own SourceUnit; a conditional edge also carries `condition_id` and a trigger selector in that unit. A legacy-index edge uses `provenance.kind: legacy_index_dependency`, actual fragment IDs, fixed index SHA-256, and the exact `/fragments/<index>/dependencies/<index>` JSON pointer. The compiler checks the pointer and aliases against the actual index. It does not fabricate a Markdown link or quote for a JSON-only declaration. Both kinds enter closure, cycle detection, provenance, hash, and budget checks.

Local Markdown destinations are resolved relative to their source, with existing targets and valid anchors inside the pinned root. Symlink traversal, path escape, missing targets, invalid anchors, and a target unit whose source path or section does not match fail. External references are data and are not fetched. Ambiguous heading anchors may be rejected rather than guessed. A standalone language-switch pair is exempt only when its local paths are an English file and its corresponding `_zh_cn.md` mirror.

## Integrity and budgets

Canonical JSON is UTF-8 with sorted keys, compact separators, no timestamps, duplicate keys, or non-finite numbers. A real manifest pins SHA-256 for `mcp/rule-registry.json`, `mcp/rule-context-index.json`, and the actual `owner_paths.py` mapping source. Owner assignments are parsed as literals without executing that file. The project gate validates the real registry and index shapes rather than treating synthetic fixtures as publishable project metadata.

Each entry hash binds its identity, format and versions, all three legacy source hashes, relevant aliases, complete transitive source units, quotes, branches, and provenance. The resource carries its own canonical hash. Limits are 8 MiB per artifact, 512 locale-specific source-unit records, and 262,144 Unicode characters per complete entry closure; a manifest may lower but not raise them. Overflow reports required and allowed values and produces no partial complete artifact.

When a Layer-01 source unit enters an entry closure, that closure must also include the same document's Codex CLI / ChatGPT Desktop optimization section in the same locale, including a section that states there is no special optimization. A narrower sourced definition remains narrow; this requirement does not force the complete General rules section. Claude-specific sections remain document compatibility background and are not consumed by this MCP server.

## CLI and fixed publication

Start the local Codex CLI MCP server with `token-io-decoupling-dev --project-root /absolute/repository/root`. The root's canonical path and directory identity are pinned at startup after checking the development marker and fixed inputs. Without this argument, only `dev_capabilities` is registered. Compiler tool calls take no arguments and cannot select a root, input, output, model, or permission. The fixed manifest is `mcp-project-dev/compiler-manifest.v1.json`; the only compile output is `mcp-project-dev/generated/runtime-instructions.v1.json`.

`compile_runtime_instructions` may replace an existing output and is marked destructive. Replacement requires `output_baseline_sha256` to match the existing validated artifact's `canonical_sha256`, not the raw file hash. A supplied baseline must also match for an identical no-op and cannot create a missing file. Without a baseline, only exclusive creation or a byte-identical no-op is allowed. Publication uses bounded no-follow reads, an exclusive owned temporary file, fsync, and atomic replacement or no-replace creation; failure preserves the prior output. `check_runtime_instructions_freshness` reads without writing and reports `fresh`, `stale`, `missing`, or `failed`.

The tools make no OpenAI, network, Git/GitHub, chat, or Memory calls. The server directly supports only local Codex CLI; no runtime-environment judgment or other Agent adapter is added. The review inventories `mcp-project-dev/legacy-mapping-review.v1.json` and `mcp-project-dev/compiler-manifest.review.v1.json` are non-publishing review evidence. Root must review future changes to classifications, provider-section scope and entry branches, and confirm a cycle-free graph and full closure budgets before publishing an updated resource.
