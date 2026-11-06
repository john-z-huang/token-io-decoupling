# Candidate compliance preflight

[English](CANDIDATE_COMPLIANCE.md) | [简体中文](CANDIDATE_COMPLIANCE_zh_cn.md)

This document owns the contract and limits of the read-only `validate_decoupling_compliance` MCP tool. It describes a bounded candidate overlay check; it does not define workflow authorization or final acceptance.

## Purpose and authority

Use this tool to inspect proposed file changes against a trusted checkout before a separately authorized write. It accepts candidate content and checks it together as an in-memory overlay, so candidates in the same request can satisfy one another's direct mirror and link-target checks. The tool does not write candidate files, make an API request, run subprocesses, or execute candidate-repository code.

The trusted root and allowed policy scopes come from operator code loaded at server startup with `--compliance-factory MODULE:CALLABLE`. Neither the payload nor the current working directory selects the root. Only configure this factory with trusted operator code and the intended checkout. The service reads baseline and direct targets through a bounded, read-only reader. Without a configured reader, it does not probe candidate paths; disk-dependent checks remain `unknown`, not `pass`.

## Request contract

Call `validate_decoupling_compliance` with `payload.request` containing `{"policy_scope": ..., "candidates": [...]}`.

- `policy_scope` is `skill_maintenance` or `generic_project`. The configured service must explicitly allow the selected scope; a disallowed scope yields `unknown` checks.
- `candidates` contains 1–64 entries with unique canonical repository-relative POSIX `path` values of at most 512 characters. Absolute paths, backslashes, NUL, empty components, `.` and `..` are rejected.
- Each entry has `operation` (`create`, `replace`, or `delete`) and a `baseline`. `create` requires `{"state":"absent"}`. `replace` and `delete` require `{"state":"sha256","value":"<64 lowercase hex characters>"}` for the current disk bytes.
- `create` and `replace` require `content` (at most 131,072 Unicode characters per file). `delete` must have no content (omitted or null). The combined candidate content is limited to 524,288 UTF-8 bytes; this counts only candidate content, not request, path, or baseline encoding overhead.

The baseline is checked against the trusted root at invocation time. A mismatch, an existing create target, or a missing replace/delete target fails the baseline check. Unsafe or unavailable reads produce `unknown`. The baseline does not lock the files or authorize a later write; callers must obtain write authorization independently and recheck current state before acting.

## Checks and result

For `skill_maintenance`, the preflight checks candidate mirror presence, applicable Markdown link language and layer rules, direct local Markdown link targets, and the Layer-01 section structure when a candidate is a Layer-01 owner. Direct targets may resolve through the candidate overlay or the configured root. A check that does not apply to a candidate is `not_applicable`.

For `generic_project`, Skill-maintenance rules are `not_applicable`; this scope does not apply repository Skill rules to an arbitrary project. A requested scope not enabled by the startup configuration is reported as `unknown`.

The result has `policy_version` (`1`), `status`, `policy_scope`, `checks`, `not_evaluated`, and `limits`. Each check reports `rule_id`, status, path, line, bounded message, and an `evidence_missing` list; `target_path` and `reason_code` are included when available. The list names evidence needed to resolve an unknown finding, and may be empty when the check needs no additional evidence. Status values are `pass`, `fail`, `unknown`, and `not_applicable`. Overall status precedence is `fail`, then `unknown`, then `pass`; if every check is not applicable, the overall status is `not_applicable`. Treat `unknown`, a failed check, truncated output, or an exceeded target budget as unresolved; use `evidence_missing` and the reason code to identify what must be supplied or corrected, then rerun against current candidates.

Limits are 256 direct target reads, 512 returned checks, and 512 characters per message, in addition to the request limits above. Exceeding a direct-target or output-check budget adds an `unknown` finding; omitted evidence must not be treated as passing.

## Acceptance boundary

A passing preflight establishes only that the returned checks passed for the supplied candidate overlay and the configured reader's observations. It does not perform reverse inbound-link scans across unchanged documents, compare English and Simplified Chinese mirror semantics, or run full repository CI and final integration acceptance; these are explicitly returned in `not_evaluated`. Complete the applicable repository checks and review before accepting or applying documentation changes. The tool does not authorize or perform that application.

## Related documents

- [MCP directory instructions](AGENTS.md)
- [Codex caller matching](CODEX_CALLER_CONTEXT.md)
- [MCP development guide](DEVELOPMENT.md)
- [Task plan lifecycle tools](TASK_PLAN_TOOLS.md)
- [Decoupling workflow routing](WORKFLOW_ROUTING.md)
