# Coding Workflow Module Contract

[English](workflow-module-contract.md) | [简体中文](workflow-module-contract_zh_cn.md)

This owner defines the reusable contract for invoking and resuming one bounded workflow module. It does not select a route, schedule other modules, grant authorization, or define module-specific policy.

## General rules

### Module declaration

Before invocation, a module declares its purpose and scope, applicable mode, required authorization and current Session facts, prerequisite evidence and freshness/epoch requirements, permitted effects, and the ordered Layer-01 through Layer-03 owners it consumes. It identifies its own output and the conditions that make each result valid. A module must not depend on route coordinates or invoke another module.

The caller provides the task Contract, current route/mode decision when applicable, authorized scope, current Session identity/state, evidence and epochs, and known effects. The caller may be the top-level route or the direct caller invoking one module; direct entry does not require a pre-existing route. On a first direct invocation, the caller establishes a continuation record in its available context before an effect or suspension, including the module/substep, authorized scope, known evidence, and effect status. The module checks only the facts its declaration requires. It may obtain a missing fact through an authorized read-only operation when the source is current and available. A write that establishes a prerequisite requires its own existing authorization; module entry does not supply it.

### Results and resume evidence

Return exactly one semantic result:

- `complete`: this module's declared work is complete and every required owner result has passed its current condition. Include the evidence, effects, and epochs produced or confirmed. A pending prompt, pending audit, unresolved prerequisite, or incomplete owner result is not `complete`. This does not grant authority or mean the complete route is accepted.
- `not_applicable`: a declared conditional trigger is absent. Include the observed evidence and reason; do not silently skip the condition.
- `needs_prerequisite`: identify each missing prerequisite by its semantic owner and evidence requirement, and record the suspended module/substep for the caller.
- `blocked`: explain the unresolved conflict, unavailable required evidence/capability, unsafe state, or other blocking condition.

For resumable work, the caller preserves the pending module and substep, completed evidence with source/currentness/epoch, and the status of effects already attempted or completed. Resume from that recorded position after the caller supplies the required evidence. Recheck affected epochs and effect state before continuing; do not repeat a completed prompt, creation, write, or Git operation automatically. A pending owner operation remains pending until its owner-defined completion evidence is confirmed. A first invocation without prior continuation history is not a failure: the direct caller establishes the record. If a prior effect is uncertain, use an already authorized readback to resolve its status before retrying; block only if the caller cannot preserve or recover the position, cannot determine the effect status, or cannot resume safely.

### Caller boundary

The caller maps `needs_prerequisite` to the relevant prerequisite owner and resumes the pending module after that evidence is available. The direct caller can perform this continuation itself; a top-level route is not required. It must not restart unrelated completed gates or repeat Mode selection. A repeated prerequisite resolution with no new evidence, relevant epoch progress, or valid owner-state change is a loop; legitimate owner-directed repair and re-verification may continue when their evidence/epochs advance. If a required continuation position cannot be preserved or recovered, caller state is contradictory, or an attempted effect cannot be resolved by authorized readback, return `blocked`; do not guess or replay. Modules report their own result to the caller and never route to sibling modules or claim route-level completion.

## Codex CLI / ChatGPT Desktop optimizations

There are currently no Codex CLI or ChatGPT Desktop-specific optimizations for this concept. Follow the general rules.

## Claude Code CLI / Claude Desktop optimizations

There are currently no Claude Code CLI or Claude Desktop-specific optimizations for this concept. Follow the general rules.

## Related concepts

- [Coding Execution Planning](execution-planning.md)
- [Coding Execution Decision Gate](execution-decision-gate.md)
- [Coding Execution Control](../execution-control/execution-control.md)
- [Coding Delegation State Record](../delegation/delegation-state-record.md)
