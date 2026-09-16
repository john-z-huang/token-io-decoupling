sed: --: No such file or directory
# Coding Execution Control

This module owns Coding execution planning: bounded stages, Decision Checkpoints, Interaction Slice release, and execution-stage feedback. It assumes that the active workflow has already supplied the Contract, role/session context, runtime capabilities, and delegation state. It does not decide mode, topology, Agent/Session creation, allocation, count, reuse, replacement, exceptions, verification, documentation, Git, or final acceptance.

## Two-level planning

The input-side responsibility defines the goal, constraints, architecture decisions, risks, and acceptance criteria. The assigned execution responsibility turns that approved direction into bounded inspection, implementation, and focused-check steps. In a Single-Agent route, these are logical phases in the current Session; in a Multi-Agent route, the workflow's assigned Workers execute only their released slices.

When project facts are needed before a material decision, use a bounded reconnaissance slice. The executor returns compressed facts, evidence-backed options, and unresolved questions; the input-side responsibility selects the direction and updates the Contract. A Worker may decide how to execute an approved direction inside its slice, but it may not approve a new semantic or architecture direction.

Parallel work is appropriate only for independent, non-conflicting slices. Dependencies, shared write targets, and ordered results require sequential release. Context transport and parent-only feedback follow the active workflow's supplied protocols.

## Decision brief and implementation release

For work that is not simple, local, low-risk, obvious, reversible, and mechanically verifiable, prepare a concise **Decision Brief** before the first substantive execution slice. It records the result of analysis rather than private chain-of-thought and should contain:

- `Problem`
- `Known facts`
- `Assumptions and unknowns`
- `Decision questions`
- `Solution envelope`
- `Risks`
- `Acceptance`
- `Stages and checkpoints`

If material decisions remain open, release reconnaissance only. After it returns, confirm or reject assumptions, choose the approved direction, and release implementation. If new evidence changes a material decision, pause that direction and repeat the decision gate. Do not release an unresolved combined mandate that asks one executor to analyze, choose, implement, and verify an undecided solution.

## Interaction Slices

Release one **Interaction Slice** at a time for non-simple work. Every slice states:

- `Objective`: the result it must produce;
- `Authorized scope/mutations`: paths, behavior, and writes allowed;
- `Return conditions`: the evidence or milestone that ends it;
- `Unreleased boundary`: the next subsystem, risk domain, semantic choice, or mutation that remains blocked.

A slice is a control unit, not a command-by-command script. The executor may continue through low-decision-density mechanics while the Contract and boundary remain unchanged. It must pause at the return conditions or before crossing the unreleased boundary. A simple fast-path task may remain one slice through implementation and focused checks.

At a material boundary, use a compressed Control Checkpoint with the status, findings, changed scope, verification, issue, need, and unreleased boundary that matter to the next decision. The input-side responsibility chooses `Continue`, `Amend`, or `Stop`; `Continue` releases only the next bounded slice, and `Amend` changes the Contract or boundary before work resumes. In a Single-Agent route, this is an internal reasoning pause rather than a simulated self-message.

## Bounded stages and feedback

Use blocking Decision Checkpoints selectively when the next stage depends on high-value judgment, such as a competing architecture/API choice, a public-interface/schema/compatibility/security boundary, a material debugging fork, a substantial scope expansion, or a verification failure that changes the Contract.

For high-uncertainty work, predeclare a short sequence of evidence-producing stages. Each stage ends at an observation or decision boundary, not a command list. The executor pauses at the declared boundary; ordinary reads, local edits, formatter/lint fixes, straightforward test repairs, and repeated compile/test cycles stay inside the approved stage. Do not add checkpoints or execution slices merely to report low-value mechanics.
