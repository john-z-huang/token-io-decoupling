# Session audit resolution

[English](session-audit-resolution.md) | [简体中文](session-audit-resolution_zh_cn.md)

This checkpoint owns route-level audit configuration resolution, prompt and response handling, migration, timeout, and canonical readback.

## Trigger and inputs

Once the verified canonical Root record is available, consume it and the current Session audit facts. Apply [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md) for audit field values and display semantics, and [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md) for the audit record's supported states and resolution values.

## Decision and result

Resolve the canonical Root audit record by reusing valid explicit/completed settings, resuming an existing pending prompt with its original deadline, asking this checkpoint’s exact fixed question only when unasked, or clarifying only invalid/ambiguous fields. This checkpoint owns the fixed question and resolution procedure; Session Audit Visibility owns field values, defaults, and display semantics. Record the actual prompt timestamp, exact 60-second deadline, response timestamp, status, resolution, changed fields, source, and revision. A valid reply updates only selected Root fields; preserve a valid Worker value or default a missing one to `full`. After a verified timeout of at least 60 seconds with no observed reply, default Root to `balanced/milestone_only`, preserve a valid Worker cadence or fill a missing one as `full/default`, then read back the canonical record. Never classify an observed reply as timeout.

## Resolution procedure

This checkpoint defines and owns the exact prompt and resolution procedure over the canonical record verified by the preceding route action. [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md) remains authoritative for field values, defaults, and display semantics only.

   - **Audit record and migration.** Read the record. For known v1, preserve each valid value/source; if either Root field is `explicit`, reuse that pair and fill only a missing Root field from v2 defaults `balanced`/`milestone_only`; preserve valid Worker cadence or fill missing as `full/default`. If both Root sources are `default` and no completed prompt exists, ask once and retain old v1 values while pending. After the known mapping is resolved—immediately for a reusable explicit pair, or after a valid answer/true timeout for the pending default pair—apply the result and set `revision: session-audit/v2`. Invalid fields, same-field conflicts, or unknown revisions require targeted clarification; do not guess or reset unrelated fields.
   - **Reuse and resume.** Reuse valid explicit startup values or completed records; for a new explicit startup record `status: reused` and resolution `startup_explicit`, and for a reused completed record record `status: reused` and resolution `prior_record`. Preserve prompt, timing, and response evidence. For `pending`, never repeat the template: if `response_at: null`, resume waiting against the original deadline; if a reply was observed, continue focused correction from it and never auto-timeout.
   - **First question.** Ask only for `unasked` records that need a question, exactly once with this unchanged template:

     > Root audit preference for this Coding session? Choose one: **balanced/milestone_only** (recommended default), **economy/off** (lowest display visibility), or **full/full**. Or reply with `audit_mode=<economy|balanced|full>` and/or `root_reasoning_cadence=<off|milestone_only|full>` to customize those fields. Worker cadence stays at its valid recorded value, or defaults to `full` if missing. If you do not reply within 60 seconds, Root defaults to **balanced/milestone_only**; Worker cadence stays at its valid recorded value, or defaults to `full` if missing. This affects display and optional summaries only; it grants no authorization.

     Use an actually available and authorized asynchronous input capability when present; otherwise use ordinary user-visible text only if permitted. Record the actual observed UTC prompt time and exact 60-second deadline, set status `pending`, `response_at: null`, and resolution `awaiting_input`. Wait using input-interruptible intervals no longer than 60 seconds. Record `unavailable` instead of guessing if asking, timing, or interruptible bounded waiting is unavailable; block this gate while allowing independent work.
   - **Reply and clarification.** A valid reply updates only named Root fields with source `explicit`, sets status `answered`, and resolution `question_reply`; for a valid late reply use `question_reply_after_timeout`, preserve the timeout evidence, and apply it only to future messages without replay. A preset sets both Root fields; keyed free text updates named fields, with other missing Root fields defaulting to `balanced`/`milestone_only`. Set `response_at` to the actual observed reply time. An invalid/ambiguous reply stays `pending`; clarify only affected fields under the original prompt/deadline, update `response_at`, and never auto-timeout after any reply.
   - **Timeout and record check.** Set status `timed_out` and resolution `timeout_default` only if no reply was ever observed and a reliable clock confirms at least 60 seconds elapsed. Then set Root to `balanced`/`milestone_only` with source `default`; preserve a valid Worker cadence or fill a missing one as `full/default`. Read back values, sources, prompt fields, and revision. This preference does not change Mode/count or grant authorization.

## Multi-Agent audit evidence

When a Worker exists and log evidence is first needed, check once whether its complete safe conversation record is accessible and record the actual access evidence in `worker_log_visibility` and `worker_log_evidence`. Root return-body or tool existence alone does not prove access. Block only an audit depending on unavailable/unverified log evidence; otherwise report the limitation and read the complete actual return body. When no Worker exists, set `worker_log_visibility: Not applicable`, record why in `worker_log_evidence`, and do not infer a Worker log result.

## Failure boundary

If asking, reliable timing, interruptible waiting, state-record guards, or audit readback is unavailable, mark unavailable and block this gate and dependent work. Keep pending audit state recoverable. If canonical authority changes or reconciliation updates current facts, refresh current Context/Decision and return to the preceding state-resolution route action; do not reopen Mode or repeat a completed prompt.

## Related concepts

- [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md)
