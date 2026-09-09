# Anthropic Coding Model Profile

This file owns the concrete Anthropic model bindings and execution-tier policy for the Claude Code Coding deployment registered by this Skill. It is deployment policy, not the Token I/O Decoupling architecture. Host-specific mechanics are supplied by the Claude Code Host Adapter; generic Session semantics are defined by [`../../coding/session-model.md`](../../coding/session-model.md) and [`../../coding/runtime.md`](../../coding/runtime.md).

This Profile targets Claude Code using the Anthropic API model family. Other Claude Code providers may resolve aliases differently or expose different model availability; do not reuse this Profile for those deployments unless the actual runtime satisfies the bindings below.

## Role bindings and execution tiers

At Coding Flow startup, confirm the current Session's actual model identity through the Host Adapter before applying this Profile:

- **Input-side Reasoning**: the current advanced Claude parent Session owns high-value semantic decisions. This Profile assumes the parent is an advanced reasoning-capable Claude runtime selected for the main session; it does not authorize Haiku-class or otherwise lightweight runtimes to own the input-side responsibility merely because they can code.
- **Substantive Primary Output**: the required Anthropic execution model is **`claude-sonnet-5`**.
- **Lightweight Output / Auxiliary Workers**: strictly bounded, low-semantic-risk, mechanically verifiable work should prefer **`claude-haiku-4-5-20251001`** when an independent Worker has concrete model-tiering value.
- **Dual-role eligibility**: when the current Session can explicitly confirm that it is `claude-sonnet-5` and the Host can satisfy the task's required Sonnet effort level in that Session, this Profile declares the current Session eligible for both Input-side Reasoning and substantive Primary Output. The generic runtime mapping therefore enters **Single-Session Coding Mode** unless a concrete structural reason requires another Session.
- **Normal two-Session mapping**: when the current advanced parent Session is not `claude-sonnet-5`, keep the parent constrained to the input-side reasoning responsibility and create/reuse an independent `claude-sonnet-5` Primary Output subagent for substantive execution.

The bindings use full model IDs instead of `sonnet` or `haiku` aliases. Claude Code aliases are provider-dependent and can advance to newer model versions over time; this Profile intentionally requires explicit runtime identity so alias drift does not silently change the deployment.

Single-Session Coding Mode remains a statement about the **substantive Primary Execution Session**, not a prohibition on useful auxiliary model tiering. A current Sonnet 5 Session may directly own substantive exploration, implementation, debugging, mechanical verification, and output while still creating a Haiku auxiliary Worker when the bounded task is cheaper to isolate and there is concrete structural benefit. That auxiliary dispatch does not turn the primary topology into normal two-Session Primary Output mode.

## Model routing before effort routing

This Profile selects the **model tier first**, then applies model-specific runtime controls.

### Route to Haiku 4.5

Prefer `claude-haiku-4-5-20251001` when the task is strictly bounded, low semantic risk, and easy to verify mechanically. Suitable work includes:

- bounded repository/file/symbol exploration and factual inventory that does not decide architecture or product semantics;
- running already-selected build/test/lint/formatter/type-check commands, collecting failures, and compressing raw logs into facts;
- file/path metadata collection, exact search/extraction, deterministic formatting, literal replacement, generated-table updates, and similarly mechanical transformations;
- small documentation/comment synchronization when the intended meaning is already fixed by the Semantic Contract;
- implementing simple unit-test cases whose behavior and expected assertions are already specified;
- parallel read-only research on independent questions where the result can be mechanically or semantically checked by the parent/Sonnet execution path.

Haiku is a **bounded executor and evidence worker**, not a cheaper substitute for substantive Primary Output. Do not give it Semantic Contract ownership, architecture/product decisions, cross-module implementation, non-trivial debugging, complex test design, public API/schema/migration/permission changes, security-sensitive changes, or tasks whose correct execution depends on substantial autonomous judgment.

If a task begins in the Haiku tier but discovers ambiguity that changes goals, architecture, compatibility, risk, or acceptance, stop that direction and return the compressed facts to the parent. The parent may amend the Contract and reroute the next stage to Sonnet.

### Route to Sonnet 5

Use `claude-sonnet-5` for substantive Primary Output, including general feature implementation, non-trivial refactoring/debugging, cross-module changes, complex tests or verification logic, approved migrations, compatibility-sensitive work, security-sensitive work, and any execution requiring substantial implementation judgment.

When uncertain whether a task is genuinely low-risk and mechanically verifiable, prefer Sonnet rather than stretching the Haiku boundary.

## Sonnet effort selection

Claude Code currently supports `low`, `medium`, `high`, `xhigh`, and `max` effort for Sonnet 5. Apply effort only **after** the task has been routed to Sonnet:

- **Substantive Primary Output**: use `effort=xhigh` for general feature implementation, non-trivial refactoring/debugging, complex test/verification code, migration work within an approved Contract, and other tasks where substantial implementation judgment is expected.
- **Bounded Sonnet support work**: use `effort=high` when the task still needs Sonnet-level judgment but is narrower than normal Primary Output, for example a focused technical document, a non-trivial but local test, or a constrained implementation that is not safely Haiku-eligible.
- **Lower Sonnet effort**: `medium`/`low` are not the default cost-control mechanism for work that could safely move to Haiku. Use them only when the task still specifically requires Sonnet but can trade reasoning depth for cost/latency.
- **Targeted escalation**: reserve `effort=max` for a narrowly scoped task that an existing Sonnet `high`/`xhigh` Worker has repeatedly failed, oscillated on, or become clearly blocked by.

Effort names are host/runtime controls, not universal capability units. The same label is calibrated per model and must not be treated as a cross-model measure of intelligence.

## Haiku reasoning-control boundary

Do **not** copy Sonnet's `high`/`xhigh`/`max` policy onto Haiku. Current Claude Code effort support does not include Haiku 4.5, so this Profile controls Haiku cost/capability primarily through **task eligibility and model choice**, not an assumed effort tier.

Haiku 4.5 has different thinking semantics from Sonnet 5 at the Anthropic API layer. This Profile does not require a fixed-thinking budget or invent an effort equivalent for Haiku. If a bounded task needs materially more reasoning than ordinary Haiku execution can provide, reroute it to Sonnet instead of emulating Sonnet effort on Haiku.

## Targeted max escalation

`effort=max` is an exception for Sonnet, not the normal Primary Output setting and not a Haiku setting.

Use a new, narrowly scoped `claude-sonnet-5` max-effort Worker only when an existing Sonnet `high`/`xhigh` Worker has repeatedly failed, oscillated, or become clearly blocked on one specific task. When possible, the predecessor first writes reusable context/handoff documents in the primary worktree as defined by [`../../coding/context-exchange.md`](../../coding/context-exchange.md), and the max Worker reads those documents instead of restarting project exploration from zero.

After the blocker is resolved, follow-on work returns to the normal Sonnet `xhigh`/`high` tiers or the Haiku lightweight tier when the new task independently qualifies for Haiku.

A current Sonnet 5 Session in Single-Session Coding Mode may create another Agent for fresh verification, real parallelism, clearly degraded/overgrown current context, explicit isolation benefit, targeted max escalation, **or bounded Haiku model tiering**. Repository size, long output, build/test work, or generic task complexity are not by themselves reasons to split substantive Primary Output into another Sonnet Session.

## Claude Code model-substitution boundary

Claude Code can replace or fail over a requested subagent model because of organization `availableModels`, provider restrictions, configured fallback chains, or runtime availability. That Host behavior is **not** a Profile fallback.

For every independent Profile-bound Worker:

1. request the exact model required by its tier (`claude-sonnet-5` or `claude-haiku-4-5-20251001`);
2. request Sonnet effort only when the selected tier requires it;
3. verify the effective runtime when Claude Code exposes it;
4. if the actual model no longer matches the selected tier, do not silently reinterpret the Worker as Profile-compatible;
5. if Sonnet effort is clamped below the task's required level, apply the unavailable rules below.

A warning-free tool call is not sufficient evidence that the requested runtime was honored, especially in non-interactive/background execution where clamps or substitutions may be less visible.

## Profile constraints and unavailable handling

- Do not silently replace substantive Primary Output `claude-sonnet-5` with Opus, Haiku, Fable, another Sonnet version, or an inherited parent model.
- Do not silently replace a Haiku-tier Worker with Sonnet and call that a cost-preserving success. If Haiku is unavailable, the parent may deliberately reroute the bounded task to Sonnet only after recognizing that the cheaper tier is unavailable; that is an explicit policy decision, not Host fallback acceptance.
- If an independent substantive Primary Output is required but `claude-sonnet-5` cannot be selected or verified, stop the corresponding substantive Coding work and briefly report the runtime block.
- If Sonnet effort cannot actually be applied because of provider support or an organization cap, stop the affected substantive task rather than pretending the requested level took effect.
- If a Haiku-eligible task cannot use the exact Haiku binding, either keep it with an already-authorized current Session when that does not violate Context Firewall/role policy, explicitly reroute it to Sonnet, or report the capability/cost-tier mismatch. Never accept an unknown substituted model as equivalent.
- Do not move high-volume substantive project-state work back into an advanced parent Session merely because Claude Code inherited or substituted that model. Token I/O separation remains intentional deployment policy.

## Provider boundary

On the Anthropic API, this Profile currently binds `claude-sonnet-5` and active Haiku 4.5 model ID `claude-haiku-4-5-20251001`. Other providers can expose different identifiers, availability, context limits, thinking controls, or alias mappings. Do not assume Amazon Bedrock, Google Cloud Agent Platform, Microsoft Foundry, gateways, or organization overrides satisfy this Profile without verifying the effective runtime.

A future provider-specific deployment should add its own Profile or an explicitly validated variant instead of weakening these exact bindings.