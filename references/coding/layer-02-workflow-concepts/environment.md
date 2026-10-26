# Environment Checkpoint

[English](environment.md) | [简体中文](environment_zh_cn.md)

## Actions

1. Read explicit runtime metadata in the current system, developer, and application context. Use a named supported runtime as the primary fact.
2. Use the callable tool inventory, workspace roots, permission profile, sandbox details, and other exposed task metadata as corroborating evidence. A local shell, worktree, model name, or tool pattern alone does not uniquely identify the runtime environment.
3. If authorized by the current task, inspect only non-sensitive runtime metadata exposed by local process or environment information; never print or persist credentials or tokens.
4. Do not use a browser, GUI navigation, screenshots, or visual page content to identify the runtime environment.
5. Classify the runtime environment into exactly one branch defined by [Runtime and Model Provider Support](../layer-01-fundamental-concepts/runtime-provider-support.md).
6. If the runtime environment does not fit any branch, mark the environment unsupported and stop work that depends on it.
7. If the evidence still leaves the runtime environment ambiguous, stop the dependent work and return that reference's exact fallback question to the user.

## Optional Enhanced eligibility

After classifying the runtime, determine whether this task actually needs optional Enhanced operations. If not, record `Not applicable` with that reason and continue Native. If it does, consume [Enhanced Workflow Availability](../layer-01-fundamental-concepts/enhanced-workflow-availability.md) and [Enhanced Host Binding](../layer-01-fundamental-concepts/enhanced-host-binding.md): inspect only directly exposed trusted identity and operation-guard evidence, record the evidence and its scope, and keep unknown or absent evidence unavailable. Public rule access is not proof of protected state or write access. Do not initialize or open workflow state here; that follows the completed Mode and Session gates. If Enhanced is required and its binding is missing or insufficient, block that dependent work and report the missing capability; keep independent Native work available.

## Pass condition

The actual runtime environment is uniquely classified from explicit metadata, or the user has supplied the fallback clarification. If Enhanced is needed, its selection and required trusted binding evidence are recorded; otherwise the Native `Not applicable` disposition is recorded.

## Boundary

This checkpoint does not choose an execution mode, bind a model to a role, authorize delegation, implement changes, or claim that an unobserved operation was performed.

## Related concepts

- [Coding Session Model](../layer-01-fundamental-concepts/session-model.md) — locate Session topology ownership.
- [Coding Context Exchange Workspace Boundary](../layer-01-fundamental-concepts/context-exchange-workspace-boundary.md) — locate filesystem and worktree capability ownership.
- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation.md) — locate mode-gate capability consumers.
- [Enhanced Workflow Availability](../layer-01-fundamental-concepts/enhanced-workflow-availability.md) — locate optional path selection and unavailable disposition.
- [Enhanced Host Binding](../layer-01-fundamental-concepts/enhanced-host-binding.md) — locate trusted identity and operation-guard evidence.
