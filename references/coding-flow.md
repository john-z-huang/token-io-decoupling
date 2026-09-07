# Coding Flow

This Flow covers project exploration, planning, implementation, refactoring, fixes, code/config/document materialization, builds, tests, and debugging. It preserves the two logical responsibilities already used by `token-io-decoupling`—Input-side Reasoning and Primary Output—but logical roles do not imply separate Agent instances. Whether execution uses one Session or multiple Sessions depends on the current model Profile and concrete isolation benefits. Ordinary Coding tasks must not create a Primary Observation Agent merely because the Skill also supports Multimodal Flow.

All roles also follow [`shared-protocols.md`](shared-protocols.md).

## Architecture roles

### Input-side Reasoning Agent

Owns high-information-density work: understanding user intent and business semantics, making architecture and risk judgments, creating or amending the Semantic Contract, handling major decision escalations, performing semantic acceptance, and explaining necessary reasoning-level decisions to the user.

The input-side role should not perform large-volume output whose main purpose is to expand an already-made decision, and it should not ingest high-volume, low-decision-density raw project state by default.

### Primary Output Role

Owns high-volume project exploration, raw tool-output handling, semantic compression, local execution planning, code/document/config materialization, compilation and testing, debugging fixes, and mechanical verification.

The Agent performing the Primary Output Role reads project state progressively: inspect summaries, statistics, and relevant paths first, then expand specific files, diffs, or logs only when needed. It may decide **how** to execute but must not independently change approved goals, architecture, constraints, or acceptance criteria.

## Luna Single-Agent Mode

When the currently running Code Agent can explicitly confirm that it is `gpt-5.6-luna`, Coding Flow enters **Single-Agent Luna Mode** by default:

- The current Session performs both the Input-side Reasoning Role and Primary Output Role. Do not create, hand off to, or require an additional Luna Primary Output Agent.
- The role boundaries still exist as logical execution discipline: stabilize high-value goals, constraints, and acceptance first; then progressively inspect project state, implement, mechanically verify, and perform final semantic acceptance. No Agent handoff is required between those stages.
- The current Luna's ordinary exploration, implementation, testing, fixing, and output are same-Session self-execution. They are not a Dispatch and must not print a fake self-dispatch.
- Large project size, many changed files, long output, build/test/debug requirements, or generic “task complexity” are not reasons to create another Luna.

Another Agent is allowed only when there is an independent structural benefit, for example:

- fresh verification that should not inherit the current implementation history;
- real parallelism where tasks are independent and do not contend for the same write targets;
- current Session context is clearly stale, contradictory, or too overgrown to continue effectively;
- explicit context, permission, or other isolation requirements whose benefit exceeds handoff cost.

These exceptions must not restore same-model delegation as the default path for ordinary Coding. The Multimodal Primary Observation Agent owns an independent high-volume visual/temporal context and is not weakened by this section's “ordinary Coding defaults to one Session” rule.

## Context Firewall

In the normal two-Session Coding Flow, the input-side Agent does not perform open-ended inspections that may bring large volumes of raw project state into its own context. `git diff`, large `git status` or logs, `find`, `rg`, file trees, build/test output, and similar high-volume checks go to the independent Agent performing the Primary Output Role, which reads, filters, and returns only the facts required for decisions.

Single-Agent Luna Mode has no cross-Session Context Firewall. The current Luna directly performs the Primary Output Role and consumes necessary project state, but it must still use progressive reading and semantic compression rather than dumping an entire project, full logs, or unrelated diffs into active context without purpose.

Only strictly bounded, obviously small metadata queries may be executed directly by the input-side Agent in normal two-Session mode—for example `pwd`, `git branch --show-current`, or checking existence of one file. The criterion is potential raw-output volume, not the command name itself.

An independent Primary Output Agent semantically compresses diagnostics by default rather than returning complete command output. It reports only facts, anomalies, relevant paths, and small evidence snippets needed for the parent's next decision; more evidence is expanded through Evidence-on-Demand.

## Primary Execution Session and Session Affinity

A continuous Coding workflow maintains one **Primary Execution Session** by default:

- in normal two-Session mode, it is the independent Primary Luna;
- in Single-Agent Luna Mode, it is the current Luna Session itself. Do not create another Luna merely to obtain “Primary Session Affinity.”

Subsequent project exploration, implementation, diagnosis, testing, fixing, and local execution should preferentially reuse that Primary Execution Session. Reuse preserves project working context, reduces repeated exploration, and may improve stable prompt-prefix reuse opportunities. Do not claim that the same Agent is guaranteed to hit prompt cache, or that a new Agent is guaranteed not to.

Create a new execution Session only for the independent-verification, real-parallelism, context-degradation/capacity, or explicit-isolation cases described above. The Primary Execution Session is sticky but not immortal: reuse it by default, rebuild it when correctness, capacity, or isolation requires it.

## Context sharing and Semantic Contract

### Simple, self-contained tasks

Normal two-Session mode uses a compact prompt: provide only the goal, necessary constraints, relevant paths, and facts to return. Do not make the input-side Agent copy large file contents or project state that the Primary Output Agent can inspect itself.

Single-Agent Luna Mode does not re-encode already-known information into a prompt addressed to itself. Maintain only the minimum stable goal, constraints, key decisions, and acceptance criteria needed in the current context.

### Complex, context-heavy tasks

In normal two-Session mode, when a task clearly depends on substantial conversation, business, or project background, prefer sharing the full relevant context that the host can safely provide with the Primary Output Agent, plus a short Semantic Contract. This avoids making the input-side Agent generate large output simply to redescribe existing background while the Contract stabilizes the currently effective decisions.

Single-Agent Luna Mode continues to use the Semantic Contract as a logical decision anchor but must not resend it to itself as a self-delegation prompt for formal completeness.

Semantic Contract fields, amendments, and context-block rules are defined in [`shared-protocols.md`](shared-protocols.md).

## Two-level planning and execution

The input-side responsibility owns semantic-level planning: goals, constraints, architecture decisions, risks, and acceptance criteria. The Primary Output responsibility owns execution-level planning: which files to inspect, modification order, local implementation choices, compile/test strategy, and fixing steps.

When normal two-Session mode needs project facts before a decision, first ask the Primary Output Agent to explore and return compressed facts, then make the high-value decision on the input side. If the output side discovers facts that would change an approved goal, architecture, constraint, or acceptance criterion, pause that direction and escalate briefly.

Single-Agent Luna Mode follows the same responsibility order in one Session without creating role-to-role messages; when major new facts appear, amend the currently effective Contract directly and continue.

Parallelism is reserved for independent work that will not contend for the same write targets. Tasks with dependencies, shared files, or ordered result relationships are executed sequentially.

## Bounded Coding stages and Decision Checkpoints

Normal two-Session Coding must not interpret “event-driven reporting” as permission to dispatch a complex implementation once and let the independent Primary Output Agent cross every substantive decision boundary until final completion. For work with meaningful semantic uncertainty, the input-side Agent defines a small number of **bounded Coding stages** and identifies which stage boundaries are **blocking Decision Checkpoints** before or during execution.

Use blocking checkpoints selectively. They are appropriate when the next stage depends on high-value judgment, for example:

- repository exploration reveals competing architecture or API-boundary choices;
- implementation crosses modules, public interfaces, schemas, migrations, compatibility boundaries, or security-sensitive behavior;
- debugging reaches a material fork where different fixes have different product or architectural consequences;
- an implementation stage completes and the next stage would substantially expand scope or make a difficult-to-reverse change;
- mechanical verification exposes a failure or regression whose acceptable resolution requires changing the Semantic Contract.

At a blocking Decision Checkpoint, the independent Primary Output Agent must **pause before entering the next substantive stage** and return only a compressed checkpoint message. Include the minimum useful fields, such as `Status`, `Findings`, `Changed`, `Verification`, `Issue`, and `Need`; omit empty fields and do not attach full diffs or logs. The input-side Agent then reviews the checkpoint, requests Evidence-on-Demand if necessary, amends the Contract or stage instruction, and explicitly releases the next bounded stage.

Do not create blocking checkpoints for low-decision-density mechanics. Ordinary file reads, local code edits within an approved design, formatter/lint fixes, straightforward test repairs, repeated compile/test cycles, and other execution details remain inside the Primary Execution Session. “Implementation complete” or “verification starting” is only a mandatory pause when it was declared a blocking checkpoint or when newly discovered facts create a real semantic escalation; otherwise it may remain an ordinary event-driven progress report.

Simple, local, low-risk tasks may still use one Dispatch and run through implementation plus verification to completion. The purpose of Coding checkpoints is to prevent long unsupervised semantic drift, not to force parent/child ping-pong or reproduce the click-by-click behavior intentionally avoided by Multimodal Routine Interaction.

Single-Agent Luna Mode uses the same bounded-stage discipline only as an internal reasoning boundary. It does not simulate checkpoint messages to itself: at a declared boundary or major new fact, the current Session re-evaluates the effective Semantic Contract, makes the necessary high-value decision, and then continues.

Recommended form for an independent Primary Output Agent:

```text
Stage 1: inspect current auth/session architecture and identify the narrowest compatible fix; checkpoint before changing public API or persistence schema
Checkpoint: Findings: refresh state is duplicated across middleware and storage; Issue: two viable ownership models; Need: choose middleware-owned vs storage-owned state before implementation
Amendment: keep public API stable; choose storage-owned state; Stage 2 approved: implement and run focused tests, then pause only if verification requires a Contract change
```

## Coding Verification Boundary

The Primary Output responsibility owns mechanical verification and high-volume evidence processing, including builds, tests, lint, formatting, type checks, diff review, accidental-file-change checks, and analysis of associated raw logs.

The input-side responsibility owns semantic acceptance: whether the user's goal is satisfied, the Semantic Contract is implemented, business/compatibility constraints remain intact, and risks reported by mechanical verification are acceptable.

In normal two-Session mode, the Primary Output Agent returns compressed verification conclusions only; the input-side Agent does not reread complete diffs, test logs, or large files by default. In Single-Agent Luna Mode, the current Session performs mechanical verification and then semantic acceptance directly. Do not create another Agent merely to preserve the verification boundary; use a fresh verifier only when independent review has concrete value.

## Input-side output discipline

In normal two-Session mode, input-side output should maximize information density and contain only what is required for advanced decisions, Semantic Contract updates, decision escalations, semantic acceptance, and necessary user interaction.

Text that primarily expands already-determined information rather than producing new high-value decisions should be materialized by the Primary Output Agent, for example:

- large code blocks, complete files, or detailed file-by-file implementation steps;
- long README content, design documents, reports, or explanations;
- extensive restatement of project state, complete diffs, or complete test reports;
- long final responses that the output side can materialize directly.

In Single-Agent Luna Mode, the current Agent already performs the Primary Output Role, so it directly completes this materialization and must not delegate long output to another Luna merely to obey this section.

When the final response in normal two-Session mode is itself long and the host cannot directly reuse output-side results, prefer having the Primary Output Agent write the complete material to a user-specified file or workspace; the input-side Agent returns only a short summary and location instead of regenerating the full content.

## Boundary with Multimodal Flow

Ordinary Coding tasks remain in this Flow. Switch to or begin with Multimodal Flow only when the task truly requires continuous GUI Observation, large image/screenshot sets, video frames, design references, or other high-volume visual world state.

If Multimodal Flow has completed visual analysis and code changes are needed, Coding Flow receives only its narrow Handoff Contract. Do not replay complete image sets, video frames, Computer Use history, OCR text, or full visual-analysis history into the Primary Execution Session merely to implement code.
