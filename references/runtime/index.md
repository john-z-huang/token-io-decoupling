# Coding Runtime Registry

This registry lists concrete Coding deployments registered with a Host Adapter and Model Profile mapping. It is deployment metadata, not part of the runtime-neutral Coding role architecture.

Load this file only through [`../coding/runtime.md`](../coding/runtime.md) when Coding Flow needs to resolve the active runtime.

## Registered deployments

| Deployment document | Status |
|---|---|
| [`hosts/codex-openai.md`](hosts/codex-openai.md) | Verified deployment; preserves this Skill's existing Coding behavior |
| [`hosts/claude-code-anthropic.md`](hosts/claude-code-anthropic.md) | In live use; the Haiku-tier auxiliary dispatch and the normal two-Session Sonnet Primary Output dispatch have now been exercised, with the remaining limits listed in the document |

Each document covers both deployment concerns for one product/provider pair: the **Host Adapter** (how the product instantiates work) and the **Model Profile** (which runtime should perform a responsibility). Select the document whose Host Adapter matches the current environment.

The Codex/OpenAI entry preserves the existing verified Coding behavior of this Skill. The Claude Code/Anthropic entry is in live Coding use for this Skill's own development, with its host mapping backed by the official Claude Code documentation; the paths live use has exercised and the limits it still records are set out in that document, and anything that document or the host does not expose must keep being reported as unverified rather than assumed.

A host or model family that is not listed here must not be treated as supported merely because it can parse Agent Skills or run coding tasks.

## Adding another Code Agent product

A new deployment should normally add:

1. one deployment document describing how that product exposes persistent instructions, independent Sessions, model/runtime parameter selection, context transport, and isolation capabilities, together with the role eligibility, concrete model bindings, execution-parameter policy, escalation, and unavailable handling that apply on it;
2. validation showing that the deployment preserves the Coding Runtime Contract and does not require vendor branches in Core documents.

Do not modify an existing deployment entry to approximate another product or provider. Add a separate document when the new environment has a concrete capability mapping, and label its validation status accurately until the relevant runtime behavior has actually been exercised.

## Multimodal boundary

Multimodal Flow is not generalized through this Coding runtime registry. Its current deployment bindings remain isolated in [`../multimodal-openai-profile.md`](../multimodal-openai-profile.md). The Claude Code/Anthropic entry in this registry applies to Coding Flow only and makes no portability claim for Multimodal Flow.
