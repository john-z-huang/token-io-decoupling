# Enhanced Host Binding

[English](enhanced-host-binding.md) | [简体中文](enhanced-host-binding_zh_cn.md)

This owner defines the trusted source of Enhanced identity and operation guards, role exposure, and per-call revalidation. It does not own route selection, mode/count, task policy, or cross-runtime model bindings.

## General rules

Protected operations require a trusted embedding to supply the current project, root-session and current-session identities, transport role, and actual permission/guard evidence. Recheck that binding and the guard required by the operation on every call, including after a tool has been listed. Revoked, missing, ambiguous, or insufficient evidence rejects the protected call and leaves Native work available where independently authorized.

Environment variables, client metadata, caller-supplied identity or paths, operation arguments, and fields such as `authorized=true` are not identity or permission evidence. Production defaults deny protected Enhanced access when no trusted provider is installed. Expose only the public read-only surface when unbound; expose the Root or Worker surface only for the corresponding verified binding and revalidate it per call. A Worker binding grants no access to another Worker or Root-only data.

Keep evidence claims scoped: a fake provider verifies service behavior against a test contract; an SDK or stdio subprocess verifies protocol behavior. Neither demonstrates that a real host supplies attestation or enforces an OS permission boundary. Do not claim real-host verification without direct evidence from that host.

## Codex CLI / ChatGPT Desktop optimizations

The current production CLI does not install a trusted host provider, so its protected operations remain denied by default. For each task, inspect the capabilities and evidence actually exposed and authorized in the current Session: if a trusted provider supplies verifiable identity and sufficient operation guards, apply the general per-call checks; otherwise mark that capability unavailable/unverified and do not make the protected call. New runtime capabilities can be used when directly exposed, authorized, and verified under the same checks; ordinary users do not need to edit this Skill first. SDK subprocess tests and fake bindings remain protocol/contract evidence only. Never use Computer Use to inspect a desktop or manufacture identity evidence.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific host-binding optimization. Follow the general rules; do not infer that a trusted provider exists.

## Related concepts

- [Enhanced Workflow Availability](enhanced-workflow-availability.md) — owns choosing Enhanced versus Native disposition.
- [Runtime and Model Provider Support](runtime-provider-support.md) — owns cross-runtime and model/effort bindings.
- [Coding Delegation State Record](delegation-state-record.md) — owns persisted identity-linked state and Worker lifecycle.
