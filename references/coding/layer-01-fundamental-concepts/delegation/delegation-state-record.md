# Coding Delegation State Record

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

This module owns the task-control record used by Coding delegation. It defines the record's canonical location, ownership, shape, field constraints, and staged presence semantics. It does not decide the mode, define Worker read/write boundaries, create children, allocate roles, or define lifecycle transitions. Session audit configuration is owned by [session audit visibility](../session-runtime/session-audit-visibility.md).

## General rules

### Ownership

The root parent owns one host-Session-level mode/count decision and updates task-specific slices and lifecycle in the same record. The record is task state; it is not stored by editing a policy file. In Native operation, maintain the canonical structured record in parent context and read it back before each route release; a transient child-status result is not canonical. In Enhanced operation, after an authorized Root store is initialized and its identity and schema are validated, the Root SQLite record is canonical for persistent Enhanced state. Parent context then keeps a readable snapshot or reference, not a competing writable authority. Native-to-Enhanced reconciliation follows [Native Reconciliation](../enhanced-native-state/native-reconciliation.md); return to Native follows [Native Authority Transfer](../enhanced-native-state/native-authority-transfer.md). Neither transition changes this record's field owners or permits overwriting a valid canonical record.

### Record shape

Before route release, maintain this canonical record:

```text
owner: <root-parent identity>
run_id: unset | <stable identifier for this Multi-Agent delegation run>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode_source: unset | explicit | default | timeout-default (legacy only)
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <locked positive integer>
source: <SemanticRef for the current mode/count decision>
semantic_references: [<retained SemanticRefs, including prior count sources>]
allocations: [{allocation_id: <stable child allocation identifier>,
               agent: unbound | <created-agent-identity>, role: unassigned | <role>,
               slice_status: pending | released, interaction_slice, scope, mutations,
               return_conditions, lifecycle, write_content_memo}]
session_audit: {audit_mode, root_reasoning_cadence, worker_reasoning_cadence,
                source: {audit_mode: explicit | default, root_reasoning_cadence: explicit | default,
                        worker_reasoning_cadence: explicit | default},
                worker_log_visibility: available | unverified | unavailable | Not applicable,
                worker_log_evidence, audit_config_prompt: {status: unasked | pending | answered |
                timed_out | unavailable | reused, prompted_at, deadline_at, response_at,
                resolution: startup_explicit | prior_record | question_reply |
                question_reply_after_timeout | timeout_default | awaiting_input | unavailable},
                revision: session-audit/v2}
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<capability names>]
block_reason: <required only when gate_status is blocked>
```

The `audit_config_prompt` record fields have these meanings; this schema does not define their transitions:

| Field | Legal values / representation | Meaning |
| --- | --- | --- |
| `status` | `unasked`, `pending`, `answered`, `timed_out`, `unavailable`, `reused` | Recorded state of the configuration question. |
| `prompted_at`, `deadline_at`, `response_at` | Observed ISO-8601 UTC timestamp or `null` | Actual prompt time, its recorded deadline, and most recently observed user-reply time. |
| `resolution` | `startup_explicit`, `prior_record`, `question_reply`, `question_reply_after_timeout`, `timeout_default`, `awaiting_input`, `unavailable` | Recorded source or outcome for effective configuration. |

The selected workflow route owns the decision and any state transition; preserve the record as task state.

| `gate_status` | Mode and count | Allocations and lifecycle | Additional requirement |
| --- | --- | --- | --- |
| `awaiting-mode` | Unset | `[]`; top-level lifecycle `pending` | Initialize before recording the first explicit choice or default. |
| `awaiting-count` | Multi-Agent; count unset | `[]`; top-level lifecycle `pending` | Only an invalid explicit count enters this state; an omitted count defaults to one. |
| `released` — Single-Agent | Single-Agent; count `0` | `[]`; top-level lifecycle required | Releases the single route, not an independent Session. `timeout-default` is accepted only as a legacy source for readback. |
| `released` — Multi-Agent | Multi-Agent; locked positive count | Exactly `child_count` reserved allocations; `run_id` is set; each has a unique stable `allocation_id` and starts `agent: unbound`, `role: unassigned`, `slice_status: pending`, `lifecycle: pending` | Releases the route and count budget, **not** each child or Interaction Slice. |
| `blocked` | Preserve confirmed values | Preserve existing allocations/lifecycle | `unavailable_capabilities` and `block_reason` required; cannot enter a dependent route. |

An initial count reserves exactly that many unassigned slots; reservation does not select a role. A one-slot budget does not automatically assign Primary Output. After task context and Decision are reviewed, the role-selection owner supplies a role suggestion or Root decides directly; the selected unique role is then recorded on one unassigned slot. A concrete `slice_status: released` requires `role`, `interaction_slice`, `scope`, `mutations`, `return_conditions`, and an explicit boolean `write_content_memo`; pending slices may leave these fields unset. Before serializing each released Worker bundle, include `write_content_memo: true` or `false`; the Worker never infers a default. Child Creation may bind `agent` and lifecycle only after the target role and slice are released. A later slice may be prepared on the **same** created child without creating or recycling a slot.

`mode_source` and `source` record the current mode/count decision. The mode remains fixed within a conversation. A Count Gate-approved one-slot increase is the only same-conversation count change: set `mode_source: explicit` and `source` to the actual approval reference, and retain the previous source in `semantic_references`. The guarded reservation receipt records the old and approved counts and the reviewed approval reference. Do not infer approval from a suggestion or modify count without this transaction. New conversations never write `timeout-default`; accept that value only to read back legacy conversations created under the former rule. A legacy `timeout-default` record must remain Single-Agent with `child_count: 0` and `allocations: []`; never reinterpret or migrate it during readback. Allocation lifecycle may differ from top-level task lifecycle. Blocking preserves all confirmed values; later directives use the Re-entry owner for Fork or other re-entry and the Count Gate for the sole approved increase.

An unchanged initial record with `mode_source: default` must be Multi-Agent, `child_count: 1`, and exactly one reserved allocation; its reservation does not initialize a child. After a user-approved increase, the record's source becomes explicit. In every released Multi-Agent record, `child_count` equals the number of allocated slots. Each role and bound child identity is unique within the Session even after completion, failure, interruption, cancellation, or unavailability; lifecycle changes never release a role. Native import or recovery must reject duplicate roles or child identities. A Fork creates a new record only after fresh mode/count re-entry and never imports the source Session's child identities as current allocations. Actual child creation remains governed by the output-type and slice gates.

`session_audit` follows the field definitions in [session audit visibility](../session-runtime/session-audit-visibility.md). The root parent alone writes it. `audit_config_prompt.status` describes the recorded prompt state; its timestamps are actual UTC observations or `null`, and `resolution` identifies the recorded source/result. The selected route collects and updates these fields. Update log evidence only at first Worker need or on new actual capability/access evidence or failure, never per message. This state never changes `mode`, `child_count`, authorization, allocations, or slice release. Do not copy the complete Root audit record into policy files or Worker-controlled state. An actual `pending` state remains pending until resolved; missing persistence or a failed audit update is not evidence of a reply, default, or completion.

## Codex CLI / ChatGPT Desktop optimizations

In Codex, `AGENTS.md` is an instruction source, not a writable live mode/count record; hook events such as `SessionStart` and `SubagentStart` can refresh approved context only when configured and supported. Read back the actual parent record, allocated identities and epoch before route release; runtime status and hook events are not the canonical record. [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks), [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Codex `/agent` and `/status`, when exposed to the active Agent Session, provide runtime observations; `AGENTS.md`, optional local memories and `/compact` serve different purposes: project instructions, recall and chat condensation. None is the authoritative live mode/count/allocation/epoch record. After a Session resume, compact, or tool-mediated thread transfer, read the retained parent record before any new route release; `SessionStart` on `compact` can add approved context if an enabled/trusted hook actually runs but does not re-lock a count. [OpenAI: subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [OpenAI: memories](https://learn.chatgpt.com/docs/customization/memories), [OpenAI: hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code CLI / Claude Desktop optimizations

Maintain the structured mode, count, and slice record in the parent context and read it back before route release. `/tasks` output is only a temporary subagent status signal, not the canonical record.

Claude Code's `/tasks` lists observable current/background subagent work, whereas `/context` inspects loaded instruction/memory files. Neither is the canonical mode/count/allocation record, and `CLAUDE.md` and auto memory are **instruction or learning context**, not a place to rewrite the live task record. If the parent resumes a conversation after compaction or restart, read back its retained task record and validate the locked gate and current epoch before releasing a new slice. A configured `SessionStart` hook may provide approved initial context, but its output alone cannot create an allocation or overwrite the locked count. [Anthropic: memory](https://code.claude.com/docs/en/memory), [Anthropic: hooks](https://code.claude.com/docs/en/hooks), [Anthropic: subagent status](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary.md) — locate Worker snapshot and record access boundaries.
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate root mode confirmation ownership.
- [Coding Delegation Count Gate](delegation-mode-count-gate.md) — locate child-count gate ownership.
- [Coding Delegation Re-entry](delegation-mode-reentry.md) — locate mode/count re-entry ownership.
- [Coding Child Role Selection](child-role-selection.md) — locate the role-selection boundary before reservation.
- [Coding Execution Control](../execution-control/execution-control.md) — locate Interaction Slice field ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child lifecycle field ownership.
- [Coding Session Audit Visibility](../session-runtime/session-audit-visibility.md) — locate session audit configuration ownership.
- [Enhanced State Store](../enhanced-native-state/enhanced-state-store.md) — locate Native versus Enhanced persistent-record authority.
- [Native Reconciliation](../enhanced-native-state/native-reconciliation.md) — locate explicit Native-to-Enhanced Root reconciliation.
- [Native Authority Transfer](../enhanced-native-state/native-authority-transfer.md) — locate explicit Enhanced-to-Native Root authority transfer.
