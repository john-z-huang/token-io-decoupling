# Coding Environment Capability Inventory

[English](environment-capability-inventory.md) | [简体中文](environment-capability-inventory_zh_cn.md)

This module owns the capability inventory for an already-classified runtime environment: exposed capabilities, unknown capability handling, dependent-route blocking, and branch-specific capability use. It does not classify the environment, choose execution mode, bind roles, authorize delegation, authorize implementation, or define task policy.

## Exposed capability inventory

Record only capabilities directly exposed by the current surface: model identity and parameter controls, Session topology, filesystem and sandbox access, tools, connectors, authentication, and any available return path for delegated work.

## Unknown capability and route blocking

Mark an unobserved capability as unknown. Do not substitute another runtime environment, model, parameter, Session, tool, permission, or inferred capability. Any required capability that is missing or unknown blocks the dependent slice.

## Branch-specific capability use

Routes consume this inventory and state only for their topology-specific deltas. On Local Codex, use the exposed model/session controls and restart after changing global instructions, overrides, the Skill, or repository instructions. On ChatGPT Work, use only explicitly exposed models, Sessions, files, connectors, and execution tools. On Standard ChatGPT, do not assume local execution, Git, worktrees, or independent Sessions.

## Related concepts

- [Coding Session Model](../layer-01-fundamental-concepts/session-model.md) — locate Session topology ownership.
- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership.md) — locate role responsibility ownership.
- [Coding Context Exchange Workspace Boundary](../layer-01-fundamental-concepts/context-exchange-workspace-boundary.md) — locate filesystem and worktree capability ownership.
- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation.md) — locate mode-gate capability consumers.
- [Coding Delegation Count Gate](../layer-01-fundamental-concepts/delegation-mode-count-gate.md) — locate count-gate capability consumers.
