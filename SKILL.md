---
name: token-io-decoupling
description: "High-volume Agent Token I/O decoupling. Coding separates high-value input-side reasoning, implementation output, independent change verification, and the Documentation/Comments & Git Operations role for approved documentation/comments and non-trivial repository Git work, while keeping Core role and Session rules independent of any specific Code Agent product or model; concrete runtime bindings are selected through Host Adapters and Model Profiles. Browser Use, Computer Use, continuous GUI workflows, video, large image/screenshot sets, and visual design use an independent Multimodal Flow that isolates high-volume visual/temporal input."
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This Skill defines two scenario-specific Agent orchestration flows that separate high-value semantic decisions from high-volume raw-state consumption and output materialization. Coding and Multimodal have materially different execution architectures, so they share only a small set of orchestration protocols instead of forcing one universal role topology.

This Skill defines orchestration conventions only. It cannot bypass higher-priority permissions, user authorization, product limitations, or safety rules, and it must not present unmeasured claims about price, cache hits, quota savings, or runtime quality as facts.

## Core principles

1. **Choose the Flow first, then load its details**: do not load every reference unconditionally at startup.
2. **Keep Coding Core runtime-neutral**: Coding defines Input-side Reasoning, Primary Output, on-demand Change Verification, and Documentation/Comments & Git Operations responsibilities, Session/context rules, checkpoints, and verification independently from concrete products or models. Runtime mapping is resolved through the Coding Runtime Contract, Host Adapter, and Model Profile selected for the current environment.
3. **Keep Multimodal details isolated**: Computer Use, video, large image/screenshot sets, visual design, and similar tasks use the independent Multimodal Flow. Its working modes, visual checkpoints, Observation rules, and current deployment bindings live in its routed references rather than being duplicated in this root file.
4. **Use narrow Handoffs for mixed tasks**: visual analysis and Coding exchange only stable goals, required changes, constraints, evidence references, and acceptance criteria. Do not dump full raw state across Flows.
5. **Treat roles as responsibilities first**: a role represents responsibility and context ownership, not a mandatory one-to-one Agent instance. Coding Session topology is derived from the active runtime; Multimodal keeps its own context-ownership rules.

## Scenario routing

### Coding Flow

Route the following tasks to Coding Flow by default:

- repository or project exploration;
- implementation, refactoring, bug fixing, debugging;
- materializing code, configuration, or developer documentation;
- non-trivial repository Git work, including synchronization, branch/worktree operations, staging, commits, history integration, remotes, pushes, and applicable Issue/PR delivery;
- independently verifying material functional changes and their surrounding behavior;
- build, test, lint, formatting, type checking, diff/log analysis;
- other development tasks where project text state and large output are the primary Token pressure.

After selecting Coding Flow, load:

1. [`references/shared-protocols.md`](references/shared-protocols.md)
2. [`references/coding-flow.md`](references/coding-flow.md)

Then follow the module-loading table in `references/coding-flow.md`. Do not preload every file under `references/coding/` or `references/runtime/`; load only the Coding modules and active runtime files required by the current responsibility and stage.

Ordinary Coding must not load Multimodal Flow or create a Primary Observation Agent merely because this Skill also supports visual work.

### Multimodal Flow

Route tasks dominated by continuous GUI Observation, large image/screenshot collections, video or large frame sets, visual-reference comparison, high-volume OCR/DOM/accessibility state, or open-ended visual authoring to Multimodal Flow.

After selecting Multimodal Flow, load:

1. [`references/shared-protocols.md`](references/shared-protocols.md)
2. [`references/multimodal-flow.md`](references/multimodal-flow.md)
3. [`references/multimodal-openai-profile.md`](references/multimodal-openai-profile.md) for the current bundled deployment bindings

`references/multimodal-flow.md` owns the detailed distinction between Routine Interaction and Creative Visual Authoring, the Observation Firewall, visual/temporal progressive disclosure, curated visual checkpoints, Computer Use execution, Semantic Checkpoints, and visual verification. Do not reconstruct or summarize those rules in this root entry point.

The current Multimodal deployment profile is intentionally kept separate from the Coding Runtime registry. This Skill makes no claim here that Multimodal bindings have been generalized or tested across other Code Agent products.

### Mixed tasks and Flow Handoff

Do not preload both complete Flows at the start of a mixed task. Select the Flow whose Token pressure dominates the current stage and hand off only when responsibilities truly change.

Typical design-driven Coding:

```text
Multimodal Flow
→ visual analysis / Visual-State Digest
→ Decision confirms stable required changes
→ narrow Handoff Contract
→ Coding Flow
→ implementation / provisional focused checks
→ independent change verification when material
→ optional Documentation/Comments & Git Operations slices
→ return to the original Multimodal Flow for visual verification when needed
```

Typical ordinary Coding followed by UI verification:

```text
Coding Flow
→ implementation / tests
→ load Multimodal Flow only when high-volume visual verification becomes necessary
→ visual verification
```

The exact Handoff fields and prohibited raw-state payloads are defined in `references/multimodal-flow.md`.

## Reference loading rules

- Load only the Flow documents, Coding modules, and active runtime documents required for the current scenario.
- If a relevant reference is already loaded and its rules remain valid, do not read it again.
- When switching Flows, load only newly required references; do not reload unchanged shared protocols.
- The main `SKILL.md` is the routing entry point, not a replacement for Flow, Runtime, or deployment details.
- Coding-specific modules are loaded through [`references/coding-flow.md`](references/coding-flow.md); concrete Coding Host/Model deployment files are selected through the Runtime Contract rather than named in Core rules.
- When correctness requires cross-Flow information, use a narrow Handoff or Evidence-on-Demand instead of loading all references and raw state at once.

## Runtime boundary

Coding architecture and concrete deployment policy are intentionally separated:

```text
Coding Core responsibilities
        ↓
Coding Runtime Contract
        ↓
Host Adapter + Model Profile
        ↓
concrete Code Agent Sessions / models / parameters
```

The Runtime Contract is loaded through Coding Flow and selects only the registered deployment that matches the current environment. Product-specific persistent-instruction paths, Agent/Session operations, model names, and execution-parameter values belong to runtime deployment files, not this root Skill or Coding Core modules.

Multimodal Flow is currently kept outside that Coding runtime abstraction. Its existing deployment bindings are preserved in its own routed profile without attempting an untested portability redesign.

## Loading boundary

This Skill may be automatically discovered, but a normal Skill `description` only influences implicit matching and cannot guarantee that the complete Skill is loaded on every host startup. If a host must always obey specific invariants, use that Host Adapter's persistent-instruction mechanism or another higher-priority host-supported instruction channel.

References under `references/` are loaded on demand. Do not read all of them at task startup merely because they might become useful later.

For the current verified Coding deployment's bootstrap, Session restart, validation, and adoption guidance, see [`BEST_PRACTICES.md`](BEST_PRACTICES.md). That guide is non-normative and does not replace the selected Flow, Runtime Contract, Host Adapter, or Model Profile.
