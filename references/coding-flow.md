# Coding Flow

This Flow covers project exploration, planning, implementation, refactoring, fixes, code/config materialization, builds, tests, debugging, independent change verification, optional documentation/comments materialization, and all non-trivial repository Git work. It preserves Input-side Reasoning and Primary Output as its base responsibilities, with on-demand Change Verification and Documentation/Comments & Git Operations roles plus separately authorized Interaction Slices for documentation and Git operations. Detailed Coding rules remain in independent modules so unrelated concerns can evolve without repeatedly editing one shared document.

All Coding roles also follow [`shared-protocols.md`](shared-protocols.md).

## Module loading

`coding-flow.md` is the stable Coding entry point. Do not move module-specific policy back into this file merely for convenience.

After Coding Flow is selected:

1. Load [`coding/session-model.md`](coding/session-model.md) to establish role ownership, generic Session semantics for implementation and on-demand Workers, Context Firewall, and Primary Execution Session affinity.
2. Load [`coding/runtime.md`](coding/runtime.md) to resolve the active Host Adapter and Model Profile and map those Session semantics to the current environment.
3. Load [`coding/execution-control.md`](coding/execution-control.md) before substantive implementation, refactoring, debugging, build/test work, or other execution that may cross semantic decision boundaries.
4. Load [`coding/context-exchange.md`](coding/context-exchange.md) when the task uses multiple independent Coding Agents, needs reusable cross-Agent context, requires Worker replacement/escalation handoff, or needs parent-led multi-Worker rendezvous and slice synchronization.

Purely bounded exploration may defer `execution-control.md` until execution begins. A Single-Session Coding task that never creates another Coding Agent does not need to load `context-exchange.md` unless file-backed recovery/context transport is actually useful.

`runtime.md` loads only the registered Host Adapter and Model Profile that match the current environment. Do not preload every file under `references/runtime/`.

If a relevant Coding module is already loaded and its rules remain valid, do not reread it. Load modules by responsibility rather than preloading the entire `references/coding/` directory.

## Normative ownership boundaries

Each Coding concern has one primary owning module:

| Concern | Owning document |
|---|---|
| roles, Session topology, Context Firewall, Primary Execution Session, pre-dispatch ownership | [`coding/session-model.md`](coding/session-model.md) |
| Runtime selection, Host/Profile composition, role eligibility mapping, unavailable boundary | [`coding/runtime.md`](coding/runtime.md) |
| Semantic Contract transport, file-backed Context Exchange, Worker handoff, multi-Worker rendezvous | [`coding/context-exchange.md`](coding/context-exchange.md) |
| two-level planning, pre-dispatch/release gate, Interaction Slices, feedback, bounded stages, Decision Checkpoints, verification, Git-operation release, output discipline | [`coding/execution-control.md`](coding/execution-control.md) |

Concrete product mechanics and concrete model/parameter policy do not belong to these Core ownership rows; the Runtime Contract selects their deployment files from the runtime registry.

Do not duplicate a module's normative rules in `SKILL.md`, this entry point, or another Coding module. Cross-reference the owning document instead. Change this file only when Coding routing, module ownership, or cross-module load conditions change.

This ownership boundary is also the maintenance boundary for parallel git worktrees: Runtime Contract changes normally touch `coding/runtime.md`; Context Exchange changes normally touch `coding/context-exchange.md`; checkpoint/verification changes normally touch `coding/execution-control.md`; Session-topology changes normally touch `coding/session-model.md`. Concrete Host or Model policy should remain inside its deployment file. A task may span modules when semantics truly require it, but shared-file edits should not be introduced merely to restate another module's policy.

## Responsibility order

The Coding architecture uses Input-side Reasoning for high-value semantic decisions, Primary Output for implementation and provisional focused checks, Change Verification for independent final change-result verification, and Documentation/Comments & Git Operations for approved post-verification docs/comments plus all non-trivial repository Git work. Git work includes synchronization, branch/worktree lifecycle, staging, commits, history integration, conflict handling, remotes, pushes, and applicable Issue/PR delivery. Logical roles do not imply separate Agent instances. When Change Verification is selected, start one independent verifier for the task conversation and reuse it across verification slices, requiring independent re-evaluation of each final-state fingerprint/epoch; create additional verifiers only for genuinely isolated requirements. Documentation/Comments & Git Operations remains a separate Session when its isolation benefit is selected, and each documentation or Git operation still requires its own parent-released Interaction Slice. `session-model.md` defines the possible topologies, while `runtime.md` determines which topology the active deployment may use.

Before substantive dispatch, consult the pre-dispatch reasoning, Interaction Slice, implementation-release, final-verification, and Git-operation release gates in [`coding/execution-control.md`](coding/execution-control.md); when multiple Coding Workers are active, also load the parent-led rendezvous rules in [`coding/context-exchange.md`](coding/context-exchange.md). This entry point only makes those ownership boundaries discoverable.

The detailed role and Session rules are normative in [`coding/session-model.md`](coding/session-model.md); do not infer additional Session requirements from this summary.

## Boundary with Multimodal Flow

Ordinary Coding tasks remain in this Flow. Switch to or begin with Multimodal Flow only when the task truly requires continuous GUI Observation, large image/screenshot sets, video frames, design references, or other high-volume visual world state.

If Multimodal Flow has completed visual analysis and code changes are needed, Coding Flow receives only its narrow Handoff Contract. Do not replay complete image sets, video frames, Computer Use history, OCR text, or full visual-analysis history into the Primary Execution Session merely to implement code.

Multimodal Flow architecture and deployment rules remain owned by its own routed references; Coding Runtime changes must not silently redefine them.
