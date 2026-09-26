# Coding Environment Capability Inventory

[English](environment-capability-inventory.md) | [简体中文](environment-capability-inventory_zh_cn.md)

This module owns the capability inventory for an already-classified runtime environment: exposed capabilities, unknown capability handling, and dependent-route blocking. Branch definitions and model bindings belong to [Runtime and Model Provider Support](../layer-01-fundamental-concepts/runtime-provider-support.md). This module does not classify the environment, choose execution mode, bind roles, authorize delegation, authorize implementation, or define task policy.

## Exposed capability inventory

Record only capabilities directly exposed by the current surface: model identity and parameter controls, Session topology, filesystem and sandbox access, tools, connectors, authentication, and any available return path for delegated work.

## Unknown capability and route blocking

Mark an unobserved capability as unknown. Do not substitute another runtime environment, model, parameter, Session, tool, permission, or inferred capability. Any required capability that is missing or unknown blocks the dependent slice.

## Route consumption

Routes consume this inventory and state only for their topology-specific deltas. Apply branch-specific controls and model bindings from [Runtime and Model Provider Support](../layer-01-fundamental-concepts/runtime-provider-support.md).

A profile required by a route is a capability requirement, not a product-wide availability claim. A branch-specific route may consume that profile only after this inventory records the current surface's actual model identity and every parameter required by that profile. If a required model or parameter is not exposed or is unknown, record the requirement in `unavailable_capabilities` and block the dependent slice or route. Do not silently substitute a model, reasoning effort, Session, tool, permission, or mode/count; choosing a different route requires re-entering its applicable gate and obtaining new explicit confirmation. This keeps Core rules decoupled from product details while allowing a route to consume its required, surface-specific profile.

## Related concepts

- [Coding Session Model](../layer-01-fundamental-concepts/session-model.md) — locate Session topology ownership.
- [Coding Session Role Ownership](../layer-01-fundamental-concepts/session-role-ownership.md) — locate role responsibility ownership.
- [Coding Context Exchange Workspace Boundary](../layer-01-fundamental-concepts/context-exchange-workspace-boundary.md) — locate filesystem and worktree capability ownership.
- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation.md) — locate mode-gate capability consumers.
- [Coding Delegation Count Gate](../layer-01-fundamental-concepts/delegation-mode-count-gate.md) — locate count-gate capability consumers.
