# Coding Session Model

This module owns Coding Flow role definitions, Session topology, Context Firewall rules, and Primary Execution Session affinity. Concrete Host/model eligibility and runtime parameters are resolved separately through [`runtime.md`](runtime.md).

All roles also follow [`../shared-protocols.md`](../shared-protocols.md).

## Architecture roles

### Input-side Reasoning Agent

Owns high-information-density work: understanding user intent and business semantics, formulating and decomposing the problem, identifying assumptions and unknowns, defining decision questions, comparing candidate directions against explicit criteria, making architecture and risk judgments, creating or amending the Semantic Contract, designing bounded stages, Interaction Slices, and blocking checkpoints, setting adaptive feedback cadence, releasing one slice at a time, handling major decision escalations, performing semantic acceptance, and explaining necessary reasoning-level decisions to the user.

Before substantive execution is dispatched, the input-side Agent retains ownership of the problem model, the meaning of evidence, unresolved semantic trade-offs, the approved solution envelope, and the decision to release implementation. These responsibilities are not delegated merely because repository evidence is high-volume. The input-side Agent may request evidence collection and candidate generation, but it must decide what the evidence means for the user's goal and whether a direction is approved.

During normal two-Session execution, the input-side Agent also owns the interaction cadence and slice boundaries. It authorizes one Interaction Slice at a time, interprets Progress Signals, and responds to each blocking Control Checkpoint with `Continue`, `Amend`, or `Stop` (or targeted Evidence-on-Demand before deciding). It must not merely wait for a long-running Output Agent or pre-release all future stages.

The input-side role should not perform large-volume output whose main purpose is to expand an already-made decision, and it should not ingest high-volume, low-decision-density raw project state by default.

### Primary Output Role

Owns high-volume project exploration, raw tool-output handling, evidence collection and semantic compression, execution-level planning within an approved semantic plan, code/config materialization, implementation fixes, and provisional implementation-feedback checks.

The Agent performing the Primary Output Role reads source and project state progressively: inspect summaries, statistics, and relevant paths first, then expand specific files or logs only when needed. It may analyze evidence and surface evidence-backed candidate options, and it may decide **how** to execute an approved direction inside the current Interaction Slice, but it must not approve or independently change unresolved semantic or architecture decisions, user/business trade-offs, goals, constraints, or acceptance criteria. Its compile, lint, unit, or narrow integration checks are implementation feedback used to guide local fixes; they are not the final change-result verification. It does not perform non-trivial repository Git inspection or operations; those belong to the separate Documentation/Comments & Git Operations role.

Each independent Coding Worker must send minimal Progress Signals within an authorized slice, return a compressed Control Checkpoint at the slice's return conditions or a mandatory material boundary, and pause before crossing its `Unreleased boundary`. Parallelism does not widen a Worker's slice or release future work.

### Context Bootstrap/Refresh Responsibility

Context Bootstrap/Refresh is an on-demand auxiliary responsibility, not a fifth core role or a mandatory Session topology. The parent Input-side Reasoning Agent creates or reuses one Bootstrap Worker only when the selection thresholds in `execution-control.md` are met. That Worker builds or delta-refreshes a bounded, fingerprinted capsule containing neutral project facts, exact source pointers, policy-routing pointers, and freshness/invalidation data. It does not own problem formulation, Semantic Contract decisions, implementation, verification conclusions, or documentation materialization, and it does not recursively delegate.

The Bootstrap Worker reads the complete mandatory Skill and repository instructions independently; its capsule supplements but never replaces them. A downstream Worker, including the initial verifier, may receive the capsule through targeted read-only exposure and then read the named authoritative files directly. Independent verification means independent judgment and no reliance on a prior verdict as evidence; it does not require rediscovering stable project layout and policy routing from zero. After a material relevant project or Skill change, reuse the same Bootstrap Worker for a delta refresh. Within one task conversation, reuse one independent verifier for each subsequent verification slice, requiring it to independently re-evaluate every new material final-state fingerprint/epoch; create an additional verifier only for a genuinely isolated requirement such as incompatible environments/snapshots, distinct permission or security domains, or an explicit independent audit.

### Change Verification Agent

Owns the final, independent verification of a material change after the Primary Output implementation slice. It receives the final project state, the effective Semantic Contract, acceptance criteria, changed-scope evidence, and provisional implementation checks, then progressively inspects the relevant diff and surrounding behavior and runs the appropriate holistic checks, such as integration, regression, cross-module, system, or end-to-end tests. It reports compressed evidence, coverage gaps, failures, and residual risks; it does not own architecture or product decisions, semantic acceptance, or repair work.

When selected, the Change Verification Agent starts in a fresh independent Session so it does not inherit the Primary Output implementation history. Its authorized verification slice is read-only with respect to product code, tests, documentation, configuration, and Git state. It consumes the changed-scope manifest and Git evidence supplied by the Documentation/Comments & Git Operations Agent, then verifies the resulting content and behavior; it may use a current, bounded Bootstrap capsule as factual/routing context, but must independently judge the supplied final state and required evidence. It does not perform non-trivial Git queries or operations. Disposable test/build outputs may be isolated by the Host. It must not recursively delegate. A material repair returns to Primary Output through the parent Input-side Agent; after repair, the parent reuses the same verifier for a new verification slice and final-state fingerprint/epoch. The verifier must re-evaluate the acceptance matrix independently and must not carry forward its earlier verdict as evidence. Create another verifier only when the parent identifies genuinely multiple isolated verification requirements, such as concurrent incompatible environments/snapshots, distinct permission or security domains, or an explicit independent audit.

When the repository provides an accumulated full-suite entrypoint or equivalent manifest, the fresh verifier starts with it before targeted changed-risk analysis; the detailed verification-asset, coverage-gap, and documentation fast-path rules are owned by the Coding Verification Boundary. The verifier remains read-only when reporting a gap, and repairs are routed to Primary Output; reuse the same verifier for the repaired epoch rather than creating one per check.

### Documentation/Comments & Git Operations Agent

Owns two separately scoped responsibilities. First, it performs optional post-verification materialization of developer documentation and code comments. It receives the final verified project state, the effective Contract, the explicit documentation/comment scope, and the compressed verification conclusion, and changes only approved documentation and comment locations. Second, it owns every non-trivial project-level Git responsibility, including repository synchronization (`fetch`/`pull`), branch and worktree lifecycle, staging, commits, history integration (`rebase`/`merge`/`cherry-pick`), conflict resolution, reset/clean/stash, tags, remote configuration, pushes, and applicable Issue/PR delivery. It may inspect or mutate Git metadata and remote state only inside a parent-released Git Interaction Slice.

Documentation/comment and Git slices are released independently. A Git conflict-resolution edit is allowed only to complete an explicitly authorized operation using already approved content; if resolution requires a new product, behavioral, or semantic decision, the Agent must stop and return that decision or repair to the parent Input-side Agent and Primary Output. Outside that narrow exception, it must not modify functionality, tests, fixtures, schemas, generated behavior, or other implementation logic. It does not perform final change verification or semantic acceptance. English and Simplified Chinese Markdown must remain semantically mirrored according to the repository's multilingual rules.

The Documentation/Comments & Git Operations Agent is created and managed by the parent Input-side Reasoning Agent when either responsibility is needed. It uses its own bounded context and the active Profile's `high` effort tier for both documentation/comments and complex Git work; it must not recursively delegate. The parent may release a Git slice before implementation for synchronization or branch/worktree preparation, after implementation for history integration or conflict handling, or after final semantic acceptance for commit, push, and Issue/PR delivery. The role, Contract, or Session affinity grants no authorization: every slice must name its exact repository/worktree/ref/remote scope, allowed mutations and external effects, and return conditions.

## Single-Session Coding Mode

Coding Flow enters **Single-Session Coding Mode** when the active Runtime Contract confirms all of the following:

- the current Session is explicitly eligible for both the Input-side Reasoning and Primary Output responsibilities under the selected Model Profile;
- the Host can satisfy the runtime parameters required for the current task in that Session;
- no independent structural benefit requires another Session.

In this mode:

- the current Session performs Input-side Reasoning and Primary Output implementation/provisional checks; do not create, hand off to, or require an additional Primary Output Agent merely to preserve a two-role topology;
- role boundaries still exist as logical execution discipline: stabilize high-value goals, constraints, decisions, and acceptance first; then progressively inspect project state, implement, run provisional feedback checks, obtain independent change verification when selected, and perform final semantic acceptance;
- for a material functional change, the current Session does not act as the final Change Verification Agent. The Input-side Agent creates one fresh independent verifier Session after implementation and reuses that verifier for later verification slices in the same task conversation; each new final-state fingerprint/epoch requires independent re-evaluation, not reuse of the earlier verdict as evidence. Additional verifier Sessions require genuinely isolated verification requirements. The Input-side Agent may also create a separate Documentation/Comments & Git Operations Agent when documentation or non-trivial Git work is needed;
- interaction slices and Continue/Amend/Stop decisions remain internal reasoning boundaries; do not simulate Progress Signal or Control Checkpoint messages to the same Session;
- the current Agent's ordinary exploration, implementation, focused testing, fixing, and implementation output are same-Session self-execution, not a Dispatch; do not print a fake self-dispatch or construct a prompt addressed to the same Session;
- large repository size, many changed files, long output, build/test/debug requirements, or generic “task complexity” are not reasons to create another Session.

Another Agent is allowed only when there is an independent structural benefit, for example:

- one initial fresh verifier that should not inherit the current implementation history, then reuse it for later verification epochs;
- real parallelism where tasks are independent and do not contend for the same write targets;
- the current Session context is clearly stale, contradictory, or too overgrown to continue effectively;
- explicit context, permission, or other isolation requirements whose benefit exceeds handoff cost.
- post-verification documentation/comment isolation or non-trivial Git-operation isolation that prevents implementation context from owning those responsibilities.

The selected Model Profile may also define a narrowly scoped escalation exception for a repeatedly blocked task. Follow [`runtime.md`](runtime.md) and the active Profile for that exception instead of treating a stronger model or runtime parameter as a general reason to split Sessions.

These exceptions must not restore same-runtime delegation as the default path for ordinary Coding. Multimodal Flow keeps its own independent high-volume Observation ownership and is not weakened by Coding's same-Session rules.

## Normal two-Session Coding Mode

When the active Runtime Contract declares the current Session eligible for Input-side Reasoning but not for Primary Output, and the Host can create or reuse a compatible independent Primary Output Session, use the normal two-Session topology:

```text
current parent Session
    └─ Input-side Reasoning

independent Primary Execution Session
    └─ Primary Output

optional independent Change Verification Session (reused across verification epochs)
    └─ Change Verification

optional Documentation/Comments & Git Operations Session
    └─ Documentation/Comments & Git Operations
```

The first split exists because the active deployment requires different runtime eligibility or context ownership, not merely because two logical role names exist. The optional verifier split is selected for the independent fresh-review benefit of material changes; the Documentation/Comments & Git Operations split is selected when post-verification documentation isolation or non-trivial Git-operation isolation has concrete value. Concrete model selection and execution parameters remain outside this module.

If the required independent Session cannot be instantiated according to the active Runtime, do not silently collapse into Single-Session Coding Mode. Follow the active Profile's unavailable-handling rule.

## Context Firewall

In normal two-Session Coding, the input-side Agent does not perform open-ended inspections that may bring large volumes of raw project state into its own context. Non-trivial Git inspection (`status`, `diff`, logs, history, remote state), synchronization, branch/worktree changes, staging, commits, rebases/merges, conflict handling, pushes, and remote/PR operations go to the Documentation/Comments & Git Operations Agent. Primary Output handles source/configuration exploration and implementation feedback; it does not perform non-trivial Git work. Change Verification consumes the new role's changed-scope manifest and Git evidence while independently verifying content and behavior. Each Agent reads, filters, and returns only the facts required for the parent's next decision.

The Context Firewall limits raw project-state ingress; it does not limit input-side reasoning or transfer decision ownership. The input-side Agent must still formulate the problem, define what evidence is needed, interpret compressed findings, choose among material directions, and release the next approved stage.

Single-Session Coding Mode has no cross-Session Context Firewall. The current Session directly performs the Primary Output Role and consumes necessary project state, but it must still use progressive reading and semantic compression rather than dumping an entire project, full logs, or unrelated diffs into active context without purpose.

Only strictly bounded, obviously small read-only metadata queries may be executed directly by the input-side Agent in normal two-Session mode—for example `pwd`, `git branch --show-current`, `git rev-parse --show-toplevel`, or checking existence of one file. Any Git query that reads a diff, status set, history, remote state, or other non-trivial repository state belongs to the Documentation/Comments & Git Operations Agent. The criterion is potential raw-output volume and repository-state impact, not the command name itself.

An independent Primary Output or Change Verification Agent semantically compresses diagnostics by default rather than returning complete command output. It reports only facts, anomalies, relevant paths, and small evidence snippets needed for the parent's next decision; more evidence is expanded through Evidence-on-Demand. The Documentation/Comments & Git Operations Agent likewise returns only its changed documentation/comment scope, changed-scope manifest, Git-operation result, and relevant checks.

## Primary Execution Session and Session Affinity

A continuous Coding workflow maintains one **Primary Execution Session** by default:

- in normal two-Session mode, it is the independent Session assigned the Primary Output Role by the active Runtime;
- in Single-Session Coding Mode, it is the current Session itself. Do not create another Session merely to obtain “Primary Session Affinity.”

Subsequent project exploration, implementation, diagnosis, testing, fixing, and local execution should preferentially reuse that Primary Execution Session. Reuse preserves project working context, reduces repeated exploration, and may improve stable prompt-prefix reuse opportunities. Do not claim that the same Agent is guaranteed to hit prompt cache, or that a new Agent is guaranteed not to.

Create a new execution Session for the initial independent change verifier when selected, or for real parallelism, context-degradation/capacity recovery, explicit documentation/comment or non-trivial Git-operation isolation, or an active-Profile targeted escalation. Reuse the selected verifier across later verification epochs in the same task conversation; create another verifier only for genuinely isolated verification requirements. The Primary Execution Session is sticky but not immortal: reuse it for implementation and provisional feedback by default, and rebuild it when correctness, capacity, or isolation requires it. The selected verifier and Documentation/Comments & Git Operations Worker are independent from Primary Execution and do not replace the Primary Execution Session.
