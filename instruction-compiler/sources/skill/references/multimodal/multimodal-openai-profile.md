# Multimodal OpenAI Deployment Profile

This file preserves current deployment-specific OpenAI bindings for Multimodal Flow after those deployment details were removed from the root `SKILL.md`. It is intentionally a small deployment-specific document, not a generalized Multimodal runtime abstraction, and is outside the currently maintained Coding workflow.

This profile is self-contained for the concrete OpenAI bindings listed below. It does not select a visual workflow or import architecture rules from another document.

## Current bindings

- **Decision Agent**: the current advanced parent model.
- **Primary Observation Agent**: `gpt-6-luna`; use `reasoning_effort=medium` by default, including substantive image/video/Computer Use Observation analysis.
- **Optional Primary Output Agent**: `gpt-6-luna`; use `reasoning_effort=medium` by default for substantive long output and other high-volume materialization.
- Primary Observation and Optional Primary Output are different responsibilities with different Session Affinity. Even when both are bound to Luna, do not merge their high-volume contexts by default.

## Deployment constraints

- Do not silently replace a Multimodal role that this profile requires to use Luna with another model.
- Raise only the affected task to `reasoning_effort=high` when concrete complexity or verification-failure evidence warrants it, then return to `medium`.
- If an independent Luna role is required but `gpt-6-luna` identity cannot be confirmed, the model cannot be selected explicitly, or the runtime environment cannot satisfy the profile's default or evidence-supported reasoning-effort tier for that dispatch, stop the corresponding substantive Multimodal work and briefly report the capability block.
- Purely read-only, strictly bounded diagnosis or observation may continue when Luna identity is confirmed but the runtime environment cannot set reasoning effort. Do not use that exception to move complex high-volume Observation/materialization back to the advanced parent model or to silently substitute a model or reasoning tier.

This profile is preserved without claiming portability to other Code Agent products or model families. Future Multimodal portability work should be based on actual testing rather than inferred from the Coding runtime architecture.
