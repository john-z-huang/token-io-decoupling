# Coding Runtime Registry

This registry lists concrete Coding deployments that have an explicit Host Adapter and Model Profile. It is deployment metadata, not part of the runtime-neutral Coding role architecture.

Load this file only through [`../coding/runtime.md`](../coding/runtime.md) when Coding Flow needs to resolve the active runtime.

## Registered deployments

| Host Adapter | Model Profile | Status |
|---|---|---|
| [`hosts/codex.md`](hosts/codex.md) | [`profiles/openai.md`](profiles/openai.md) | Current verified deployment |
| [`hosts/claude-code.md`](hosts/claude-code.md) | [`profiles/anthropic.md`](profiles/anthropic.md) | Official-capability-backed integration; live Claude Code CLI smoke test pending |
| [`hosts/qwen-code.md`](hosts/qwen-code.md) | [`profiles/alibaba-qwen.md`](profiles/alibaba-qwen.md) | Official-capability-backed integration; live Qwen Code CLI smoke test pending |

The Codex/OpenAI entry preserves the existing verified Coding behavior of this Skill. The Claude Code/Anthropic entry is registered because the required Host capabilities are explicitly documented by Claude Code and the runtime mapping fits the existing Coding Runtime Contract; however, the environment used to author that integration did not have the `claude` CLI installed, so it must not be described as locally smoke-tested until a real Claude Code run verifies it.

The Qwen Code/Alibaba Qwen entry maps `qwen3.8-max` to Input-side Reasoning and `qwen3.8-flash` to Primary Output. Qwen Code documents the required Agent Skills, regular-subagent, model-selection, continuation, worktree, and provider-effort capabilities; Alibaba Cloud documents both Qwen3.8 model bindings and their effective reasoning tiers. The environment used to author this integration has not run a real Qwen Code CLI Max-parent/Flash-subagent smoke test, so the deployment remains capability-backed rather than locally verified.

A host or model family that is not listed here must not be treated as supported merely because it can parse Agent Skills or run coding tasks.

## Adding another Code Agent product

A new deployment should normally add:

1. a Host Adapter describing how that product exposes persistent instructions, independent Sessions, model/runtime parameter selection, context transport, and isolation capabilities;
2. a Model Profile declaring role eligibility, concrete model bindings, execution-parameter policy, escalation, and unavailable handling;
3. validation showing that the deployment preserves the Coding Runtime Contract and does not require vendor branches in Core documents.

Do not modify an existing deployment entry to approximate another product or provider. Add a separate adapter/profile pair when the new environment has a concrete capability mapping, and label its validation status accurately until an actual runtime smoke test has been performed.

## Multimodal boundary

Multimodal Flow is not generalized through this Coding runtime registry. Its current deployment bindings remain isolated in [`../multimodal-openai-profile.md`](../multimodal-openai-profile.md). The Claude Code/Anthropic and Qwen Code/Alibaba Qwen entries in this registry apply to Coding Flow only and make no portability claim for Multimodal Flow.
