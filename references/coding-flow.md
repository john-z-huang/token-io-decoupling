# Coding Flow

This Flow covers project exploration, planning, implementation, refactoring, fixes, code/config materialization, builds, tests, debugging, independent change verification, optional documentation/comments materialization, and all non-trivial repository Git work. Detailed Coding rules live in independent modules under `references/coding/`; this file is only the stable Coding routing/assembly entrypoint and does not duplicate module-internal policy.

All Coding roles also follow [`shared-protocols.md`](shared-protocols.md).

## Module registry and maintenance rule

[`coding/owner.md`](coding/owner.md) is the **ownership registry** for Coding functional modules under `references/coding/`. It records which semantics each module owns, which semantics it explicitly does not own, and the boundaries with documents outside the directory such as `coding-flow`, `shared-protocols`, and `references/runtime/**`.

Whenever the **functional responsibility, definition boundary, split/merge relationship, or ownership relationship** of any module under `references/coding/` changes, the same change must update both `coding/owner.md` and its Chinese mirror `coding/owner_zh_cn.md`. A change that only adjusts details inside an already registered ownership boundary does not require a mechanical registry edit.

Register the responsibility boundary in the owner registry before adding a new Coding module. If two modules are found to define the same semantic rule, use the owner registry to preserve one authoritative definition and remove the duplicate body from the non-owner document or replace it with a minimal reference.

The owner registry is maintenance/routing metadata, not a runtime module that must be loaded for every Coding task. Load it when determining rule ownership, changing Coding documentation structure, or changing module responsibilities.

## Module loading

After Coding Flow is selected, load modules as required by the task:

1. Load [`coding/session-model.md`](coding/session-model.md) to establish role and Session semantics.
2. Load [`coding/runtime.md`](coding/runtime.md) to resolve the registered Runtime deployment for the current environment.
3. Load [`coding/execution-control.md`](coding/execution-control.md) before substantive implementation, refactoring, debugging, build/test work, or other execution that may cross semantic decision boundaries.
4. Load [`coding/context-exchange.md`](coding/context-exchange.md) when the task uses multiple independent Coding Agents, needs reusable cross-Agent context, requires Worker replacement/escalation handoff, or needs parent-led multi-Worker rendezvous. Whenever an independent Worker uses file-backed Context Exchange, also load [`coding/content-memo.md`](coding/content-memo.md).

Purely bounded exploration may defer `execution-control.md` until execution begins. A Single-Session Coding task that never creates another Coding Agent does not need to load `context-exchange.md` or `content-memo.md` unless file-backed recovery/context transport is actually useful.

`runtime.md` loads only the registered deployment document matching the current environment; do not preload all of `references/runtime/`. If a relevant Coding module is already loaded and its rules remain valid, do not reread it. Load modules by responsibility rather than preloading the whole `references/coding/` directory.

## Flow assembly boundary

`session-model.md` owns roles, Session topology, and role independence; `runtime.md` resolves Host/model bindings; `execution-control.md` owns execution release, Interaction Slices, checkpoints, verification, and Git-operation gates; `context-exchange.md` owns cross-Worker context transport and handoff; `content-memo.md` owns Worker Context Exchange prose and content-memo policy.

This entrypoint only decides **when to load and compose those modules**. Do not infer new role, Session, checkpoint, Context Exchange, or Runtime rules from this summary; detailed semantics are authoritative in the owning module. See [`coding/owner.md`](coding/owner.md) for the ownership registry.

## Boundary with Multimodal Flow

Ordinary Coding tasks remain in this Flow. Switch to or begin with Multimodal Flow only when the task truly requires continuous GUI Observation, large image/screenshot sets, video frames, design references, or other high-volume visual world state.

If Multimodal Flow has completed visual analysis and code changes are needed, Coding Flow receives only its narrow Handoff Contract. Do not replay complete image sets, video frames, Computer Use history, OCR text, or full visual-analysis history into the Primary Execution Session merely to implement code.

Multimodal Flow architecture and deployment rules remain owned by its own routed references; Coding Runtime changes must not silently redefine them.
