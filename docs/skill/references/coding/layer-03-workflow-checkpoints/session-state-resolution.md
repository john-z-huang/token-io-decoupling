# Session State Resolution

[English](session-state-resolution.md) | [简体中文](session-state-resolution_zh_cn.md)

This checkpoint owns the route-level confirmation of the current Session facts and canonical parent-controlled workflow record before audit preferences are applied. It does not own audit values or mode/count policy.

## Trigger and inputs

Consume released Mode/count and current Session identity, role, and Context Firewall facts. Apply [Session Model](../layer-01-fundamental-concepts/session-runtime/session-model.md), [Session Role Ownership](../layer-01-fundamental-concepts/session-runtime/session-role-ownership.md), [Session Context Firewall](../layer-01-fundamental-concepts/session-runtime/session-context-firewall.md), and [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md).

## Decision and result

1. Confirm the released Mode/count and current Session facts. Missing or conflicting mode, identity, role, or Context Firewall evidence blocks dependent work before any protected operation.
2. Read the canonical parent-controlled record from its authoritative conversation context. Preserve existing mode, count, allocations, approved task scope, and lifecycle values; do not reconstruct or overwrite missing/conflicting history from a tool result, hash, or stale summary.
3. Confirm the record agrees with the released Mode/count and current known allocation state. Apply the owner-defined role and path checks before any gated operation. A worker assignment, Slice release, task authorization, and creation/dispatch remain distinct facts and must each be verified under their owners.
4. Read back and return the current record and evidence to the route. This readback does not grant authority or release a Slice, does not establish cross-call sequencing, and does not establish audit preferences.

## Failure boundary

If current identity, role, firewall, released mode/count, or canonical record cannot be verified, block the dependent protected operation. Do not substitute a database, infer a replacement record, or treat a structural evaluation result as canonical state. Independent authorized work may continue when it does not rely on the missing facts.

## Related concepts

- [Session Model](../layer-01-fundamental-concepts/session-runtime/session-model.md)
- [Coding Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md)
