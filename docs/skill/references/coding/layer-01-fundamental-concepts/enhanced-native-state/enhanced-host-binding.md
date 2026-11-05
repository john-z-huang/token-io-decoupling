# Enhanced Host Binding

[English](enhanced-host-binding.md) | [简体中文](enhanced-host-binding_zh_cn.md)

This owner defines local Enhanced session scope, role registration and per-operation checks. Binding here is application registration, not independent host authentication or OS isolation. It does not own mode, count or route selection.

## General rules

### Local registration and operation scope

Use the process's fixed project scope, current request session identifier and recorded allocations. State calls must check role, owning Root, own Worker assignment, database identity, paths, revision, idempotency and independent authorization. Reject missing, conflicting or out-of-scope inputs. Do not require an additional privileged host, external identity provider or unverifiable guard proof, and do not fill every guard to pretend it was verified.

Root registration of a Worker requires an approved role and released Slice. Allocation records are application relationships, not attestation of real runtime parent-child identity. An unknown thread must explicitly open its own Root workflow before using that state; multiple Root registrations for one thread block. Re-read current allocations per call and restore request scope on return/error.

### Trust boundary

Metadata supplies local routing only. Payloads, environment variables, profiles and `authorized=true` cannot replace operation authorization. The same OS user can edit local data or forge metadata; this design does not defend against that user's malicious processes or provide independent process authentication or OS-level Worker isolation. Actual file access remains subject to OS permissions. Historical verified/trusted/guard field names do not expand this guarantee.

Native Coding responsibility does not automatically register an MCP Worker. Independently authorized Native work remains available when Enhanced is unselected or its dependencies are unavailable. Transfer of existing canonical state follows its current owner; never recreate or overwrite records. Synthetic and protocol tests prove tested behavior, not host authentication.

## Codex CLI / ChatGPT Desktop optimizations

### Local stdio

Standard local Codex CLI stdio derives the project partition from canonical startup cwd and reads MCP `_meta.threadId/sessionId`. State calls require bounded nonempty metadata and a safe thread component; changing opaque sessionId does not reset the thread. Root registers Workers through existing allocation operations; Workers resolve scope from existing allocations in the current project. Inspect capabilities and separate configuration before calls; no privileged-channel startup step is needed.

Source: `core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta`; the [official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp) describes stdio registration. Use only actual exposed, authorized call paths; Computer Use is forbidden. This optimization supports local Codex CLI only.

## Claude Code CLI / Claude Desktop optimizations

### Not applicable

The [official MCP documentation](https://code.claude.com/docs/en/mcp) describes stdio there too, but this does not establish the same metadata contract. This repository's MCP does not support that direct client and adds no adapter. Document users may continue general rules and independently authorized Native work; absence of this optimization does not block unrelated work.

## Related concepts

- [Enhanced Workflow Availability](enhanced-workflow-availability.md)
- [Enhanced State Store](enhanced-state-store.md)
- [Delegation State Record](../delegation/delegation-state-record.md)
