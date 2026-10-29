# Codex MCP caller matching

[English](CODEX_CALLER_CONTEXT.md) | [简体中文](CODEX_CALLER_CONTEXT_zh_cn.md)

This document owns the implementation contract and development verification of optional Codex request matching. Matching constrains an already verified host binding; it does not authenticate a Session, assign a role, establish a parent relationship, or supply an operation guard.

## Source contract

Read-only inspection of the local Codex source snapshot `bb8f5304fcd9f901d8e0747fccb8c8904cbc504e` established these facts:

- `codex-rs/core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta` adds `threadId` and `sessionId` to the tool request's top-level `_meta`. These are distinct fields; neither supplies a Root/Worker role or parent relationship.
- `augment_mcp_tool_request_meta_with_sandbox_state` and `codex-rs/codex-mcp/src/sandbox_metadata.rs::augment_metadata` can additionally forward opaque sandbox state when a server advertises the relevant capability. State and launcher information are separate. This caller matcher neither requests those capabilities nor interprets or executes launcher information.

These are source facts, not evidence that the currently connected client runs that revision or supplies a trusted binding. Deployment must verify the actual client's wire behavior and its identity and permission boundaries separately. Codex source remains unmodified by this integration.

## Enablement and authority

A trusted supervisor can launch `token-io-decoupling start-mcp-server --profile root --host-fd N --codex-context` (or another selected profile executable), using the authenticated inherited channel described in the [development guide](DEVELOPMENT.md#authenticated-host-channel). `--codex-context` requires a usable host channel. The equivalent Python factory option is `require_codex_context=True` on `create_server`, with a verified provider.

The MCP SDK's request context supplies the two fields. The matcher requires bounded, nonempty strings and rejects malformed or missing context. `threadId` must exactly equal the verified provider's `current_session_id`. `sessionId` is opaque context; a change does not reset canonical identity, Mode/count, Run, or database state. The provider remains the source of project, Root, current Session, role, capabilities, and guards. Tool payloads, environment variables, and client names cannot replace request context or establish that authority.

Each protected Root/Worker callback and bound schema diagnostic runs inside its own caller scope. Every binding read used by the state service rechecks the current request against a fresh provider result. Scopes are reset on return or error and isolated across concurrent requests. No request may borrow a preceding or concurrent request's identity. A mismatch fails before state paths are inspected or mutated. Public rule and capability reads remain available.

Unrelated `_meta` fields are ignored. Caller metadata is not persisted in SQLite or emitted in error bodies. Missing or revoked provider evidence still rejects operations even when the strings match. This option does not provide the missing real-host attestation, sandbox enforcement, or privileged supervisor installation.

## Supported client boundary

The MCP Server supports only Codex and ChatGPT Desktop, as required by the [MCP development instructions](AGENTS.md). This matcher consumes the Codex request contract only when the actual supported client exposes it. Unsupported Code Agents have no adapter or fallback integration here. Client identity, hook input, and environment values alone do not satisfy host authentication or operation guards.

## Development verification

Tests must exercise real MCP SDK request metadata rather than placing these fields inside tool arguments. Cover Root and Worker calls and persistence readback; missing, malformed, and mismatched callers; public-read availability; concurrent isolation; changed opaque `sessionId`; provider identity changes between reads; and rejection before filesystem effects. Retain exact tool-schema and inventory checks: SDK context must not become a user-supplied tool parameter.

Synthetic providers and peer-authentication overrides are test evidence only. They do not verify the actual client's attestation, parent graph, sandbox, or current-session database access. Run the locked checks in the development guide after changes.

## Related concepts

- [MCP development guide](DEVELOPMENT.md)
- [Enhanced Host Binding](../references/coding/layer-01-fundamental-concepts/enhanced-native-state/enhanced-host-binding.md)
- [Enhanced State Store](../references/coding/layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md)
