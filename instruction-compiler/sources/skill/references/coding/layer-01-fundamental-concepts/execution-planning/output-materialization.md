# Output Materialization

[English](output-materialization.md) | [简体中文](output-materialization_zh_cn.md)

This owner defines controlled preparation, inspection, and application of a bounded candidate output batch through a separately authorized write capability. It does not own role policy, grant issuance, final verification, or general-purpose file writing.

## General rules

### Keep preparation, review, and application distinct

Prepare output only when the current assignment, operation-specific grant, pinned roots, exact paths, and required safety capabilities are verified for the current call. A role assignment, tool discovery, capability listing, or ordinary write permission does not substitute for a separate matching grant. If the required context or guard is missing, stale, revoked, or ambiguous, stop without guessing a path or capability.

Preparation creates a bounded candidate artifact outside the project and must not be described as a project write. Preserve its identifier and manifest hash. Inspect only bounded portions and review the candidate before application. Apply the same prepared candidate only after rechecking current authority, artifact integrity, baselines, and a fresh whole-batch preflight for the pinned project. Do not regenerate content during apply or treat a prior preflight as current authorization.

Use only the finite locally rendered templates and declared limits. Any optional semantic service may select among supplied fact identifiers only; local code retains supplied facts and renders the output. Missing configuration, refusal, invalid response, stale context, or limit failure stops preparation without substituting free-form output. Do not infer zero usage when a service does not report usage.

Application is bounded by exact authorized paths and operations. Recheck current file state, preserve external changes, and inspect receipts and actual files after partial or uncertain outcomes. A same-candidate replay must not overwrite a later user change. Cooperative locks do not protect against unrelated writers; a multi-file batch may be partially applied and has no promised global rollback. When state is uncertain or authority has changed, stop and resolve from current evidence before preparing a new candidate.

This capability is optional. Native output work may continue under its own authorized route when this capability is unavailable. Never treat unavailable as success or weaken the relevant role, permission, or verification owner.

## Codex CLI / ChatGPT Desktop optimizations

The current MCP operation is `materialize_decoupled_output` with `payload.request` action `prepare`, `inspect`, or `apply`. It requires a trusted startup-injected authorization provider that supplies current Worker binding and assignment context, a separate operator grant, pinned project/artifact roots, and required read-only compliance preflight. The service checks that provider context matches the actual per-call Worker binding and rechecks authority across phases. Tool payloads cannot select or supply authority context. No standard provider is configured; without the trusted provider and grant, the capability is unavailable and no default root is guessed.

The supported role is `Primary Output` with output class `code_configuration` and policy scope `generic_project`. Project-specific Skill authoring belongs to the private development Skill; ordinary documentation and other roles/classes are unsupported. Policy version 2 has finite `literal_text`, `json_document`, and `fact_markdown` templates. `prepare` stores a candidate outside the project; `inspect` reads a bounded page; `apply` rechecks current grant, assignment, hashes, baselines, and whole-batch preflight before writing. Keep and pass the same manifest hash. Review per-file and batch receipts, especially `partial`, `conflict`, or `uncertain`; do not assume rollback or retry over changed content. The MCP output-materialization contract owns exact request fields, limits, and recovery classifications.

For the optional fact-ordering request, follow the fixed API contract stated in the actual MCP tool metadata; the model can return only an ordering of supplied fact IDs. This tool contract does not inspect or change the Agent Session's model. Agent runtime, model, and effort bindings belong to [Runtime and Model Provider Support](../session-runtime/runtime-provider-support.md).

## Claude Code CLI / Claude Desktop optimizations

This repository's MCP Server supports local Codex CLI only. Claude's generic MCP capability does not make this server a supported direct client, and no Claude-specific direct-tool optimization is defined. Follow the general rules using capabilities actually exposed and authorized in the current Session. If this controlled capability is unavailable, use any independently authorized direct output route and its verification requirements.

## Related concepts

- [Candidate Compliance Preflight](candidate-compliance.md) — owns read-only candidate checks.
- [Session Role Ownership](../session-runtime/session-role-ownership.md) — owns role responsibility; this service still requires its separate trusted binding context and grant.
- [Workflow Navigation Availability](../workflow-navigation/navigation-availability.md) — owns direct-owner fallback when optional navigation is unavailable.
- [Coding Execution Control](../execution-control/execution-control.md) — owns release and Control transitions.
- [Task Assignment](task-assignment.md) — owns executor and output responsibility.
