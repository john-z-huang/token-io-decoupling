# Coding Flow

This Flow covers project exploration, planning, implementation, refactoring, fixes, code/config/document materialization, builds, tests, and debugging. It preserves the two logical responsibilities already used by `token-io-decoupling`—Input-side Reasoning and Primary Output—but keeps the detailed Coding rules in independent modules so unrelated work can evolve without repeatedly editing one shared document.

All Coding roles also follow [`shared-protocols.md`](shared-protocols.md).

## Module loading

`coding-flow.md` is the stable Coding entry point. Do not move module-specific policy back into this file merely for convenience.

After Coding Flow is selected:

1. Load [`coding/session-model.md`](coding/session-model.md) to establish role ownership, Luna Single-Agent Mode, Context Firewall, and Primary Execution Session affinity.
2. Load [`coding/profile.md`](coding/profile.md) to map the current runtime model and reasoning-effort tiers to those responsibilities.
3. Load [`coding/execution-control.md`](coding/execution-control.md) before substantive implementation, refactoring, debugging, build/test work, or other execution that may cross semantic decision boundaries.
4. Load [`coding/context-exchange.md`](coding/context-exchange.md) when the task uses multiple independent Coding Agents, needs reusable cross-Agent context, or requires Worker replacement/escalation handoff.

Purely bounded exploration may defer `execution-control.md` until execution begins. Single-Agent Luna tasks that never create another Coding Agent do not need to load `context-exchange.md` unless file-backed recovery/context transport is actually useful.

If a relevant Coding module is already loaded and its rules remain valid, do not reread it. Load modules by responsibility rather than preloading the entire `references/coding/` directory.

## Normative ownership boundaries

Each Coding concern has one primary owning module:

| Concern | Owning document |
|---|---|
| roles, Session topology, Context Firewall, Primary Execution Session | [`coding/session-model.md`](coding/session-model.md) |
| model bindings, `reasoning_effort`, targeted max escalation | [`coding/profile.md`](coding/profile.md) |
| Semantic Contract transport, file-backed Context Exchange, Worker handoff | [`coding/context-exchange.md`](coding/context-exchange.md) |
| two-level planning, bounded stages, Decision Checkpoints, verification, output discipline | [`coding/execution-control.md`](coding/execution-control.md) |

Do not duplicate a module's normative rules in `SKILL.md`, this entry point, or another Coding module. Cross-reference the owning document instead. Change this file only when Coding routing, module ownership, or cross-module load conditions change.

This ownership boundary is also the maintenance boundary for parallel git worktrees: model/Profile work should normally touch `coding/profile.md`; Context Exchange work should normally touch `coding/context-exchange.md`; checkpoint/verification work should normally touch `coding/execution-control.md`; Session-topology work should normally touch `coding/session-model.md`. A task may span modules when semantics truly require it, but shared-file edits should not be introduced merely to restate another module's policy.

## Responsibility order

The Coding architecture still uses Input-side Reasoning for high-value semantic decisions and Primary Output for high-volume project-state consumption, materialization, and mechanical verification. Logical roles do not imply separate Agent instances. The current runtime Profile decides whether those responsibilities share one Session or use independent Sessions.

The detailed role and Session rules are normative in [`coding/session-model.md`](coding/session-model.md); do not infer additional Session requirements from this summary.

## Boundary with Multimodal Flow

Ordinary Coding tasks remain in this Flow. Switch to or begin with Multimodal Flow only when the task truly requires continuous GUI Observation, large image/screenshot sets, video frames, design references, or other high-volume visual world state.

If Multimodal Flow has completed visual analysis and code changes are needed, Coding Flow receives only its narrow Handoff Contract. Do not replay complete image sets, video frames, Computer Use history, OCR text, or full visual-analysis history into the Primary Execution Session merely to implement code.

The Multimodal Flow architecture and its runtime rules remain owned by [`multimodal-flow.md`](multimodal-flow.md); Coding module changes must not silently redefine them.
