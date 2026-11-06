# Codex MCP local session context

[English](CODEX_CALLER_CONTEXT.md) | [简体中文](CODEX_CALLER_CONTEXT_zh_cn.md)

This document owns the local stdio application-scope and request-metadata boundary. These identifiers are not independent authentication or OS isolation.

## Installation and calls

Standard `setup codex` registers the two current standalone local stdio executables: workflow and tools, each with no startup arguments. No privileged service, inherited host descriptor or external identity provider is required; the old `--host-fd` and `--codex-context` options are removed. Start Codex from the intended project directory. The MCP captures its canonical path at startup for project-scoped checks. Stateless rule and workflow calls do not persist a project partition.

Codex supplies `threadId` and `sessionId` in top-level MCP request `_meta`. Operations that use request metadata require bounded nonempty strings; path-using operations additionally validate the relevant path. Do not put these fields in tool payloads. `sessionId` is opaque and does not authenticate the caller. Public capability, rule and configuration diagnostics need no session metadata. Capability reports describe configured support; they do not prove identity, permission, or every dependency.

## Allocation and permissions

Stateless navigation and structural evaluation do not store allocation, role, or workflow state. Supplied identities, assignments, evidence pointers, and hashes are caller facts and do not attest a real parent-child relationship or grant permission. Each protected operation must apply its own current role, path, grant, and authorization checks.

`materialize_decoupled_output` requires a trusted startup-injected authorization provider, matching per-call Worker binding, independent operator grant, pinned roots, and current preflight. The tool payload cannot choose the provider or supply authority. No standard provider is configured, so the operation is unavailable by default.

## Trust boundary and verification

The same OS user can edit local files or send metadata directly. This service does not defend against that user's malicious processes and does not claim independent process authentication or OS-level Worker isolation. The trust boundary is the user's approved local Codex/MCP configuration and actual OS permissions. Internal Python injection is an embedding/test seam, not a standard-install prerequisite.

Only local Codex CLI is supported. Source `core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta` supplies thread metadata; the [official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp) describes local stdio registration. Local regressions cover missing metadata, role mismatch, unsafe paths and concurrency. Follow the development guide for installed-package and fresh-CLI checks; synthetic identifiers are not authentication evidence.

## Related concepts

- [Development guide](DEVELOPMENT.md)
- [Session Role Ownership](../../../../../instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/session-runtime/session-role-ownership.md)
