# Token I/O Decoupling Coding Flow Best Practices — Current Codex Deployment

[English](BEST_PRACTICES.md) | [简体中文](BEST_PRACTICES_zh_cn.md)

This is an optional, non-normative guide for installing and using the **current verified Codex + OpenAI Coding deployment**. It is not a product-neutral specification. Normative Coding architecture remains in the Skill and Coding Core references; concrete host/model policy remains in the Runtime deployment files.

For normative behavior, load [`SKILL.md`](SKILL.md), then the Coding references [`references/shared-protocols.md`](references/shared-protocols.md), [`references/coding-flow.md`](references/coding-flow.md), and the Runtime documents selected through [`references/coding/runtime.md`](references/coding/runtime.md). This guide keeps only the shortest operational path and must not become a second copy of those rules.

## Why use this flow?

The Coding Flow can help when project state and materialized output are the main source of Token pressure:

- The decision and execution responsibilities stay clear, so implementation can continue without interrupting every small mechanical step.
- A compact Semantic Contract and bounded checkpoints let the operator review high-value decisions without steering every command.
- A Context Firewall keeps raw project state with its owning execution Session while explicit decisions remain recoverable.

The Coding Flow already partially implements a LOOP-style closed feedback loop: at milestones, blocks, or high-value decision boundaries, an independent Primary Output Agent sends compressed feedback; the Input-side Reasoning Agent analyzes it, revises the Semantic Contract when needed, and releases the next stage. In Single-Session Coding Mode, the same stage and decision boundaries remain logical rather than simulating parent/child messages.

These are operational benefits, not guarantees about cache hits, cost, quota, latency, or model quality.

## Quick start

### Install once

Keep the complete Skill installation together so lazy loading can reach the selected Core and Runtime references. The current Coding path uses:

- `SKILL.md` and its `SKILL_zh_cn.md` mirror;
- `references/shared-protocols*` and `references/coding-flow*`;
- the required `references/coding/*` modules;
- `references/runtime/index*` plus the selected Codex Host Adapter and OpenAI Model Profile.

The `BEST_PRACTICES*.md` pair is optional human-facing deployment guidance. It is not a runtime dependency.

### Add the Codex global bootstrap

This subsection is deliberately Host-specific. Put one language version in `~/.codex/AGENTS.md`. At the same level, `~/.codex/AGENTS.override.md` takes precedence when present; inspect the active file and do not keep conflicting bootstrap copies. Keep repository and project-specific policy in their own instruction files.

Copy this short English bootstrap when English is the language of the persistent instructions:

```md
# Global bootstrap for token-io-decoupling Coding Flow

Before any Coding work:

1. Load and follow ~/.agents/skills/token-io-decoupling/SKILL.md.
2. Choose Coding Flow, then load references/shared-protocols.md and
   references/coding-flow.md, followed by the Coding modules they require.
3. Resolve the active Coding runtime through references/coding/runtime.md and
   use only the Host Adapter and Model Profile registered for this environment.
4. Do not substitute a model or runtime parameter when the selected Profile
   requires an exact binding; follow its unavailable-handling rule.
```

The Chinese document contains the Chinese bootstrap. Use only the version appropriate for the persistent instruction language.

### Start a new run after changes

The current Codex Host Adapter defines run lifecycle and persistent-instruction behavior. After changing `~/.codex/AGENTS.md`, its active override, a Skill file, or a project instruction file, start a new run or TUI Session; do not assume an existing Session has adopted the change.

For Codex instruction discovery and loading details, see its official AGENTS.md configuration documentation.

Run a small, non-destructive smoke check in the new run:

1. Confirm that `token-io-decoupling` is loaded.
2. Confirm that the task is routed to Coding Flow and unrelated Multimodal references are not preloaded.
3. Confirm that Coding Runtime resolution selects the registered Codex Host Adapter and OpenAI Model Profile rather than deriving product/model policy from Core documents.
4. Confirm that the resulting Session topology matches the current model identity and Profile eligibility.
5. In this repository, run `python3 scripts/check-multilingual-docs.py`, inspect `git diff --check`, and review `git status --short` for unexpected files.

If the check fails, fix the loading, runtime selection, or precedence issue and start another new run. Do not paste the full Skill into the task or silently replace a required model.

## Every Coding task

### 1. Write the smallest Semantic Contract

Before substantive execution, record the goal, constraints, approved decisions, and acceptance criteria. Amend the Contract when a high-value decision changes; do not repeatedly rewrite the full background.

```text
Goal: Add CSV export without changing the public API.
Constraints: Preserve Python 3.11 support and existing output.
Decisions: Reuse the current serializer; pause before any schema change.
Acceptance: Focused tests pass and only intended files change.
```

### 2. Resolve the active runtime, then keep execution context stable

The Input-side Reasoning responsibility decides the objective, constraints, architecture, risks, and acceptance. The Primary Output responsibility explores the project, materializes the approved result, and performs mechanical verification.

For the current verified deployment, [`references/coding/runtime.md`](references/coding/runtime.md) selects the Codex Host Adapter and OpenAI Model Profile. Reuse the resulting Primary Execution Session for related work unless a concrete reason to rebuild exists.

### 3. Bound high-value decision points

Let routine reads, local edits, and straightforward test cycles continue inside the execution Session. Report milestones, decision changes, blocks, or material deviations—not a transcript of every command. Before crossing a public API, schema, compatibility, security, or otherwise difficult-to-reverse boundary, pause with a short checkpoint and release the next stage only after the Contract is still correct.

When a decision needs proof, request a targeted path, excerpt, fact, or verification result. Do not forward complete diffs, logs, or file trees when a small piece of evidence is enough.

### 4. Verify, then accept

The execution side owns builds, tests, lint, formatting, type checks, diff review, and accidental-file checks. The decision side performs semantic acceptance: the goal is met, the Contract is implemented, constraints remain intact, and reported risks are acceptable.

## When to create another Session in the current OpenAI Profile

| Situation | Default action |
| --- | --- |
| The current Session is explicitly `gpt-5.6-luna`, the required reasoning-effort tier can be satisfied, and the task is ordinary Coding | The Profile declares dual-role eligibility; use generic Single-Session Coding Mode. |
| Fresh independent verification, real parallel work on disjoint targets, context-capacity recovery, or explicit isolation has concrete value | Create another Session only for that bounded purpose. |
| The current parent Session is not eligible for Primary Output under the OpenAI Profile | Use normal two-Session mapping with the required independent `gpt-5.6-luna` Primary Output Session. |
| A specific high/xhigh Worker has repeatedly failed or become clearly blocked | Use the Profile's narrowly scoped `reasoning_effort=max` escalation and preserve handoff context when possible. |
| The required Luna model or runtime parameter cannot be satisfied | Stop the corresponding substantive work and report the block; do not silently substitute another model. |
| The reason is only repository size, long output, build/test work, or generic “task complexity” | Do not create another Session for that reason alone. |

For exact rules, use [`references/coding/runtime.md`](references/coding/runtime.md), [`references/runtime/hosts/codex.md`](references/runtime/hosts/codex.md), and [`references/runtime/profiles/openai.md`](references/runtime/profiles/openai.md).

## Common mistakes

- Copying normative Skill or Flow text into `AGENTS.md`, a README, or a task prompt, creating a second policy that can drift.
- Putting Codex/OpenAI-specific model or parameter decisions back into runtime-neutral Coding Core documents.
- Treating a model's general coding capability as automatic role eligibility instead of consulting the active Profile.
- Loading unrelated Flow or Runtime references, or forwarding full raw state when a targeted Evidence-on-Demand request is sufficient.
- Sending one unlimited implementation instruction across several semantic decision boundaries without a checkpoint.
- Creating same-runtime Agents without an independent benefit, or running parallel work against overlapping targets or ordered decisions.
- Continuing in a stale run after instruction changes, or presenting unmeasured cache, cost, quota, or latency benefits as facts.

## References

- [`SKILL.md`](SKILL.md): routing and cross-Flow boundaries.
- [`references/shared-protocols.md`](references/shared-protocols.md): shared Contract, dispatch, evidence, and reporting protocols.
- [`references/coding-flow.md`](references/coding-flow.md): stable Coding module loader.
- [`references/coding/session-model.md`](references/coding/session-model.md): runtime-neutral role and Session semantics.
- [`references/coding/runtime.md`](references/coding/runtime.md): Runtime Contract and selection algorithm.
- [`references/runtime/index.md`](references/runtime/index.md): registered deployments.
- [`references/runtime/hosts/codex.md`](references/runtime/hosts/codex.md): current Codex Host Adapter.
- [`references/runtime/profiles/openai.md`](references/runtime/profiles/openai.md): current OpenAI Coding Model Profile.
- [`MULTI_LINGUAL.md`](MULTI_LINGUAL.md): bilingual documentation rules for this repository.

This guide covers the current Codex Coding deployment only. For Multimodal routing, return to [`SKILL.md`](SKILL.md) and load its routed Multimodal references; do not reconstruct Multimodal rules here.
