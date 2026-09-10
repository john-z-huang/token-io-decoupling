# Coding Runtime Registry

This registry lists concrete Coding deployments that have an explicit Host Adapter and Model Profile. It is deployment metadata, not part of the runtime-neutral Coding role architecture.

Load this file only through [`../coding/runtime.md`](../coding/runtime.md) when Coding Flow needs to resolve the active runtime.

## Registered deployments

| Host Adapter | Model Profile | Status |
|---|---|---|
| [`hosts/codex.md`](hosts/codex.md) | [`profiles/openai.md`](profiles/openai.md) | Current verified deployment |

The Codex/OpenAI entry preserves the existing verified Coding behavior of this Skill.

A host or model family that is not listed here must not be treated as supported merely because it can parse Agent Skills or run coding tasks.

## Adding another Code Agent product

A new deployment should normally add:

1. a Host Adapter describing how that product exposes persistent instructions, independent Sessions, model/runtime parameter selection, context transport, and isolation capabilities;
2. a Model Profile declaring role eligibility, concrete model bindings, execution-parameter policy, escalation, and unavailable handling;
3. validation showing that the deployment preserves the Coding Runtime Contract and does not require vendor branches in Core documents.

Do not modify an existing deployment entry to approximate another product or provider. Add a separate adapter/profile pair when the new environment has a concrete capability mapping, and label its validation status accurately until an actual runtime smoke test has been performed.

## Multimodal boundary

Multimodal Flow is not generalized through this Coding runtime registry. Its current deployment bindings remain isolated in [`../multimodal-openai-profile.md`](../multimodal-openai-profile.md). This registry applies to Coding Flow only and makes no portability claim for Multimodal Flow.
