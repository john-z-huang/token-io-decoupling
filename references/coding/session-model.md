# Coding Session Model

This module owns Coding Flow role definitions, Session topology, Context Firewall rules, and Primary Execution Session affinity. Coding runtime model bindings and reasoning-effort policy are defined separately in [`profile.md`](profile.md).

All roles also follow [`../shared-protocols.md`](../shared-protocols.md).

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

The current Coding Profile may also define a narrowly scoped escalation exception for a repeatedly blocked task. Follow [`profile.md`](profile.md) for that exception instead of treating stronger reasoning effort as a general reason to split Sessions.

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

Create a new execution Session only for the independent-verification, real-parallelism, context-degradation/capacity, explicit-isolation, or Profile-defined targeted-escalation cases described above. The Primary Execution Session is sticky but not immortal: reuse it by default, rebuild it when correctness, capacity, or isolation requires it.
