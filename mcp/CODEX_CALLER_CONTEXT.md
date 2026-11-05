# Codex MCP local session context

[English](CODEX_CALLER_CONTEXT.md) | [简体中文](CODEX_CALLER_CONTEXT_zh_cn.md)

This document owns project, thread and role scoping for local stdio requests. These identifiers are not independent authentication or OS isolation.

## Installation and calls

Standard `setup codex` registers four local stdio profiles. No privileged service, inherited host descriptor or external identity provider is required; the old `--host-fd` and `--codex-context` options are removed. Start Codex from the intended project directory. The MCP captures its canonical path at startup and derives the project partition with SHA-256.

Codex supplies `threadId` and `sessionId` in top-level MCP request `_meta`. State operations require bounded nonempty strings; the thread must also be a safe path component. Do not put these fields in tool payloads. `sessionId` is opaque and a change does not reset thread state. Public capability, rule and configuration diagnostics need no session metadata. Capability details `support.local_stdio` and `runtime.binding` distinguish local support from current request context; reporting does not probe every dependency.

## Allocation and permissions

Root must register Workers through the existing reserve, slice and `delegation_bind` sequence. Registration is an application record, not host attestation of a real parent-child relationship. Workers resolve their Root from existing allocations and Worker state in the current project and access only their own assignment. Multiple Root registrations, mismatched database identities and unsafe paths reject. A previously unknown thread must explicitly open its own Root workflow before using that state; a profile does not prove a role. ContextVar scopes reset on return/error and do not borrow concurrent request context.

Traversal, derived symlinks, database identity, role, allocation lifecycle, revision, idempotency and independent materialization-grant checks remain enforced. API requests still require configuration and per-call outbound authorization. Capability fields are not user permission.

## Trust boundary and verification

The same OS user can edit local files or send metadata directly. This service does not defend against that user's malicious processes and does not claim independent process authentication or OS-level Worker isolation. The trust boundary is the user's approved local Codex/MCP configuration and actual OS permissions. Internal Python injection is an embedding/test seam, not a standard-install prerequisite.

Only local Codex CLI is supported. Source `core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta` supplies thread metadata; the [official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp) describes local stdio registration. Local regressions cover missing metadata, role mismatch, unsafe paths and concurrency. Follow the development guide for installed-package and fresh-CLI checks; synthetic identifiers are not authentication evidence.

## Related concepts

- [Development guide](DEVELOPMENT.md)
- [Enhanced Host Binding](../docs/skill/references/coding/layer-01-fundamental-concepts/enhanced-native-state/enhanced-host-binding.md)
