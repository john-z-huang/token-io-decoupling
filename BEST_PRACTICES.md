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
```

This file includes the English bootstrap; use the corresponding language version when persistent instructions are in Chinese.

### Start a fresh run after instruction changes

After changing `~/.codex/AGENTS.md`, its override, a Skill file, or a project instruction file, start a new run or TUI Session. Do not assume an existing Session has adopted the change.

In the new run, perform a small non-destructive smoke check:

1. Confirm that the Skill is loaded and the task is routed to Coding Flow.
2. Confirm that unrelated Multimodal references are not preloaded.
3. Confirm that Runtime resolution selects the registered Codex Host Adapter and OpenAI Model Profile.
4. Confirm that Session topology matches the current model identity and Profile eligibility.
5. In this repository, run `python3 scripts/check-multilingual-docs.py`, `git diff --check`, and `git status --short`.

If any check fails, fix loading, Runtime selection, or precedence before continuing. Never paste the full Skill into a task or silently substitute a required model.

## Day-to-day Coding loop

1. Start with a small Semantic Contract; use [`references/shared-protocols.md`](references/shared-protocols.md) for its fields and update rules.
2. Follow [`SKILL.md`](SKILL.md) and [`references/coding-flow.md`](references/coding-flow.md) for routing and staged execution.
3. Keep routine work within the approved stage; use the checkpoint and evidence guidance in [`references/coding/execution-control.md`](references/coding/execution-control.md) when a decision boundary appears.
4. Run the appropriate mechanical checks, then perform semantic acceptance against the Contract. Session ownership details belong to [`references/coding/session-model.md`](references/coding/session-model.md).

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
