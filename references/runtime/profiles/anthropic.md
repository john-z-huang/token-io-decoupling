# Anthropic Coding Model Profile

This file owns the concrete Anthropic model bindings and effort policy for the Claude Code Coding deployment registered by this Skill. It is deployment policy, not the Token I/O Decoupling architecture. Host-specific mechanics are supplied by the Claude Code Host Adapter; generic Session semantics are defined by [`../../coding/session-model.md`](../../coding/session-model.md) and [`../../coding/runtime.md`](../../coding/runtime.md).

This Profile targets Claude Code using the Anthropic API model family. Other Claude Code providers may resolve aliases differently or expose different model availability; do not reuse this Profile for those deployments unless the actual runtime satisfies the bindings below.

## Role bindings and dual-role eligibility

At Coding Flow startup, confirm the current Session's actual model identity through the Host Adapter before applying this Profile:

- **Input-side Reasoning**: the current advanced Claude parent Session owns high-value semantic decisions. This Profile assumes the parent is an advanced reasoning-capable Claude runtime selected for the main session; it does not authorize Haiku-class or otherwise lightweight runtimes to own the input-side responsibility merely because they can code.
- **Primary Output**: the required Anthropic execution model is **`claude-sonnet-5`**.
- **Dual-role eligibility**: when the current Session can explicitly confirm that it is `claude-sonnet-5` and the Host can satisfy the task's required effort level in that Session, this Profile declares the current Session eligible for both Input-side Reasoning and Primary Output. The generic runtime mapping therefore enters **Single-Session Coding Mode** unless a concrete structural reason requires another Session.
- **Normal two-Session mapping**: when the current advanced parent Session is not `claude-sonnet-5`, keep the parent constrained to the input-side reasoning responsibility and create/reuse an independent `claude-sonnet-5` Primary Output subagent.

The binding uses the full model ID instead of the `sonnet` alias. Claude Code aliases are provider-dependent and can advance to newer model versions over time; this Profile intentionally requires an explicit runtime identity so model-family alias drift does not silently change the deployment.

Single-Session Coding Mode is the same Core mode used by other runtimes. A current Sonnet 5 Session directly performs project exploration, implementation, debugging, mechanical verification, and output rather than delegating ordinary work to another Sonnet 5 merely to preserve a two-role topology.

## Effort selection

Claude Code and Sonnet 5 support `low`, `medium`, `high`, `xhigh`, and `max` effort levels. This Profile maps Coding task classes as follows:

- **Primary Output substantive work**: use `effort=xhigh` for general feature implementation, non-trivial refactoring or debugging, complex test/verification code, migration work within an already approved Contract, and other tasks where substantial implementation judgment is expected.
- **Bounded auxiliary materialization**: prefer `effort=high` for developer documentation, code comments, simple unit tests, low-risk mechanical edits, and similarly constrained support work. Additional auxiliary Coding Workers default to `high` unless their concrete task meets the `xhigh` criteria.
- **Strictly bounded mechanical work**: use `effort=medium` or `low` only when the task has low semantic risk and is easy to verify mechanically, such as running already-selected checks and compressing results, collecting file/path metadata, exact search/extraction, literal replacements, deterministic formatting, or generated-table updates. `low` should normally be limited to short deterministic/read-only work.
- **Do not down-tier semantic ownership**: lightweight Workers must not own the Semantic Contract, architecture/product decisions, cross-module implementation, complex debugging, complex test design, or public API/schema/permission changes.

Effort names are host/runtime controls, not universal capability units. Do not infer that the same effort label has identical underlying reasoning budget across Anthropic models or other vendors.

## Targeted max escalation

`effort=max` is an exception escalation, not the normal Primary Output setting.

Use a new, narrowly scoped `claude-sonnet-5` max-effort Worker only when an existing `high`/`xhigh` Worker has repeatedly failed, oscillated, or become clearly blocked on one specific task. When possible, the predecessor first writes reusable context/handoff documents in the primary worktree as defined by [`../../coding/context-exchange.md`](../../coding/context-exchange.md), and the max Worker reads those documents instead of restarting project exploration from zero.

After the blocker is resolved, follow-on work returns to the normal `xhigh`/`high` tiers. Do not keep `max` for unrelated work merely because one escalation succeeded.

A current Sonnet 5 Session in Single-Session Coding Mode may create another Agent only for fresh verification, real parallelism, clearly degraded/overgrown current context, explicit isolation benefit, or targeted max escalation for a specific repeatedly blocked task. Project exploration, implementation, testing, long output, or generic task complexity are not exceptions.

## Claude Code model-substitution boundary

Claude Code can replace a requested subagent model when organization `availableModels` or provider constraints block the requested value. That Host behavior is **not** a Profile fallback.

For every independent Profile-bound Worker:

1. request the exact `claude-sonnet-5` model and required effort;
2. verify the effective runtime when Claude Code exposes it;
3. if the actual model is not `claude-sonnet-5`, do not accept the Worker as Primary Output under this Profile;
4. if the actual effort is clamped below the task's required level, apply the unavailable rules below.

A warning-free tool call is not sufficient evidence that the requested runtime was honored, especially in non-interactive/background execution where some clamps or substitutions may not be surfaced prominently.

## Profile constraints and unavailable handling

- Do not silently replace the Primary Output binding with `opus`, `haiku`, `fable`, another Sonnet version, or an inherited parent model.
- If an independent Primary Output is required but `claude-sonnet-5` cannot be selected or verified as the actual subagent model, stop the corresponding substantive Coding work and briefly report the runtime block.
- If the required effort cannot actually be applied because the model/provider does not support it or an organization cap clamps it below the required tier, stop the affected substantive task rather than pretending the requested level took effect.
- Purely read-only, strictly bounded diagnosis may continue when the correct model identity is confirmed but the required higher effort cannot be set, provided the work remains deterministic/low-risk and does not cross into substantive implementation.
- Do not move high-volume project-state work back into an advanced parent Session merely because Claude Code automatically inherited or substituted that model. The Primary Output binding is intentional deployment policy for Token I/O separation.
- Built-in Explore or Plan may be used for bounded one-shot research when appropriate, but they are not the sticky Primary Execution Session because they do not provide the resumable agent identity required for Session Affinity.

## Provider boundary

On the Anthropic API, current Claude Code documentation maps the `sonnet` alias to Sonnet 5 and the `opus` alias to Opus 5, but other providers can map the same aliases to older versions. This Profile therefore uses `claude-sonnet-5` explicitly and must not be assumed compatible with Amazon Bedrock, Google Cloud Agent Platform, Microsoft Foundry, gateways, or organization model overrides without verifying the effective model identity.

A future provider-specific deployment should add its own Profile or an explicitly validated variant instead of weakening this Profile's exact binding.