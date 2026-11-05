# Enhanced Workflow Availability

[English](enhanced-workflow-availability.md) | [简体中文](enhanced-workflow-availability_zh_cn.md)

This owner defines when the optional Enhanced path may be selected and how to disposition unavailable capability. It does not own runtime identity proofs, mode/count, state lifecycle, or Native reconciliation.

## General rules

Native remains the default route, subject to its own required records, permissions, and capabilities. Enhanced is an optional capability choice, never an implicit consequence of public rule access or a product/runtime classification. Select Enhanced only for a task that needs its stateful operations and only after the [local binding](enhanced-host-binding.md) owner confirms current request scope, registered role, paths and operation authorization.

When Enhanced is not selected and has never become canonical, record `Not applicable` with the reason and continue the Native route when its requirements are met. If an established Enhanced Root store is canonical, missing service access or a route preference does not make Native writable: use [Native Authority Transfer](native-authority-transfer.md) and block dependent writes until transfer is complete. A switch from a canonical Native record to Enhanced requires [Native Reconciliation](native-reconciliation.md) before dependent Root writes. API-advice failure alone leaves an otherwise healthy Enhanced state service available. Do not discard, silently overwrite, or reset valid records, bypass a hard constraint, or infer an Enhanced capability.

Coding Mode and its count remain governed by their existing owners. Availability does not select, reopen, or change them. Public access to a rules context establishes only that the rules can be read; it proves neither current session scope, database availability, nor permission to perform protected operations.

## Codex CLI / ChatGPT Desktop optimizations

Standard local stdio supports state operations. Confirm current request scope, allocations and independent authorization under the [binding owner](enhanced-host-binding.md). No privileged host proof is required. Computer Use is forbidden; unexposed capabilities remain unavailable.

## Claude Code CLI / Claude Desktop optimizations

This MCP optimization is not applicable and adds no direct client support. Independently authorized Native document workflows remain available.

## Related concepts

- [Enhanced Host Binding](enhanced-host-binding.md) — owns current session scope and operation guards.
- [Native Authority Transfer](native-authority-transfer.md) — owns safe return to Native after Enhanced becomes canonical.
- [Native Reconciliation](native-reconciliation.md) — owns Native-to-Enhanced Root reconciliation.
- [Coding Delegation State Record](../delegation/delegation-state-record.md) — owns persisted workflow state and mode/count records.
- [Coding Execution Control](../execution-control/execution-control.md) — owns Slice release and Control decisions.
