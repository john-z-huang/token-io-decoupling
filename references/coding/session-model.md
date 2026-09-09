# Coding Session Model

This module owns Coding Flow role definitions, Session topology, Context Firewall rules, and Primary Execution Session affinity. Concrete Host/model eligibility and runtime parameters are resolved separately through [`runtime.md`](runtime.md).

All roles also follow [`../shared-protocols.md`](../shared-protocols.md).

## Architecture roles

### Input-side Reasoning Agent

Owns high-information-density work: understanding user intent and business semantics, making architecture and risk judgments, creating or amending the Semantic Contract, handling major decision escalations, performing semantic acceptance, and explaining necessary reasoning-level decisions to the user.

The input-side role should not perform large-volume output whose main purpose is to expand an already-made decision, and it should not ingest high-volume, low-decision-density raw project state by default.

### Primary Output Role

Owns high-volume project exploration, raw tool-output handling, semantic compression, local execution planning, code/document/config materialization, compilation and testing, debugging fixes, and mechanical verification.

The Agent performing the Primary Output Role reads project state progressively: inspect summaries, statistics, and relevant paths first, then expand specific files, diffs, or logs only when needed. It may decide **how** to execute but must not independently change approved goals, architecture, constraints, or acceptance criteria.

## Single-Session Coding Mode

Coding Flow enters **Single-Session Coding Mode** when the active Runtime Contract confirms all of the following:

- the current Session is explicitly eligible for both the Input-side Reasoning and Primary Output responsibilities under the selected Model Profile;
- the Host can satisfy the runtime parameters required for the current task in that Session;
- no independent structural benefit requires another Session.

In this mode:

- the current Session performs both Coding responsibilities; do not create, hand off to, or require an additional Primary Output Agent merely to preserve a two-role topology;
- role boundaries still exist as logical execution discipline: stabilize high-value goals, constraints, decisions, and acceptance first; then progressively inspect project state, implement, mechanically verify, and perform final semantic acceptance;
- the current Agent's ordinary exploration, implementation, testing, fixing, and output are same-Session self-execution, not a Dispatch; do not print a fake self-dispatch or construct a prompt addressed to the same Session;
- large repository size, many changed files, long output, build/test/debug requirements, or generic “task complexity” are not reasons to create another Session.

Another Agent is allowed only when there is an independent structural benefit, for example:

- fresh verification that should not inherit the current implementation history;
- real parallelism where tasks are independent and do not contend for the same write targets;
- the current Session context is clearly stale, contradictory, or too overgrown to continue effectively;
- explicit context, permission, or other isolation requirements whose benefit exceeds handoff cost.

The selected Model Profile may also define a narrowly scoped escalation exception for a repeatedly blocked task. Follow [`runtime.md`](runtime.md) and the active Profile for that exception instead of treating a stronger model or runtime parameter as a general reason to split Sessions.

These exceptions must not restore same-runtime delegation as the default path for ordinary Coding. Multimodal Flow keeps its own independent high-volume Observation ownership and is not weakened by Coding's same-Session rules.

## Normal two-Session Coding Mode

When the active Runtime Contract declares the current Session eligible for Input-side Reasoning but not for Primary Output, and the Host can create or reuse a compatible independent Primary Output Session, use the normal two-Session topology:

```text
current parent Session
    └─ Input-side Reasoning

independent Primary Execution Session
    └─ Primary Output
```

The split exists because the active deployment requires different runtime eligibility or context ownership, not merely because two logical role names exist. Concrete model selection and execution parameters remain outside this module.

If the required independent Session cannot be instantiated according to the active Runtime, do not silently collapse into Single-Session Coding Mode. Follow the active Profile's unavailable-handling rule.

## Context Firewall

In normal two-Session Coding, the input-side Agent does not perform open-ended inspections that may bring large volumes of raw project state into its own context. `git diff`, large `git status` or logs, `find`, `rg`, file trees, build/test output, and similar high-volume checks go to the independent Agent performing the Primary Output Role, which reads, filters, and returns only the facts required for decisions.

Single-Session Coding Mode has no cross-Session Context Firewall. The current Session directly performs the Primary Output Role and consumes necessary project state, but it must still use progressive reading and semantic compression rather than dumping an entire project, full logs, or unrelated diffs into active context without purpose.

Only strictly bounded, obviously small metadata queries may be executed directly by the input-side Agent in normal two-Session mode—for example `pwd`, `git branch --show-current`, or checking existence of one file. The criterion is potential raw-output volume, not the command name itself.

An independent Primary Output Agent semantically compresses diagnostics by default rather than returning complete command output. It reports only facts, anomalies, relevant paths, and small evidence snippets needed for the parent's next decision; more evidence is expanded through Evidence-on-Demand.

## Primary Execution Session and Session Affinity

A continuous Coding workflow maintains one **Primary Execution Session** by default:

- in normal two-Session mode, it is the independent Session assigned the Primary Output Role by the active Runtime;
- in Single-Session Coding Mode, it is the current Session itself. Do not create another Session merely to obtain “Primary Session Affinity.”

Subsequent project exploration, implementation, diagnosis, testing, fixing, and local execution should preferentially reuse that Primary Execution Session. Reuse preserves project working context, reduces repeated exploration, and may improve stable prompt-prefix reuse opportunities. Do not claim that the same Agent is guaranteed to hit prompt cache, or that a new Agent is guaranteed not to.

Create a new execution Session only for independent verification, real parallelism, context-degradation/capacity recovery, explicit isolation, or an active-Profile targeted escalation. The Primary Execution Session is sticky but not immortal: reuse it by default, rebuild it when correctness, capacity, or isolation requires it.
