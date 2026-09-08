# Token I/O Decoupling Coding Flow Best Practices

[English](BEST_PRACTICES.md) | [简体中文](BEST_PRACTICES_zh_cn.md)

This is an optional, non-normative guide for installing and using the Coding Flow. It is written for two readers: a host or repository maintainer setting up the Skill, and a Coding operator applying it to a task.

For normative behavior, load [`SKILL.md`](SKILL.md), then the Coding references [`references/shared-protocols.md`](references/shared-protocols.md) and [`references/coding-flow.md`](references/coding-flow.md). This guide keeps only the shortest operational path and must not become a second copy of those rules.

## Why use this flow?

The Coding Flow can help when project state and materialized output are the main source of Token pressure:

- The decision and execution responsibilities stay clear, so implementation can continue without interrupting every small mechanical step.
- A compact Semantic Contract and bounded checkpoints let the operator review high-value decisions without steering every command.
- A Context Firewall keeps raw project state with its owning execution Session while explicit decisions remain recoverable.

The Coding Flow already partially implements a LOOP-style closed feedback loop: at milestones, blocks, or high-value decision boundaries, the Primary Output Agent sends compressed feedback; the Input-side Reasoning Agent analyzes it, revises the Semantic Contract when needed, and releases the next stage; the Primary Output Agent then continues exploration, implementation, verification, or fixes. Most micro-work cycles can therefore close between Agents, leaving the user outside the loop and mainly requiring intervention when the goal changes, a major trade-off needs a decision, permission approval is required, or final acceptance is due; the user can remain separate from the executing Agent, and ordinary communication with the main Agent usually does not interrupt the Primary Execution Session. This is only a partial implementation of LOOP, not full autonomy: it depends on the host's continued dispatch and Session capabilities and must stop at permission, safety, product, or user-judgment boundaries.

These are operational benefits, not guarantees about cache hits, cost, quota, latency, or model quality.

## Quick start

### Install once

Runtime-required files are the Skill and the references selected by Coding Flow:

- `SKILL.md` and its `SKILL_zh_cn.md` mirror;
- paired `references/shared-protocols` and `references/coding-flow` files.

The `BEST_PRACTICES*.md` pair is optional, human-facing deployment guidance. Keep the English canonical files and Simplified Chinese mirrors together, but do not treat this guide as a runtime dependency.

### Add the global bootstrap

Put one language version in `~/.codex/AGENTS.md`. At the same level, `~/.codex/AGENTS.override.md` takes precedence when present; inspect the active file and do not keep conflicting bootstrap copies. Keep repository and project-specific policy in their own instruction files.

Copy this short English bootstrap when English is the language of the persistent instructions:

```md
# Global bootstrap for token-io-decoupling Coding Flow

Before any Coding work:

1. Load and follow ~/.agents/skills/token-io-decoupling/SKILL.md.
2. Choose Coding Flow, then load only references/shared-protocols.md and
   references/coding-flow.md.
3. Treat SKILL.md and those references as the source of truth for Flow, roles,
   model Profile, and execution boundaries. If a required model or parameter is
   unavailable, follow the Skill's unavailable-handling rule; do not substitute it.
```

The Chinese document contains the Chinese bootstrap. Use only the version appropriate for the persistent instruction language.

### Start a new run after changes

Codex builds its applicable instruction chain when a run or TUI Session starts. After changing `~/.codex/AGENTS.md`, its active override, a Skill file, or a project instruction file, start a new run or TUI Session; do not assume an existing Session has adopted the change.

For discovery and loading details, see the official [AGENTS.md configuration documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Run a small, non-destructive smoke check in the new run:

1. Confirm that `token-io-decoupling` is loaded.
2. Confirm that the task is routed to Coding Flow and only its Coding references are loaded.
3. Confirm that the current model Profile and Session behavior come from `SKILL.md`.
4. In this repository, run `python3 scripts/check-multilingual-docs.py`, inspect `git diff --check`, and review `git status --short` for unexpected files.

If the check fails, fix the loading or precedence issue and start another new run. Do not paste the full Skill into the task or silently replace a required model.

## Every Coding task

### 1. Write the smallest Semantic Contract

Before substantive execution, record the goal, constraints, approved decisions, and acceptance criteria. Amend the Contract when a high-value decision changes; do not repeatedly rewrite the full background.

```text
Goal: Add CSV export without changing the public API.
Constraints: Preserve Python 3.11 support and existing output.
Decisions: Reuse the current serializer; pause before any schema change.
Acceptance: Focused tests pass and only intended files change.
```

### 2. Keep roles logical and execution context stable

The Input-side Reasoning responsibility decides the objective, constraints, architecture, risks, and acceptance. The Primary Output responsibility explores the project, materializes the approved result, and performs mechanical verification. Reuse the Primary Execution Session for related work unless a concrete reason to rebuild exists.

### 3. Bound high-value decision points

Let routine reads, local edits, and straightforward test cycles continue inside the execution Session. Report milestones, decision changes, blocks, or material deviations—not a transcript of every command. Before crossing a public API, schema, compatibility, security, or otherwise difficult-to-reverse boundary, pause with a short checkpoint and release the next stage only after the Contract is still correct.

When a decision needs proof, request a targeted path, excerpt, fact, or verification result. Do not forward complete diffs, logs, or file trees when a small piece of evidence is enough.

### 4. Verify, then accept

The execution side owns builds, tests, lint, formatting, type checks, diff review, and accidental-file checks. The decision side performs semantic acceptance: the goal is met, the Contract is implemented, constraints remain intact, and reported risks are acceptable.

## When to create another Session

| Situation | Default action |
| --- | --- |
| The current Code Agent is explicitly `gpt-5.6-luna` and the task is ordinary Coding | Keep one Session in Single-Agent Luna Mode. |
| Fresh independent verification, real parallel work on disjoint targets, context-capacity management, or explicit isolation has concrete value | Create another Session only for that bounded purpose. |
| The current Agent cannot confirm the required Luna Profile | Follow the normal two-Session mapping and use the required independent Luna Primary Output role. If unavailable, stop and report the block. |
| The reason is only repository size, long output, or generic “task complexity” | Do not create another Session for that reason alone. |

For exact model and Session rules, use [`SKILL.md`](SKILL.md) and [`references/coding-flow.md`](references/coding-flow.md).

## Common mistakes

- Copying normative Skill or Flow text into `AGENTS.md`, a README, or a task prompt, creating a second policy that can drift.
- Loading unrelated Flow references or forwarding full raw state when a targeted Evidence-on-Demand request is sufficient.
- Sending one unlimited implementation instruction across several semantic decision boundaries without a checkpoint.
- Creating same-model Agents without an independent benefit, or running parallel work against overlapping targets or ordered decisions.
- Continuing in a stale run after instruction changes, or presenting unmeasured cache, cost, quota, or latency benefits as facts.

## References

- [`SKILL.md`](SKILL.md): routing, roles, Profile, and execution boundaries.
- [`references/shared-protocols.md`](references/shared-protocols.md): shared Contract, dispatch, evidence, and reporting protocols.
- [`references/coding-flow.md`](references/coding-flow.md): Coding roles, Session mapping, stages, and verification boundary.
- [`MULTI_LINGUAL.md`](MULTI_LINGUAL.md): bilingual documentation rules for this repository.

This guide covers Coding Flow only. For Multimodal routing, return to [`SKILL.md`](SKILL.md) and load its routed reference; do not reconstruct Multimodal rules here.
