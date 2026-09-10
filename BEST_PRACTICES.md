# Coding Flow Best Practices — Current Codex Deployment

[English](BEST_PRACTICES.md) | [简体中文](BEST_PRACTICES_zh_cn.md)

This optional, non-normative guide covers installation and day-to-day use of the current verified Codex + OpenAI Coding deployment. It is not a product-neutral specification: normative behavior belongs to [`SKILL.md`](SKILL.md) and the Coding references, while concrete Host/Model policy belongs to the Runtime deployment files.

For the shortest normative loading path, use [`references/shared-protocols.md`](references/shared-protocols.md), [`references/coding-flow.md`](references/coding-flow.md), and the Runtime documents selected through [`references/coding/runtime.md`](references/coding/runtime.md). This guide is deliberately operational and should not duplicate those rules.

## Quick start

### Install once

Keep the canonical personal Skill at `~/.agents/skills/token-io-decoupling/`. The installation must include the root Skill, its bilingual mirror, the shared/Coding references, the Coding modules, the Runtime registry, and the selected Codex Host Adapter and OpenAI Model Profile. `BEST_PRACTICES*.md` is optional human-facing guidance, not a Runtime dependency.

Each Host Adapter maps this one source to the product's supported discovery mechanism. Keep project-scoped Skills in the host-native repository directory.

### Add the Codex global bootstrap

Put one language version in `~/.codex/AGENTS.md`. If `~/.codex/AGENTS.override.md` exists, it takes precedence; inspect the active file and remove conflicting bootstrap copies. Keep repository and project policy in their own instruction files.

Use this English bootstrap when persistent instructions are in English:

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
5. Before substantive dispatch, the Input-side Agent must define the problem,
   assumptions, decision questions, risks, acceptance, and stage/checkpoint
   plan. If project facts are missing, dispatch bounded reconnaissance first,
   then explicitly release implementation after synthesizing the evidence.
   Do not delegate an unresolved combined “analyze, choose, implement, and
   verify” mandate.
6. For non-simple normal two-Session work, authorize one Interaction Slice at
   a time. Use adaptive non-blocking Progress Signals and blocking Control
   Checkpoints; after each Control Checkpoint, choose Continue, Amend, or Stop.
```

This file includes the English bootstrap; use the corresponding language version when persistent instructions are in Chinese.

### Start a fresh run after instruction changes

After changing `~/.codex/AGENTS.md`, its override, a Skill file, or a project instruction file, start a new run or TUI Session. Do not assume an existing Session has adopted the change.

In the new run, perform a small non-destructive smoke check:

1. Confirm that the Skill is loaded and the task is routed to Coding Flow.
2. Confirm that unrelated Multimodal references are not preloaded.
3. Confirm that Runtime resolution selects the registered Codex Host Adapter and OpenAI Model Profile.
4. Confirm that Session topology matches the current model identity and Profile eligibility.
5. In this repository, have Documentation/Comments & Git Operations run `python3 scripts/check-multilingual-docs.py`, `python3 scripts/check-context-exchange.py`, `git diff --check`, and `git status --short` for the documentation/Git scope.
6. For a non-simple task, confirm that a concise Decision Brief exists, reconnaissance pauses before implementation when material facts are missing, and implementation release follows input-side synthesis.
7. For a material functional change, confirm that Primary Output is limited to implementation and provisional focused checks, a fresh Change Verification Session is created for final holistic checks, and Documentation/Comments & Git Operations is released with separate, explicit scopes: docs/comments only after verification, and non-trivial Git work at the stage where it is needed.
8. For a non-simple multi-Session task, confirm that each Worker has one authorized Interaction Slice, that Progress Signals do not block unnecessarily, and that Control Checkpoints produce an explicit Continue/Amend/Stop decision before the next slice.

If any check fails, fix loading, Runtime selection, or precedence before continuing. Never paste the full Skill into a task or silently substitute a required model.

### Keep the context capsule between runs

The `.token-io-decoupling/` directory is persistent runtime-only state. Keep the root `.gitignore` rule that ignores `/.token-io-decoupling/`; do not stage, commit, or automatically delete the directory. Apply cleanup only through an explicit user or retention policy.

Use Context Bootstrap/Refresh only when reuse is likely to pay for setup: at least two independent downstream Workers, one fresh Worker needing broad discovery plus three or more routed policy modules, or a relevant source set above roughly 20k raw characters / 5k token-equivalents. Skip it for Single-Session work, one small Worker, local or documentation-only fast paths, known one- or two-file tasks, or a net-negative setup. The capsule should stay bounded to neutral facts, source/policy pointers, fingerprints, and freshness data; it is not a substitute for mandatory instruction loading or semantic decisions.

Before downstream use, compare the capsule's `HEAD`/tree, tracked-delta fingerprint, listed source hashes, relevant untracked state, and active task/scope. After a material relevant change, reuse the same Bootstrap Worker for a delta refresh of affected sections, or read the named authoritative files directly until refresh completes. For one unchanged material final-state fingerprint, reuse one fresh verifier for Evidence-on-Demand; create a new verifier only after a material repair changes that fingerprint. Routine delivery read-back stays with the delivery slice unless a concrete external-risk criterion explicitly selects independent delivery verification.

## Day-to-day Coding loop

1. Start with a small Semantic Contract; use [`references/shared-protocols.md`](references/shared-protocols.md) for its fields and update rules.
2. For non-simple work, form the concise Decision Brief and keep problem definition, decision questions, solution approval, and release ownership on the input side.
3. If evidence is missing, run a bounded reconnaissance stage and pause for input-side synthesis before implementation; then follow [`SKILL.md`](SKILL.md) and [`references/coding-flow.md`](references/coding-flow.md) for routing and staged execution.
4. For non-simple normal two-Session work, authorize one Interaction Slice at a time; use adaptive Progress Signals inside the slice and blocking Control Checkpoints at natural or material boundaries, then decide Continue/Amend/Stop before releasing the next slice.
5. Keep routine work within the approved slice; when multiple Coding Workers are active, use the parent-led rendezvous and Context Exchange guidance in [`references/coding/context-exchange.md`](references/coding/context-exchange.md).
6. Let Primary Output run provisional focused checks during implementation, without performing non-trivial Git operations. For a material change, have Input-side Reasoning create a fresh Change Verification Agent for holistic final checks, map each acceptance criterion to its compressed evidence, and perform semantic acceptance against the Contract. Create Documentation/Comments & Git Operations when either responsibility is needed: release docs/comments only after verification, and release complex Git operations at the relevant stage as separate bounded slices. Use `reasoning_effort=high` and require explicit user/task authorization for synchronization, branch/worktree changes, staging, commits, history integration, conflict handling, pushes, or Issue/PR delivery. Session ownership details belong to [`references/coding/session-model.md`](references/coding/session-model.md).

The flow provides operational structure, not guarantees about cache hits, cost, quota, latency, or model quality.

## Runtime-specific decisions

This guide does not restate model, effort, Session-topology, escalation, or unavailable-handling policy. Resolve those decisions through [`references/coding/runtime.md`](references/coding/runtime.md), then follow the registered [`Codex Host Adapter`](references/runtime/hosts/codex.md) and [`OpenAI Model Profile`](references/runtime/profiles/openai.md).

## References

- [`SKILL.md`](SKILL.md): flow routing and cross-Flow boundaries.
- [`references/shared-protocols.md`](references/shared-protocols.md): Contract, dispatch, evidence, and reporting protocols.
- [`references/coding-flow.md`](references/coding-flow.md): Coding module loader.
- [`references/coding/session-model.md`](references/coding/session-model.md): runtime-neutral role and Session semantics.
- [`references/coding/runtime.md`](references/coding/runtime.md): Runtime Contract and selection algorithm.
- [`references/runtime/index.md`](references/runtime/index.md): registered deployments.
- [`references/runtime/hosts/codex.md`](references/runtime/hosts/codex.md): current Codex Host Adapter.
- [`references/runtime/profiles/openai.md`](references/runtime/profiles/openai.md): current OpenAI Coding Model Profile.
- [`MULTI_LINGUAL.md`](MULTI_LINGUAL.md): bilingual documentation rules.

This guide covers Coding Flow only. For Multimodal work, return to [`SKILL.md`](SKILL.md) and load its routed references.
