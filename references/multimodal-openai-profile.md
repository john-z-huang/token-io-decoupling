# Multimodal OpenAI Deployment Profile

This file preserves the current concrete OpenAI bindings for Multimodal Flow after those deployment details were removed from the root `SKILL.md`. It is intentionally a small deployment-specific document, not a generalized Multimodal runtime abstraction.

The Multimodal architecture, working modes, Observation Firewall, visual checkpoints, and handoff behavior remain normative in [`multimodal-flow.md`](multimodal-flow.md).

## Current bindings

- **Decision Agent**: the current advanced parent model.
- **Primary Observation Agent**: `gpt-5.6-luna`; substantive large image/video/Computer Use Observation analysis uses `reasoning_effort=xhigh`.
- **Optional Primary Output Agent**: `gpt-5.6-luna`; substantive long output and other high-volume materialization use `reasoning_effort=xhigh`.
- Primary Observation and Optional Primary Output are different responsibilities with different Session Affinity. Even when both are bound to Luna, do not merge their high-volume contexts by default.

Coding Flow's Single-Session Coding Mode changes only Coding role mapping. It does not weaken Multimodal Observation ownership or imply that Observation and Output should share one Session.

## Deployment constraints

- Do not silently replace a Multimodal role that this profile requires to use Luna with another model.
- If an independent Luna role is required but `gpt-5.6-luna` identity cannot be confirmed, the model cannot be selected explicitly, or the host cannot satisfy the reasoning-effort tier required for that dispatch, stop the corresponding substantive Multimodal work and briefly report the capability block.
- Purely read-only, strictly bounded diagnosis or observation may continue when Luna identity is confirmed but the host cannot set reasoning effort. Do not use that exception to move complex high-volume Observation/materialization back to the advanced parent model or to silently assign a lighter tier to work whose profile requires `xhigh`.

This profile is preserved without claiming portability to other Code Agent products or model families. Future Multimodal portability work should be based on actual testing rather than inferred from the Coding runtime architecture.
