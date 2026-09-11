# Coding Execution Control

This module owns Coding Flow planning responsibility, bounded implementation stages, blocking Decision Checkpoints, implementation/final verification boundaries, Documentation/Comments & Git Operations release gates, and input-side output discipline.

Role and Session semantics come from [`session-model.md`](session-model.md). Semantic Contract and Evidence-on-Demand primitives come from [`../shared-protocols.md`](../shared-protocols.md).

## Two-level planning and execution

The input-side responsibility owns semantic-level planning: goals, constraints, architecture decisions, risks, and acceptance criteria. The Primary Output responsibility owns execution-level planning for implementation: which source/configuration files to inspect, modification order, local implementation choices, provisional focused checks, and fixing steps. When selected, the Change Verification responsibility owns the execution-level plan for independent final checks; the Documentation/Comments & Git Operations responsibility owns bounded plans for post-verification docs/comments and all non-trivial repository Git operations. The input-side responsibility owns authorization and release for each slice, while that Worker executes only the documentation or Git mechanics explicitly included in the released slice.

When normal two-Session mode needs project facts before a decision, first ask the Primary Output Agent to explore and return compressed facts, then make the high-value decision on the input side. If the output side discovers facts that would change an approved goal, architecture, constraint, or acceptance criterion, pause that direction and escalate briefly.

Single-Session Coding Mode follows the same responsibility order in one Session without creating role-to-role messages; when major new facts appear, amend the currently effective Contract directly and continue.

Parallelism is reserved for independent work that will not contend for the same write targets. Tasks with dependencies, shared files, or ordered result relationships are executed sequentially. When multiple independent Agents need reusable state, use [`context-exchange.md`](context-exchange.md) rather than parent-generated long summaries.

### Context Bootstrap/Refresh selection

Context Bootstrap/Refresh is an optional auxiliary slice. Select one parent-managed, non-recursive Bootstrap Worker when at least two independent downstream Workers are likely, when one fresh Worker would otherwise need broad project discovery plus three or more routed policy modules, or when the relevant source set is roughly above 20k raw characters / 5k token-equivalents and the capsule will be reused. Skip it for Single-Session work, one small Worker, local or documentation-only fast paths, known one- or two-file tasks, and whenever expected reuse does not exceed setup cost. The Bootstrap Worker materializes only a bounded factual/policy-routing capsule with source fingerprints and freshness data; it does not make semantic decisions or verification judgments. These rules are measurable routing criteria, not claims about billed tokens, cache hits, cost, quota, latency, or quality.

Before reuse, compare the capsule's `HEAD`/tree, tracked-delta fingerprint, listed source hashes, relevant untracked project state, and active task/scope with the current state. A material mismatch requires the parent to reuse the same Bootstrap Worker for a delta refresh of affected facts and pointers, or requires the receiving Worker to read the named authoritative sources directly. No Worker may rely on stale capsule claims. A refresh does not satisfy independent Change Verification.

## Pre-dispatch reasoning and implementation release

Except for simple, local, low-risk, obvious, reversible, mechanically verifiable work, the input-side Agent must form a concise **Decision Brief** before the first substantive Dispatch. The brief records the result of input-side analysis, not hidden chain-of-thought. It should contain:

- `Problem`
- `Known facts`
- `Assumptions and unknowns`
- `Decision questions`
- `Preliminary solution envelope`
- `Risks`
- `Acceptance`
- `Stages and checkpoints`

Do not request or expose private chain-of-thought. The brief may be short, but it must make the unresolved decisions, evidence needs, and release conditions explicit.

When the brief still lacks project facts needed for a material decision, the first Dispatch is a **bounded reconnaissance** stage only. It must name the questions to answer and the evidence to collect, default to no file or environment mutation, return compressed findings plus evidence-backed candidate options and unresolved questions, and pause after reporting. The Primary Output Agent may analyze the project and propose candidates, but it may not select or release a semantic or architecture direction on the input side's behalf.

After reconnaissance, the input-side Agent synthesizes the evidence, confirms or rejects assumptions, chooses the approved direction, updates the Decision Brief or Semantic Contract, and explicitly releases the implementation stage. If new evidence changes a material decision, pause and repeat this reasoning gate before continuing. In Single-Session Coding Mode, apply the same gate as an internal reasoning boundary without creating a fake self-dispatch.

Do not dispatch an unresolved combined mandate such as “analyze the problem, choose the best approach, implement it, and verify it” when material semantic, architecture, compatibility, security, schema, or public-interface decisions remain open. A simple fast-path task may still use one Dispatch through implementation and applicable focused checks, provided its approved direction is obvious and its result is mechanically verifiable; a selected final verifier remains a separate Dispatch.

## Interaction slices and adaptive feedback

For non-simple work in normal two-Session Coding, the input-side Agent authorizes only one **Interaction Slice** at a time. Each slice must state:

- `Objective`: the result this slice must produce;
- `Authorized scope/mutations`: the paths, behavior, and writes allowed inside the slice;
- `Return conditions`: the evidence or milestone that ends the slice;
- `Unreleased boundary`: the next subsystem, risk domain, semantic choice, or mutation that remains blocked.

The independent Worker retains low-decision-density autonomy inside the authorized slice, but may not cross its unreleased boundary merely because it can predict the next step. A slice is a control unit, not a command-by-command script. Simple, local, low-risk, obvious, reversible, mechanically verifiable work may remain a single fast-path implementation slice; when a final verifier is selected, its verification remains a separate slice.

Use two feedback types, both compressed and free of log floods:

- **Progress Signal** is a non-blocking, minimal milestone report from within an authorized slice. If the boundary and Contract remain unchanged, the Worker may continue without waiting for a response. Do not emit fixed-interval heartbeats or report every command.
- **Control Checkpoint** is a blocking rendezvous at the end of a slice or when a material boundary is reached. The Worker pauses before crossing the boundary and returns only the facts, changes, check result, issue, and need relevant to the next decision.

Feedback cadence is adaptive, not a fixed wall-clock interval. A Control Checkpoint is required at least when reconnaissance or diagnosis ends; when a cohesive behavior or implementation slice completes before entering another subsystem or risk domain; when verification produces a material conclusion; or when any Contract, architecture, scope, permission, security, or public-interface deviation appears. If a slice is expected to run without a natural milestone for a long period, the input-side Agent must define an intermediate Progress Signal or narrow the slice before dispatch.

After every Control Checkpoint, the input-side Agent must analyze the compressed evidence and choose `Continue`, `Amend`, or `Stop` (or request Evidence-on-Demand before choosing). It must not merely acknowledge the report or pre-release all later stages. `Continue` authorizes one newly specified slice; `Amend` changes the Contract or slice boundary before work resumes; `Stop` ends that direction. In Single-Session Coding Mode, apply the same sequence as an internal reasoning boundary without simulating parent/child messages.

## Bounded Coding stages and Decision Checkpoints

Normal two-Session Coding must not interpret “event-driven reporting” as permission to dispatch a complex implementation once and let the independent Primary Output Agent cross every substantive decision boundary through final verification. For work with meaningful semantic uncertainty, the input-side Agent defines a small number of **bounded Coding stages** and identifies which stage boundaries are **blocking Decision Checkpoints** before or during execution.

Use blocking checkpoints selectively. They are appropriate when the next stage depends on high-value judgment, for example:

- repository exploration reveals competing architecture or API-boundary choices;
- implementation crosses modules, public interfaces, schemas, migrations, compatibility boundaries, or security-sensitive behavior;
- debugging reaches a material fork where different fixes have different product or architectural consequences;
- an implementation stage completes and the next stage would substantially expand scope or make a difficult-to-reverse change;
- Change Verification exposes a failure or regression whose acceptable resolution requires changing the Semantic Contract.

At a blocking Decision Checkpoint—which is the Control Checkpoint form of an Interaction Slice boundary—the independent Primary Output Agent must **pause before entering the next substantive stage** and return only a compressed checkpoint message. Include the minimum useful fields, such as `Status`, `Findings`, `Changed`, `Verification`, `Issue`, and `Need`; omit empty fields and do not attach full diffs or logs. The input-side Agent then reviews the checkpoint, requests Evidence-on-Demand if necessary, chooses `Continue`, `Amend`, or `Stop`, and explicitly releases at most the next bounded slice.

Do not create blocking checkpoints for low-decision-density mechanics. Ordinary file reads, local code edits within an approved design, formatter/lint fixes, straightforward test repairs, repeated compile/test cycles, and other execution details remain inside the Primary Execution Session. “Implementation complete” or “verification starting” is only a mandatory pause when it was declared a blocking checkpoint or when newly discovered facts create a real semantic escalation; otherwise it may remain an ordinary event-driven progress report.

Simple, local, low-risk tasks may still use one Dispatch and run through implementation plus applicable focused checks to completion. If the Input-side Agent selects final Change Verification, that verification remains a separate Dispatch; otherwise the Agent must explicitly record why the task is too trivial to benefit from fresh review. The purpose of Coding checkpoints is to prevent long unsupervised semantic drift, not to force parent/child ping-pong or reproduce the click-by-click behavior intentionally avoided by Multimodal Routine Interaction.

Single-Session Coding Mode uses the same bounded-stage discipline only as an internal reasoning boundary. It does not simulate checkpoint messages to itself: at a declared boundary or major new fact, the current Session re-evaluates the effective Semantic Contract, makes the necessary high-value decision, and then continues.

Recommended form for an independent Primary Output Agent:

```text
Stage 1: inspect current auth/session architecture and identify the narrowest compatible fix; checkpoint before changing public API or persistence schema
Checkpoint: Findings: refresh state is duplicated across middleware and storage; Issue: two viable ownership models; Need: choose middleware-owned vs storage-owned state before implementation
Amendment: keep public API stable; choose storage-owned state; Stage 2 approved: implement and run focused tests, then pause only if verification requires a Contract change
```

## Supervised operational stages

For high-uncertainty normal two-Session Coding work—such as a first build, unfamiliar-environment bootstrap, toolchain diagnosis, or an external dependency or fallback execution path—the input-side Agent should predeclare a short sequence of evidence-producing stages. Each stage should end at a concrete observation or decision boundary rather than enumerate commands.

At the end of each predeclared implementation stage, the independent Primary Output Agent must return a compressed Control Checkpoint and pause. The input-side Agent reviews the evidence, chooses `Continue`, `Amend`, or `Stop`, amends the Semantic Contract or next-slice instruction when needed, and explicitly releases at most the next stage. The selected Change Verification Agent and Documentation/Comments & Git Operations Agent follow their own released slices, pause at their slice boundaries, and return equivalent checkpoints. Any independent Worker must also checkpoint immediately before changing the system or user environment, and immediately when a permission or network block, a deviation from the selected execution path, or materially different repair or fallback options appear.

Low-value commands, logs, and mechanical retries within an approved implementation or verification stage remain in that Worker's context. This rule does not require per-command reports or fixed-frequency no-information heartbeats, and it does not force every Coding task into small stages: known, low-risk, easily mechanically verified implementation operations may still run continuously until their implementation checkpoint.

## Coding Verification Boundary

### Verification assets and regression-first fresh verification

Each repeatable verification point should be materialized in the repository as an automated test or deterministic, project-native Python, Shell, or other script when doing so provides reusable regression value. One-off commands may diagnose a problem, but they must not remain the sole durable evidence for a check that is expected to recur.

When a repository has multiple verification assets, it should maintain discoverable phase or component aggregators and one full-suite entrypoint, or an equivalent manifest. A fresh Change Verification session must run the accumulated full-suite entrypoint first when one is available. It then performs targeted independent analysis only for changed risks or acceptance criteria that the suite does not cover, rather than rediscovering the repository layout and standard commands from scratch.

The verifier remains read-only. If it identifies a valuable missing recurring check, it reports the coverage gap and the precise expected assertion; it does not add the check itself. The parent routes the repair to Primary Output, which materializes the test or deterministic script. The same verifier is reused for the new final-state epoch and reruns the cumulative suite. Do not create a new verifier for every verification point or coverage gap.

Verification assets must be deterministic, idempotent, non-interactive, and have meaningful exit statuses. They should run offline without live APIs or secrets by default, make minimal or no product and Git mutations, and leave no generated artifacts behind. Optional network, system, or end-to-end suites should be explicit and separate when applicable so baseline regression does not depend on them.

### Documentation-only verification fast path

Ordinary documentation-only changes to wording, paths, status, or references default to lightweight deterministic checks: relevant stale-reference searches, Markdown or link checks, whitespace/diff checks, and the affected existing contract script. They do not require complex full functional verification merely because a documentation file changed. Escalate when documentation changes or defines a public contract, schema, configuration format, executable command, security or permission rule, generated artifact, or materially executable behavior.

The Primary Output responsibility owns only implementation-feedback checks and their high-volume evidence processing, such as focused builds, tests, lint, formatting, type checks, and local diagnostics used to guide implementation fixes. These checks are provisional and must not be presented as final change-result verification.

The Change Verification responsibility owns final change-result verification for a material change. Its initially fresh independent Agent/Session inspects the final project state and relevant surrounding behavior, checks the complete changed scope and accidental-file status against the changed-scope manifest and Git evidence produced by Documentation/Comments & Git Operations, and runs the appropriate holistic evidence-producing checks, such as integration, regression, cross-module, system, or end-to-end tests. Independent means independent judgment and no inherited Primary Output implementation history; a current bounded factual/routing capsule may be used, but a prior verifier verdict is never evidence. It does not perform non-trivial Git queries or operations. Normally create one independent verifier for a task conversation and reuse it across verification slices. Each slice has a supplied final-state fingerprint (epoch), and the verifier must independently re-evaluate the acceptance matrix and all appropriate checks for that state. It reports compressed evidence, failures, coverage gaps, and residual risks; it does not modify product code, tests, documentation, or configuration and does not repair findings.

Reuse that verifier for targeted Evidence-on-Demand, clarification, and post-repair verification slices. When the final-state fingerprint changes, the reused verifier must independently re-evaluate the new epoch and must not carry forward its earlier verdict as evidence. A non-material rerun on the identical state also reuses that verifier rather than creating another one merely because a check was pending. Create additional verifiers only for genuinely multiple isolated verification requirements, such as concurrent incompatible environments/snapshots, distinct permission or security domains, or an explicitly independent audit.

The Documentation/Comments & Git Operations responsibility owns post-verification materialization of approved developer documentation and code comments plus every non-trivial project-level Git operation. It may run documentation-specific checks, including the repository multilingual validator, and Git-specific checks such as scoped status/diff validation, but it does not perform final functional verification or semantic acceptance. It must not modify functionality or tests, except for an explicitly authorized conflict-resolution edit that uses already approved content and introduces no new product decision.

### Documentation, comments, and Git operations boundary

Documentation/comment work is a post-verification Interaction Slice. Non-trivial Git work is also owned by this role, but its slice may be released earlier when synchronization, branch/worktree preparation, history integration, or conflict handling is needed. For commit, push, remote, or Issue/PR delivery, the input-side Agent may release a Git slice only after the final tree is verified and semantically accepted, any docs slice has passed without scope drift, explicit user/task authority for the requested repository or GitHub effects is present, and the Host can provide the required capability boundary. A failed verifier, unresolved repair, failed documentation check, missing authorization, or unavailable capability blocks the dependent slice.

Every Documentation/Comments & Git Operations slice must state its objective, exact approved docs/comment or repository/worktree/ref/remote scope, allowed mutations and external effects, return conditions, and unreleased boundary. A Git slice may inspect or mutate Git metadata, synchronize repositories, manage branches/worktrees, stage, commit, rebase/merge/cherry-pick, reset/clean/stash, manage tags, resolve explicitly authorized conflicts, configure remotes, push, and perform applicable Issue/PR delivery. It must not edit tracked functionality, tests, or other content; the conflict-resolution exception is limited to already approved content. It must not make product decisions, perform semantic acceptance, or infer external authorization from its role, Contract, or Session affinity. The applicable repository development workflow supplies exact mechanics and checks; this module does not duplicate provider-specific commands or private workflow details.

Routine delivery read-back (status, staged scope, commit, branch, Issue, or PR metadata) stays inside the already-authorized delivery slice and does not default to a separate delivery verifier. Create an independent delivery verifier only when the parent identifies a concrete external-risk or independence benefit, such as a high-impact remote operation or a delivery boundary that cannot be safely checked by the delivery Worker, and releases that additional slice explicitly.

Within the released slice, the high-level order is: confirm the final Git evidence, status/diff, staged scope, and approved scope; use a suitable open Issue or create one with a category label and `@me`, then verify it; create or confirm a compliant branch and Chinese commit; push only after the Issue and staged/commit checks pass; create an `@me` PR with `Closes #N`; and verify the remote branch, Issue state/label/assignee, PR base/head/assignee, and Issue linkage. Synchronization, branch/worktree setup, and history integration may be separate earlier Git slices. The Worker must pause at a blocking Control Checkpoint before an external effect not covered by the release, and whenever any permission, network, label, assignee, branch, staged-scope, conflict, or PR-topology check fails. No verified open Issue means no push or PR.

The input-side responsibility owns semantic acceptance: whether the user's goal is satisfied, the Semantic Contract is implemented, business/compatibility constraints remain intact, and the risks reported by Change Verification, documentation checks, and Git-operation evidence are acceptable. It also decides whether a change is material enough to require an independent verifier, whether post-verification documentation/comment work is needed, and whether a Git slice is authorized for the current stage.

### Ordered final-result workflow

For a material functional change, the default order is:

1. Primary Output implements the approved slice and runs provisional focused checks, then pauses at its implementation checkpoint.
2. Input-side Reasoning creates one fresh independent Change Verification Agent/Session with the final state, its fingerprint/epoch, Contract, acceptance criteria, changed-scope evidence, and provisional-check summary. The verifier runs independent holistic checks and pauses with a compressed verification checkpoint.
3. Input-side Reasoning maps each acceptance criterion to verifier evidence and chooses `Continue`, `Amend`, or `Stop`. On failure, it releases only a narrowly scoped repair slice to Primary Output and then reuses the same verifier for a new verification slice and repaired final-state fingerprint/epoch. The verifier must independently re-evaluate the repaired state; its earlier verdict is not evidence. Additional verifier Agents are created only for genuinely isolated requirements. Documentation/comment and dependent remote Git slices must not start while a material verification issue remains unresolved.
4. After verification passes, Input-side Reasoning performs semantic acceptance and, when needed, creates a Documentation/Comments & Git Operations Agent/Session with an explicit docs/comment-only scope. That Agent returns its changed scope and documentation-specific checks. If Git synchronization, branch/worktree preparation, or history integration is needed at another stage, the parent releases a separate Git scope to the same role with its own checkpoint.
5. After the final tree and any documentation checkpoint pass, Input-side Reasoning may release the same role for a commit, push, remote, or Issue/PR Git slice when explicit user/task authority and the required Host capability are present. The Git slice returns compressed local and remote evidence; it does not make product decisions or perform semantic acceptance.
6. Input-side Reasoning performs final semantic acceptance, including confirmation that the documentation/comment pass introduced no functional or test changes, any conflict resolution stayed within approved content, and requested Git/remote evidence is consistent with the approved change.

For a trivial behavior-preserving or documentation-only task, Input-side Reasoning may explicitly skip a Change Verification Agent; it must record why the independent review has no concrete value and still run the applicable documentation/static checks. A Git-only operation that does not change tracked content may use compressed pre/post Git evidence without a verifier; conflict resolution or any tracked-content change requires independent verification, reusing the task's verifier when one already exists. A Primary Output self-report never substitutes for an explicitly required verifier.

For final semantic acceptance, the input-side Agent maps each acceptance criterion to compressed Change Verification evidence when a verifier is required (or to the explicitly recorded focused/static evidence when independent verification is skipped), adds documentation evidence where applicable, and gives an explicit judgment:

```text
Acceptance criterion → evidence → input-side judgment
```

The judgment must confirm that the user's goal is satisfied, the implementation remains within the approved solution envelope, business and compatibility constraints remain intact, no unapproved semantic decision was smuggled into execution, the independent verifier examined the final state when required, approved Git scope was preserved, and residual verification risks are acceptable. This evidence-backed mapping does not require rereading a complete diff, full test log, or large file; request only the smallest additional evidence needed through Evidence-on-Demand.

In normal two-Session mode, Primary Output returns compressed implementation-feedback conclusions and Change Verification returns compressed final-verification conclusions; the input-side Agent does not reread complete diffs, test logs, or large files by default. In Single-Session Coding Mode, the current Session performs implementation and provisional checks, then the input-side Agent creates one fresh independent verifier for material changes and reuses it across later verification epochs rather than accepting its own final verification. Do not create a verifier merely to preserve a role name; create the initial one when the Contract/risk/materiality or explicit user requirement gives independent review concrete value, and create additional verifiers only for genuinely isolated requirements.

## Input-side output discipline

In normal two-Session mode, input-side output should maximize information density and contain only what is required for advanced decisions, Semantic Contract updates, decision escalations, semantic acceptance, and necessary user interaction.

After each independent Worker produces a detailed report in its own Session, the input-side Agent must analyze and compress it before responding to the user. The response should contain only the necessary core outcome, changed scope, verification status, unresolved issues or risks, and next action, as applicable. It should direct the user to the relevant Worker context summary to review the original detailed report. The input-side Agent must not copy or substantially restate a long portion of any Worker report. Only an explicit user request for more detail permits expansion, and any expansion must remain within the requested scope; absent such a request, the input-side response remains concise after analysis.

Text that primarily expands already-determined information rather than producing new high-value decisions should be materialized by the Worker authorized for that output, for example:

- large code blocks, complete files, or detailed file-by-file implementation steps;
- long README content, design documents, reports, or explanations by the Documentation/Comments & Git Operations Agent after it is released for such work;
- extensive restatement of project state, complete diffs, or complete test reports;
- long final responses that an authorized materialization Worker can materialize directly.

In Single-Session Coding Mode, there is no separate implementation Session or context summary to which the user can be directed. The current Agent already performs the Primary Output Role, so it directly completes implementation materialization and may provide the necessary detailed report itself when the task or user requires it. If Documentation/Comments & Git Operations is selected, that Worker owns docs/comment materialization and non-trivial Git evidence/output. The two-Session compression-and-redirection rule does not require the current Agent to simulate a separate output-side report or to create another same-runtime Session merely to delegate long implementation output.

When the final response in normal two-Session mode is itself long and the host cannot directly reuse output-side results, prefer having the authorized materialization Worker write the complete material to a user-specified file or workspace; the input-side Agent returns only a short summary and location instead of regenerating the full content.
