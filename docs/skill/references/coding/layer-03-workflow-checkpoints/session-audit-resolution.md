# Session Audit Resolution

[English](session-audit-resolution.md) | [简体中文](session-audit-resolution_zh_cn.md)

This checkpoint owns applying current Session audit preferences to the parent-controlled record and confirming the resulting values. It does not make audit visibility a permission or execution gate.

## Trigger and inputs

After the canonical parent-context record is available, consume it and current Session audit facts. Apply [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md) for field values and display semantics, and [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md) for record ownership and shape.

## Decision and result

Use valid explicit preferences already supplied by the user or retained in the current parent-controlled record. Otherwise apply the defaults immediately: Root `balanced/milestone_only`; Worker `full`. The user may explicitly change any preference, and the parent records the effective values and whether they were explicit or default. Do not ask a mandatory first-use question. Do not start a timer, wait for a reply, or migrate older prompt-state values.

If the available record contains obsolete prompt/timing or migration fields, ignore those fields and preserve valid preference values. Do not infer a preference from obsolete prompt status. If current explicit values conflict or are invalid, request clarification only for the affected preference when appropriate; if it cannot be resolved, use the policy default and report the limitation rather than blocking unrelated work.

Worker-log visibility remains an evidence description. When a task depends on access to the complete safe Worker conversation record, report `available`, `unverified`, or `unavailable` only from actual access evidence; no Worker means `Not applicable` with a reason. If that evidence is required and unavailable or unverified, block only the dependent audit judgment. A returned final body or tool discovery alone does not prove full log access.

## Failure boundary

Preference collection is optional and never grants authorization. Continue using effective defaults if no preference was supplied. Preserve required progress reports and confidentiality rules. Block only a judgment that depends on required but missing audit evidence; report unavailable preference or Worker-log evidence without treating it as proof of completion.

## Related concepts

- [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md)
- [Coding Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md)
