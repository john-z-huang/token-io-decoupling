# Workflow module entry resolution

[English](module-entry-resolution.md) | [简体中文](module-entry-resolution_zh_cn.md)

This checkpoint owns readiness resolution for an invocation of one bounded workflow module. It processes the caller's declared requirements; it does not select or enumerate modules, define Layer-04 module contracts, or schedule routes.

## Trigger and inputs

Use when a caller requests a module to begin or resume work. The caller supplies the task and authorized scope, the applicable released route/mode evidence, the module's declared prerequisite owners and evidence requirements, current Session state, relevant evidence and epochs, the suspended position if resuming, and the status of prior effects. A first direct invocation may have no continuation history or top-level route; the current caller can establish continuation in its available context. Apply [Workflow Module Contract](../layer-01-fundamental-concepts/execution-planning/workflow-module-contract.md), plus the relevant [Contract](../layer-02-workflow-concepts/entry-and-context/contract.md), [Environment](../layer-02-workflow-concepts/entry-and-context/environment.md), [capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md), [Mode](../layer-02-workflow-concepts/entry-and-context/mode.md), and direct prerequisite owners.

## Decision and result

1. Confirm the requested scope and applicable mode are current and authorized. A released Mode is evidence to consume, not a reason to ask again or change the route. Do not repeat a completed prompt or effect.
2. Check only the declared prerequisites and the caller's suspended position. Verify evidence source, freshness, relevant epoch, required capability, and effect status against their direct owners. If an authorized read-only source can establish missing evidence, retrieve only that bounded evidence and record its provenance.
3. Return `ready` with the verified evidence, current epochs, and permitted-effect boundary when the module can safely start or resume. `ready` is only the entry preflight result; the module must still return its own `complete`, `not_applicable` with reason, `needs_prerequisite`, or `blocked` result. An unresolved pending owner result is not ready for dependent work and cannot be treated as complete. Readiness is not authorization beyond the caller's existing scope and does not imply module or route completion.
4. Return `needs_prerequisite` with the semantic owner, missing evidence, and suspended module/substep when required evidence is missing but no block condition applies. The caller, including a direct caller without a top-level route, decides where to resume; this checkpoint does not route to a module or restart unrelated gates.
5. Return `blocked` when authorization or mode conflicts, a required capability/evidence source is unavailable, a required continuation position cannot be preserved or recovered, caller state is contradictory, prerequisite resolution repeats without new evidence/relevant epoch progress/valid owner-state change, or prior effect status cannot be resolved by authorized readback. The absence of continuation history on first entry is not by itself a block. Preserve the current state and do not retry, replay, or infer a safe continuation. Owner-directed repair and re-verification may continue when their evidence or epochs advance.

## Failure boundary

This checkpoint may verify or obtain authorized read-only evidence. The current caller may establish a continuation record on first direct entry; this checkpoint does not require a route or external persistence mechanism. It does not create or mutate a prerequisite, expand scope, reselect Mode, issue prompts, create Agents, dispatch work, perform Git operations, or choose a later module. Any write needed to establish a prerequisite requires its existing authorization and must return through the caller's normal gate. Missing or stale evidence blocks only the dependent module work; it does not authorize skipping its declared owner.

## Related concepts

- [Workflow Module Contract](../layer-01-fundamental-concepts/execution-planning/workflow-module-contract.md)
- [Contract](../layer-02-workflow-concepts/entry-and-context/contract.md)
- [Environment capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md)
- [Mode](../layer-02-workflow-concepts/entry-and-context/mode.md)
