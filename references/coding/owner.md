# Coding Documentation Ownership Registry

This file only registers the **definition ownership and boundaries** of modules under `references/coding/`. It answers “which document should define this Coding rule?” It is not an execution specification for Coding Flow and does not repeat the full rules owned by each module.

## Ownership principles

- Every stable Coding semantic rule should have one primary owner.
- A non-owner document may reference a rule for routing, prerequisites, or result consumption, but should not duplicate the full normative definition.
- When two modules define the same semantic rule, use this registry to identify the owner first; keep the authoritative definition there and replace the other copy with a minimal reference or remove it.
- If a new rule does not naturally fit an existing owner, update this registry or split out a specialized module before writing the normative rule. Do not place it opportunistically in the nearest long document.
- English and Chinese mirror files have the same semantic ownership; `*_zh_cn.md` is not a separate owner.

## `runtime.md` / `runtime_zh_cn.md`

**Owns:**

- the Coding Runtime Contract;
- resolution of Core Coding roles into Host Adapter + Model Profile;
- Core boundaries for runtime capability resolution, deployment selection, downgrade, and unavailable handling;
- host-neutral constraints for binding Coding roles to runtimes.

**Does not own:**

- commands, tools, Session creation mechanics, or product capabilities for a concrete Host; those belong to `references/runtime/hosts/**`;
- concrete model names, parameters, or effort settings for a provider/model family; those belong to `references/runtime/models/**`;
- role responsibilities and independence themselves; those belong to `session-model`;
- Worker execution feedback, checkpoints, or Context Exchange document behavior.

## `session-model.md` / `session-model_zh_cn.md`

**Owns:**

- the Coding role set and each role's responsibilities;
- Single-Session and multi-Session topology;
- Session lifecycle, reuse, replacement, and role independence;
- isolation boundaries among Primary Output, Change Verification, Documentation/Comments & Git Operations, and other Coding responsibilities;
- conditions under which a logical responsibility does or does not require an independent Session.

**Does not own:**

- how a Host actually creates Sessions or selects models; that belongs to Runtime deployment;
- how a Worker reports progress or blocks the parent within an Interaction Slice; that belongs to `execution-control`;
- file-backed context transport between Sessions; that belongs to `context-exchange`;
- Worker content-memo language, switch, and write policy; that belongs to `content-memo`.

## `execution-control.md` / `execution-control_zh_cn.md`

**Owns:**

- execution-control semantics for an Interaction Slice;
- Progress Signals;
- Control Checkpoints;
- the parent's `Continue` / `Amend` / `Stop` control loop over Workers;
- when a Worker continues, blocks, or returns during execution;
- event-driven feedback and execution synchronization boundaries.

**Does not own:**

- role/Session topology; that belongs to `session-model`;
- directory layout, file ownership, and cross-Worker transport for file-backed Context Exchange; that belongs to `context-exchange`;
- whether a content memo refreshes at a checkpoint or what that refresh contains; that belongs to `content-memo`. `execution-control` owns the checkpoint event itself only.

## `context-exchange.md` / `context-exchange_zh_cn.md`

**Owns:**

- Coding context sharing and Semantic Contract transport boundaries;
- file-backed Context Exchange workspace layout for multiple Workers;
- ownership and filesystem-capability boundaries for the Context Exchange Root, root `INDEX.md`, and Worker subdirectories;
- the fallback order for targeted read-only access, mechanical cross-Worker copies, and compact parent-mediated handoff;
- context handoff mechanics for Worker replacement / escalation;
- selection, structure, freshness, and consumption of Context Bootstrap/Refresh capsules;
- information allowed/prohibited in Context documents and their transport relationship with Evidence-on-Demand.

**Does not own:**

- the working language of Worker-authored Context Exchange prose; that belongs to `content-memo`;
- the default value, disable authority, contents, or refresh cadence of `write_content_memo`; those belong to `content-memo`;
- Progress Signal / Control Checkpoint trigger semantics; those belong to `execution-control`;
- role independence and Session topology; those belong to `session-model`.

## `content-memo.md` / `content-memo_zh_cn.md`

**Owns:**

- the working language of Worker-authored prose in the Worker's Context Exchange subdirectory;
- the `write_content_memo` dispatch configuration and its default-`true` semantics;
- the authority boundary that only the parent may set `write_content_memo: false`;
- responsibility, recommended filename, content boundary, and compression requirements for the default execution content memo;
- memo refresh policy at material milestones, Control Checkpoints, handoff, exit/replacement, and related events;
- which other protocols remain active when `write_content_memo: false`.

**Does not own:**

- creation and isolation of the Context Exchange Root / Worker subdirectory; that belongs to `context-exchange`;
- why a Control Checkpoint triggers or how the parent decides at it; that belongs to `execution-control`;
- whether the Worker is an independent Session or which model runs it; that belongs to `session-model` + Runtime deployment.

## Boundaries with documents outside this directory

### `references/coding-flow.md` / `_zh_cn.md`

This is the **routing/assembly entrypoint** for Coding Flow: it owns which Coding modules are loaded on which task paths, the high-level phase order, and module composition. It should not redefine detailed protocols already owned by modules in this directory.

### `references/shared-protocols.md` / `_zh_cn.md`

This is the **shared-protocol owner** for primitives reused across Coding and Multimodal. Truly cross-Flow primitives such as Semantic Contract fields, shared Dispatch Preview, and Evidence-on-Demand should be defined there. Coding modules own only Coding-specific application, routing, or extensions and should not copy the shared normative body.

### `references/runtime/**`

This area owns **concrete deployment implementation**: Host Adapters define tools, Session/process creation mechanics, filesystem behavior, and capabilities actually exposed by a host; Model Profiles define concrete model bindings, parameters, and effort. `references/coding/runtime*` owns only the host/model-neutral Coding Runtime Contract.

## Routing new rules

When adding or changing a Coding rule, classify it semantically first:

1. “Which responsibilities/Sessions exist, and are they independent?” → `session-model`.
2. “When does a Worker report, block, continue, or stop during execution?” → `execution-control`.
3. “Where does context live, who can read/write it, and how is it transported or handed off across Workers?” → `context-exchange`.
4. “What language does Worker context prose use, should an execution summary be written, and what/when should it record?” → `content-memo`.
5. “How do these roles bind to Host/model capabilities?” → `runtime`; concrete Host/model details continue under `references/runtime/**`.
6. Is it a cross-Flow primitive? → check `shared-protocols` first rather than creating a duplicate Coding definition.

If one requirement spans multiple owners, split the normative behavior into the smallest owner-specific pieces and connect them by references. Do not choose one document to own all cross-layer semantics.