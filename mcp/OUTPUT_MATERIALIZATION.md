# Worker output materialization

[English](OUTPUT_MATERIALIZATION.md) | [简体中文](OUTPUT_MATERIALIZATION_zh_cn.md)

This document owns the `materialize_decoupled_output` Worker tool contract: its prepare, inspect, and apply lifecycle, trusted operator grant, bounded templates, result interpretation, and recovery boundaries. The [MCP workspace development guide](DEVELOPMENT.md) owns profile inventory and startup-factory indexing.

## Purpose and authority

The tool lets an eligible Worker prepare bounded output artifacts outside the project, inspect those artifacts, and apply an explicitly granted set of files through the configured project root. It is worker-only and does not add a profile. Tool discovery, a verified Worker binding, Worker state-store guards, `WORKER_WRITE`, and an assignment do not by themselves grant project-file write authority.

Each operation re-reads the verified Worker materialization context and a separate trusted operator grant. The context must identify the current Worker, Root, project, allocation, role, output class, released slice, and confirmed assignment hash. The grant must be active and match that binding, the pinned project and artifact directory identities, policy version, exact paths, operations, and allowed templates. A changed or revoked grant, changed assignment, missing context, or unavailable safety capability fails closed. Grant data is obtained from trusted operator code, never from the request payload.

The initial supported role is `Primary Output`, with either `code_configuration` or `skill_instructions`. Ordinary documentation, the Documentation/Comments & Git Operations role, and other roles/classes are unsupported. The actual released assignment and independent grant must both allow every path and operation. This tool preserves the Skill's role ownership and the existing Worker output classes.

The operator configures absolute project and artifact roots through an explicit trusted startup factory. The factory returns `OutputMaterializerConfig` with those roots and a `grant_provider.current_grant()` method. The server uses the same configured project root and compliance preflight service as the existing read-only compliance tool. Without the factory, service, grant, secure directory access, or required preflight, the tool reports unavailable and does not guess paths, create a default host or directory, or modify user configuration. Keep the artifact root private and physically separate from the project root. Startup rejects overlapping lexical roots and matching opened-directory identities and verifies directories without following path-component symlinks; it does not detect every physical alias such as OS bind mounts, which remains the operator's responsibility.

## Request lifecycle

The MCP call envelope is `{ "payload": { "request": { ... } } }`. Its discriminator selects one of three actions:

| Action | Request data | Effect |
| --- | --- | --- |
| `prepare` | `files` and optional `outbound_data_permitted` (default `false`) | Validates authority and templates, renders candidate content, then stores an immutable candidate and manifest in the artifact area. It does not write project files. |
| `inspect` | `prepared_id`, `expected_manifest_hash`, `file_index`, optional `offset` (default `0`) and `max_chars` (default `2048`) | Reads a bounded range from a prepared file after rechecking the grant and manifest. |
| `apply` | `prepared_id`, `expected_manifest_hash` | Rechecks authority, candidate integrity, baselines, and the whole batch preflight, then applies eligible files. It does not regenerate content or call Responses. |

Each prepared file has a normalized relative leaf path, `operation` (`create` or `replace`), a baseline (`absent` for create or a SHA-256 for replace), and a version-1 template. The requested path must be permitted by both the confirmed assignment and current grant. Paths are exact; directory creation, globs, absolute paths, traversal, and repository-control data such as `.git` are not supported.

`prepare` returns `status: prepared`, an opaque `prepared_id`, `manifest_sha256`, per-file content hash/character/byte counts and a preview limited to 256 characters, plus inspect instructions. `inspect` returns the bounded content slice and page fields, including offset, maximum length, total character/byte counts, hash, next offset, and whether the file is complete. The caller must retain the manifest hash and provide it unchanged to subsequent inspect and apply calls. A mismatch or tampered artifact is a conflict and must not be treated as fresh output.

## Templates, limits, and optional ordering

Version 1 supports three finite templates:

- `literal_text` accepts bounded supplied text and preserves it as candidate content.
- `json_document` accepts bounded JSON text, rejects duplicate object keys and non-finite numbers, and validates a maximum nesting depth of 16 and 4,096 total nodes before canonical serialization (`ensure_ascii=false`, sorted keys, compact separators, and one final newline). It is not an open-ended recursive JSON schema.
- `fact_markdown` accepts bounded heading IDs/titles and fact IDs, heading references, and source text. Local code renders the supplied values as Markdown. By default facts remain in source order.

The fixed bounds are 1–16 files, 512 characters per path, 131,072 characters per text field or rendered file, and 524,288 UTF-8 bytes across the rendered candidate contents in a batch. JSON nesting is limited to depth 16 and 4,096 total nodes. Fact Markdown accepts at most 8 headings and 64 facts; a fact is at most 8,192 characters. Before making a Responses call, the implementation rejects headings containing line breaks. The Responses input budget is 48,000 characters across its system instructions and input text combined, excluding fixed SDK schema and JSON framing; the output limit is 4,000 tokens. Inspection returns at most 8,192 characters per call, defaulting to 2,048. The implementation rechecks size after rendering. These are character/byte/token limits, not estimates.

For `fact_markdown`, the operator grant may permit `ordering: "responses"`. This optional branch requires `outbound_data_permitted: true` on that prepare request as a per-call assertion; it does not grant file or network permission. Each request explicitly reads and uses nonblank process `OPENAI_API_KEY` and `OPENAI_BASE_URL`, uses only `gpt-6-luna` at medium reasoning effort with a 30-second timeout and zero automatic retries. Production uses the fixed OpenAI client configuration; the operator factory cannot override the client. The model receives bounded supplied facts and may return only an ordering of the supplied fact IDs. Local code rejects unknown, repeated, omitted, or otherwise invalid IDs and renders the original text. The model cannot create prose, code, files, or permissions. Missing configuration, refusal, timeout, incomplete or malformed output, or budget failure stops preparation without producing a candidate; API error details are not returned to the tool caller, and there is no free-text fallback. The apply action never calls the API. API usage is not included in this tool's result; missing usage data must not be interpreted as zero.

## Apply checks and filesystem boundary

Before writing, apply requires the complete candidate batch to pass the existing compliance preflight at policy version 1 for the same pinned project root. `fail`, `unknown`, missing, stale, or unavailable preflight blocks the entire batch, including an all-identical replay. Files already matching their candidate are safely verified and projected to preflight as `replace` with the candidate SHA-256 baseline; pending files retain the original manifest operation and baseline. This projection is only a read-only preflight input: it does not change the write authority in the original manifest or grant. Apply also rechecks each current grant, assignment, path authorization, candidate hash, and baseline. It does not execute or import code from the target repository.

Project and artifact roots are operator-configured and opened safely. Reads reject symlinks and non-regular or unstable files. Writes use same-directory temporary files and atomic per-file publication; create uses no-clobber behavior, and replace rechecks the expected baseline and reads back the result. Existing parent directories are required; apply does not create them. The implementation does not elevate file permissions.

Cooperative locking serializes participants using the same service, but does not provide a global compare-and-swap against unrelated writers. An external writer can race after the last check. A multi-file batch is not collection-atomic: an error may leave some files applied. The service does not promise reliable automatic rollback.

## Results and recovery

On a completed apply, the durable receipt identifies version, prepared ID, manifest hash, batch status, and per-file status with optional `actual_sha256`. Per-file values are `applied`, `already_identical`, `conflict`, `not_attempted`, or `uncertain`; batch values are `applied`, `already_identical`, `partial`, `conflict`, or `uncertain`. A preflight or integrity gate may instead return `status: blocked`, `reason_code`, current per-file classifications, and preflight status; this is not a receipt that says files were applied. Inspect per-file hashes and actual state before deciding what to do next.

- On an uncertain prepare with no returned ID/hash, do not invent an identifier or assume the call is idempotent. A repeated prepare may create a new candidate and may make another ordering API call. Treat the result as unresolved and have the operator manage any orphaned artifact using the configured artifact-store procedures; this tool does not expose an artifact listing operation.
- On an uncertain inspect, repeat the same bounded read only after checking that the prepared ID and expected hash are still current.
- On an uncertain apply or partial receipt, read the current files and compare them with the candidate, baseline, and durable receipt. For the same manifest, matching candidate content is already applied and is never rewritten. A file with no write attempt recorded (`not_attempted`) may resume from its original baseline if authority and a fresh preflight still pass. If a prior receipt records `applied`, `already_identical`, or `uncertain` and current content is no longer the candidate, report conflict even when it matches the original baseline; this preserves later user reversions and possible writes with uncertain readback. Other content is also a conflict. Never overwrite an external change or assume rollback. If applying again is still intended, review current facts and prepare a new candidate.
- If grant, assignment, preflight, root identity, or manifest has changed, prepare and review a new candidate under current facts; do not reuse stale approval or hashes.

## Related documents

- [MCP workspace development guide](DEVELOPMENT.md)
- [Candidate compliance preflight](CANDIDATE_COMPLIANCE.md)
- [MCP directory instructions](AGENTS.md)
