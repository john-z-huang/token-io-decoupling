# Checkpoint Structural Checks

[English](checkpoint-structure-checks.md) | [简体中文](checkpoint-structure-checks_zh_cn.md)

This owner defines deterministic structural evaluation of caller-supplied checkpoint facts and evidence. It does not authenticate inputs, determine semantic truth, authorize work, or accept a task.

## General rules

### Treat evaluation as an optional structural aid

Use a structural check when it helps identify missing or malformed supplied facts for a current checkpoint judgment. The current checkpoint owner remains authoritative. Inspect it directly and decide what the evidence means; a structurally complete submission is not proof that its facts are true or that the checkpoint passed.

Inputs, evidence references, revisions, fingerprints, and hashes supplied by the caller remain caller-supplied facts. A checker may reject malformed, inconsistent, stale, or unsupported inputs, but cannot authenticate the caller, prove permission or provenance, grant authority, establish sequencing across calls, or accept a task. Results do not persist state or remember previous calls.

`ready_for_agent_review` means only that the supplied input meets the checker's structural requirements. `incomplete_for_agent_review` reports missing required facts or evidence. `blocked_input` reports an invalid, inconsistent, stale, or unsupported input. Review the current owner and evidence independently for every status.

For Control, the structural result does not replace the current Control owner, current-state verification, or the required user/Agent judgment. If the optional structural check is unavailable, use the authoritative owner and available evidence directly; block only a judgment whose required input cannot otherwise be established.

## Codex CLI / ChatGPT Desktop optimizations

When the optional structural check is useful and available, call `workflow_evaluate` with `payload.node_id` and `payload.submission`; the top-level node must match `submission.node_id`. Call `evaluate_control_checkpoint` with `payload.submission` for Control; its node must be `control`. Both envelopes accept `payload.language` (`en` or `zh_cn`, default `en`), optional `payload.expected_rule_hash`, optional `payload.semantic_input`, and optional `payload.current_facts`. Set `language` to `zh_cn` when checking the Chinese rule text; the default `en` selects English rules. `current_facts` defaults to an empty map; supplying it does not enable API requests or authorize disclosure. Omit `semantic_input` for structural-only use. Supplying `semantic_input` additionally requests separate Decisions advice and follows [Decisions Advisory](../execution-planning/decisions-advisory.md); it does not change the structural result.

The typed submission contains 1–128 facts; at most 128 top-level evidence references; at most three coverage dimensions; and an optional evidence-request ID of 1–128 characters. A fact may include at most 16 evidence references; a `missing_evidence` judgment may identify 1–16 required references. Each reference URI is 1–512 characters, and an evidence ID or request ID is 1–128 characters. The normalized submission (excluding its optional `input_hash`) and the complete normalized evaluation payload are each limited to 32 KiB of UTF-8 JSON; the complete payload ceiling includes all fields, including `submission`, `current_facts`, and any `semantic_input`, so the component maxima cannot all be used at once. The payload's `current_facts` map allows 0–16 flat string pairs, with keys 1–64 characters and values 1–1,024 characters; keys and values cannot be blank or whitespace-only. These JSON byte ceilings apply to the normalized model payload, not protocol framing.

The optional `input_hash` is a consistency assertion: omission lets the service return the computed `source_input_hash`; a supplied mismatch returns `blocked_input` with `source_input_hash_mismatch`. Compute the canonical SHA-256 as follows: serialize `submission.model_dump(mode="json", exclude={"input_hash"})` using `ensure_ascii=False`, sorted keys, and compact `,` and `:` separators; encode the result as UTF-8 and hash those bytes. `source_input_hash` fingerprints only the normalized submission. The separate optional `expected_rule_hash` must come from the full registered-node `rules_get_context` result for the same node and selected language, with `context_version` omitted. Do not pass a version-1 fragment bundle's `context_hash` or `index_sha256`; those identify a different rules fragment set. Because `expected_rule_hash` is optional, do not make an extra rules lookup when that freshness assertion is unnecessary. The returned `rule_hash` identifies the full current registered node rules in the selected language; it is distinct from `source_input_hash`.

The result reports `status`, `reason`, evaluated `language`, `source_input_hash`, `rule_hash`, and applicable selected branch and missing requirements. Treat it as `authority: structural_check_only`; it is never a checkpoint pass, permission, acceptance, or sequencing token. The tools do not persist state. A schema violation fails input validation before evaluation; correct the caller-supplied input against the current schema before retrying, and do not truncate facts or evidence to fit. A returned `blocked_input` identifies an inconsistent, stale, or unsupported submission.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific direct-MCP optimization for structural checkpoint checks. Follow the general rules, use only capabilities actually exposed to the current Session, and maintain equivalent evidence through an authorized mechanism. When the optional check is unavailable, mark it `Not applicable` with a reason unless the task independently requires its structural result; in that case, block only the dependent judgment if the required structure cannot be checked by another authorized means.

## Related concepts

- [Workflow Rule Context](rule-context.md) — owns bounded navigation to current workflow rules.
- [Workflow Navigation Availability](navigation-availability.md) — owns the unavailable-navigation and optional-check branch.
- [Coding Execution Control](../execution-control/execution-control.md) — owns Slice and Control decisions.
- [Decisions Advisory](../execution-planning/decisions-advisory.md) — owns separately requested optional semantic advice.
