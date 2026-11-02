# Decoupling workflow routing tool

[English](WORKFLOW_ROUTING.md) | [简体中文](WORKFLOW_ROUTING_zh_cn.md)

This document owns the public contract for the MCP workflow tool `decide_decoupling_workflow`: its bounded request, routing behavior, result interpretation, hashes, and failure boundaries. It is advisory navigation. The linked workflow documents and capability/permission gates remain authoritative.

## Purpose and route selection

Call the tool with `payload.request`. It accepts a locked Coding mode and count, one current workflow stage or `auto`, and caller supplied facts about capabilities, constraints, and evidence. It does not determine whether a checkpoint passed, change the mode or count, grant permission, create an agent, dispatch work, or call another tool.

An explicit stage selects its route locally after loading and checking the relevant current rule context. It makes no API request and does not need outbound permission. `auto` can ask one bounded Decisions choice, but only when source facts are present, the request permits outbound data, and Decisions is enabled with outbound data permitted by server configuration. The request assertion does not prove the caller's authority to disclose data.

## Request contract

The outer envelope is `{ "payload": { "request": { ... } } }`. The strict request fields are:

| Field | Contract |
| --- | --- |
| `task_id` | Required, nonblank, 1–160 characters. |
| `task_summary` | Required nonblank text, up to 1,200 characters. |
| `stage` | Required: `auto`, `entry_readiness`, `session_readiness`, `work_definition`, `execution`, `verification_repair`, `documentation`, or `delivery_acceptance`. |
| `language` | `en` or `zh_cn`; defaults to `en`. |
| `mode_locked` | Required strict boolean. It must be `true` for a route result. |
| `mode_count` | The canonical Core `ModeCount` object: `mode` is `Single-Agent Coding` or `Multi-Agent Coding`; `child_count` is a nonnegative integer, exactly `0` for Single-Agent and at least `1` for Multi-Agent. |
| `capabilities` | Up to 7 unique facts, each with `capability_id`, `status`, and `source_ref`. IDs are `rule_context`, `implementation`, `verification`, `documentation`, `git`, `child_creation`, and `dispatch`; status is `available`, `unavailable`, or `unknown`. |
| `hard_constraints` | Up to 8 unique records with `constraint_id`, `source_ref`, and `statement`. |
| `source_facts` | Up to 8 unique records with `fact_id`, `source_ref`, and `statement`. Each fact is bounded text with a source pointer; the pointer is caller supplied, not source authentication. |
| `source_facts_hash` | Required 64-character lowercase SHA-256 matching the canonical `source_facts` list. |
| `outbound_data_permitted` | Required strict boolean. It must be `true` for `auto` to make an API request. |

Fact and constraint identifiers are 1–96 characters and must start with an ASCII letter or digit; the remaining characters may be letters, digits, `.`, `_`, `:`, or `-`. Source references are 1–256 characters. Statements are nonblank and at most 1,200 characters. The complete canonical request is limited to 32,000 UTF-8 JSON bytes; oversize input is rejected, never truncated.

The route mapping follows the seven modules already defined by the current workflow owners:

| Stage | Single-Agent | Multi-Agent |
| --- | --- | --- |
| `entry_readiness` | SM01 | MM01 |
| `session_readiness` | SM02 | MM02 |
| `work_definition` | SM03 | MM03 |
| `execution` | SM04 | MM04 |
| `verification_repair` | SM05 | MM05 |
| `documentation` | SM06 | MM06 |
| `delivery_acceptance` | SM07 | MM07 |

The native route reference points to the matching language and mode route. The Multi-Agent execution stage may include conditional reminders about role and authority gates, task authorization and memo conditions, and Slice-before-child lifecycle. Verification, documentation, and delivery stages may return their applicable conditional checks, including repair only after a verification finding, re-verification after a changed epoch, and Git only under existing authority. These reminders do not replace the route owner or authorize an action.

## Hashes and rule context

`source_facts_hash` is SHA-256 over UTF-8 canonical JSON for the input-order list of each fact's `model_dump(mode="json")`, using `ensure_ascii=false`, sorted object keys, and compact separators. `input_hash` uses the same canonical JSON and SHA-256 over the complete normalized request, excluding only `source_facts_hash`. These hashes detect content changes; they do not authenticate sources, prove facts, or establish permission.

For an explicit stage, the tool loads that stage's bounded rule bundles, checks completeness and budget, then reloads them and compares hashes before returning advice. For `auto`, it first loads the selection context for task intent, mode, and decision rules; the Decisions request contains the bounded caller facts and current rule fragments. After the request it reloads and rechecks the context, then loads and rechecks the selected stage context. The total rule text and Decisions input are each bounded to 42,000 characters. The response returns rule and index hashes plus compact rule evidence and missing-fact references; it does not repeat full rule text. A stale or unavailable context must be refreshed before reuse.

## Result and review

Every result has `advisory_only: true`, `status`, `reason`, `source_facts_hash`, and `input_hash`. A locked mode also yields a `native_route` reference. A selected stage can include its `module_id` and `conditional_checks`. Results may include `rule_hash`, `index_sha256`, `rule_evidence`, `missing_facts`, and `capability_evidence`; API outcomes may also include `failure_class`, `provider_error_code`, `recovery`, the fixed model ID, and token usage. Evidence is a compact set of references and hashes, not a replacement for reading the current route owners.

| Status | Meaning |
| --- | --- |
| `available` | A stage or module suggestion was produced. It is not a readiness result or permission. |
| `insufficient_evidence` | The current facts or required rule context cannot support a safe suggestion. Review the listed missing facts. |
| `blocked` | A prerequisite, configuration, request, or provider check failed; do not treat this as a suggestion. |
| `stale` | Rule context changed during the operation; refresh current rules and recompute before using any result. |

The exact `reason` values are `explicit_stage_advice`, `stage_selected`, `mode_not_locked`, `source_facts_missing`, `outbound_data_not_permitted`, `decisions_disabled`, `rules_unavailable`, `rule_context_incomplete`, `rule_context_budget_exceeded`, `request_exceeds_supported_bound`, `missing_credentials`, `provider_error`, `timeout`, `refusal`, `invalid_response`, `incomplete_response`, `unsupported_model`, `insufficient_evidence`, and `stale_rule_context`. Provider errors are classified into bounded codes; the result does not expose raw provider errors or credential values. Recheck the hashes and current capabilities, route, facts, and permissions before acting. Continue to follow the existing route and checkpoint owners.

## API and side-effect boundary

Only `auto` can make a Decisions request. Before the request, the server reads nonblank `OPENAI_API_KEY` and `OPENAI_BASE_URL` from its process environment and passes both explicitly to the client. It uses exactly `gpt-6-luna`, with automatic retries disabled. A refusal, incomplete or invalid choice, wrong returned model, missing configuration, provider failure, missing outbound permission, disabled Decisions configuration, incomplete rules, or changed rule hash cannot produce an available suggestion. No API fallback or model substitution is used.

The tool is stateless: it writes no workflow state and performs no Git, file, agent-creation, or dispatch operation. Tool discovery does not attest identity or grant authority. The native route remains the owner of stage order, checkpoint actions, branch conditions, evidence, and acceptance.

## Related concepts

- [MCP workspace development guide](DEVELOPMENT.md) — owns workspace tooling and the public profile inventory.
- [Single-Agent Coding workflow](../docs/skill/references/coding/layer-04-workflows/coding-single-agent.md) — owns the Single-Agent route.
- [Multi-Agent Coding workflow](../docs/skill/references/coding/layer-04-workflows/coding-multi-agent.md) — owns the Multi-Agent route.
- [Task Assignment](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-assignment.md) — owns execution-subject decisions.
