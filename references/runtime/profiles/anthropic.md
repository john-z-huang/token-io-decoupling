# Anthropic Coding Model Profile

This file owns the concrete Anthropic model bindings and execution-tier policy for the Claude Code Coding deployment registered by this Skill. It is deployment policy, not the Token I/O Decoupling architecture. Host-specific mechanics are supplied by the Claude Code Host Adapter; generic Session semantics are defined by [`../../coding/session-model.md`](../../coding/session-model.md) and [`../../coding/runtime.md`](../../coding/runtime.md).

This Profile targets Claude Code using the Anthropic API model family. Other Claude Code providers may resolve aliases differently or expose different model availability; do not reuse this Profile for those deployments unless the actual runtime satisfies the bindings below.

## Role bindings and execution tiers

At Coding Flow startup, confirm the current Session's actual model identity through the Host Adapter before applying this Profile:

- **Input-side Reasoning**: the current advanced Claude parent Session owns high-value semantic decisions. This Profile assumes the parent is an advanced reasoning-capable Claude runtime selected for the main session; it does not authorize Haiku-class or otherwise lightweight runtimes to own the input-side responsibility merely because they can code.
- **Substantive Primary Output**: the required Anthropic execution model is **`claude-sonnet`**.
- **Change Verification**: when selected, start one fresh independent **`claude-sonnet`** Session for the task conversation's final change-result verification, then reuse that verifier for later verification slices. Each new final-state fingerprint/epoch must be independently re-evaluated; an earlier verdict is not evidence. Create additional verifier Sessions only for genuinely isolated requirements, such as incompatible environments/snapshots, distinct permission or security domains, or an explicit independent audit.
- **Documentation/Comments & Git Operations**: when selected, use a separate **`claude-sonnet`** Session for approved post-verification documentation/code-comment materialization and all non-trivial repository Git operations. It owns synchronization, branch/worktree operations, staging, commits, history integration, reset/clean/stash, conflict handling, tags, remotes, pushes, and applicable Issue/PR delivery; only tiny read-only Git metadata queries remain outside this role.
- **Context Bootstrap/Refresh**: when selected, use a dedicated or reusable **`claude-sonnet`** Worker with `effort=medium` by default for bounded factual and policy-routing capsule materialization. Deterministic metadata/source-hash or delta-refresh capsule work may instead use **`claude-haiku`** when it stays mechanically verifiable, or `effort=low` when it must stay on Sonnet. Semantic interpretation remains with Input-side Reasoning.
- **Lightweight Output / Auxiliary Workers**: strictly bounded, low-semantic-risk, mechanically verifiable work should prefer **`claude-haiku`** when an independent Worker has concrete model-tiering value.
- **Dual-role eligibility**: when the current Session can explicitly confirm that it is `claude-sonnet` and the Host can satisfy the task's required Sonnet effort level in that Session, this Profile declares the current Session eligible for both Input-side Reasoning and substantive Primary Output. The generic runtime mapping therefore enters **Single-Session Coding Mode** unless a concrete structural reason requires another Session.
- **Normal two-Session mapping**: when the current advanced parent Session is not `claude-sonnet`, keep the parent constrained to the input-side reasoning responsibility and create/reuse an independent `claude-sonnet` Primary Output subagent for substantive execution.

The bindings deliberately use the provider's tier aliases `claude-sonnet` and `claude-haiku` rather than pinned version IDs. Claude Code resolves each alias to the newest model version the host currently serves, so this Profile follows the product's current model for each tier without an edit here. What this Profile commits to is therefore a **tier-level** guarantee — substantive execution on the Sonnet tier, lightweight execution on the Haiku tier — not a specific version. Record which concrete version each alias resolves to at Coding Flow startup, and re-run the adoption checks when it moves.

Single-Session Coding Mode remains a statement about the **substantive Primary Execution Session**, not a prohibition on useful auxiliary model tiering. A current Sonnet-tier Session directly performs source/project exploration, implementation, debugging, provisional focused checks, and implementation output rather than delegating ordinary work to another Sonnet Session merely to preserve a two-role topology. It does not absorb non-trivial Git operations. A Haiku auxiliary Worker may still be created when the bounded task is cheaper to isolate and there is concrete structural benefit; that auxiliary dispatch does not turn the primary topology into normal two-Session Primary Output mode.

Single-Session Coding Mode does not remove the verification or delivery roles. For a material functional change, the Input-side Agent still starts one fresh independent Change Verification Session and reuses it for later verification epochs in the same task conversation; each epoch requires independent re-evaluation rather than carrying forward an earlier verdict. It may create additional verifier Sessions only for genuinely isolated requirements, and may create a separate Documentation/Comments & Git Operations Session when documentation or non-trivial Git work is needed.

A current Sonnet-tier Session in Single-Session Coding Mode may create another Agent only for the initial selected independent verification, post-verification documentation/comment or non-trivial Git-operation isolation, real parallelism, clearly degraded/overgrown current context, explicit isolation benefit, **or bounded Haiku model tiering**. Reuse the selected verifier across later verification epochs; additional verifier Sessions require genuinely isolated requirements. Repository size, long output, build/test work, or generic task complexity are not by themselves reasons to split substantive Primary Output into another Sonnet Session.

## Model routing before effort routing

This Profile selects the **model tier first**, then applies model-specific runtime controls.

### Route to Haiku

Prefer `claude-haiku` when the task is strictly bounded, low semantic risk, and easy to verify mechanically. Suitable work includes:

- bounded repository/file/symbol exploration and factual inventory that does not decide architecture or product semantics;
- running already-selected build/test/lint/formatter/type-check commands, collecting failures, and compressing raw logs into facts;
- file/path metadata collection, exact search/extraction, deterministic formatting, literal replacement, generated-table updates, and similarly mechanical transformations;
- small documentation/comment synchronization when the intended meaning is already fixed by the Semantic Contract;
- implementing simple unit-test cases whose behavior and expected assertions are already specified;
- parallel read-only research on independent questions where the result can be mechanically or semantically checked by the parent/Sonnet execution path.

Haiku is a **bounded executor and evidence worker**, not a cheaper substitute for substantive Primary Output. Do not give it Semantic Contract ownership, architecture/product decisions, cross-module implementation, non-trivial debugging, complex test design, public API/schema/migration/permission changes, security-sensitive changes, or tasks whose correct execution depends on substantial autonomous judgment.

If a task begins in the Haiku tier but discovers ambiguity that changes goals, architecture, compatibility, risk, or acceptance, stop that direction and return the compressed facts to the parent. The parent may amend the Contract and reroute the next stage to Sonnet.

### Route to Sonnet

Use `claude-sonnet` for substantive Primary Output, including general feature implementation, non-trivial refactoring/debugging, cross-module changes, complex tests or verification logic, approved migrations, compatibility-sensitive work, security-sensitive work, and any execution requiring substantial implementation judgment.

When uncertain whether a task is genuinely low-risk and mechanically verifiable, prefer Sonnet rather than stretching the Haiku boundary.

## Sonnet effort selection

Claude Code supports `low`, `medium`, and `high` effort on the Sonnet tier, and these are the only bands this deployment uses. Apply effort only **after** the task has been routed to Sonnet, and choose the band from the task's actual difficulty:

- **`low`**: simple documentation edits and simple code writing — documentation/comment synchronization whose meaning is already fixed, and small, well-specified code changes that need little reasoning depth.
- **`medium`**: ordinary development. This is the default band for general feature implementation, routine refactoring or debugging, and implementation-feedback test code.
- **`high`**: difficult tasks — cross-module changes, non-trivial debugging, compatibility- or security-sensitive work, approved migrations, complex test/verification logic, and any task that has already resisted `medium`. This is the highest band this deployment uses; a task that `high` cannot resolve is a runtime or semantic blocker to report rather than a reason to seek a stronger setting.

Role placement:

- **Substantive Primary Output**: `medium` for ordinary development, `low` for a released task that is a simple documentation edit or simple code writing, and `high` when the task is genuinely difficult. This ladder does not transfer ownership of problem formulation, architecture choice, unresolved semantic trade-offs, or acceptance to the Primary Output role; output length or project size alone does not justify moving up a band.
- **Change Verification**: a selected verifier defaults to `high` because it must independently choose and interpret holistic checks across the final changed state. It owns verification evidence only; it does not own repair, architecture decisions, or semantic acceptance.
- **Documentation/Comments & Git Operations**: `low` for bounded developer documentation/code-comment materialization, and `medium` for non-trivial repository Git work, which is routine operation rather than a simple edit. Its documentation write scope excludes functionality and tests; its Git scope is limited to the explicitly released repository/worktree/ref/remote operations. It must not be used to compensate for failed verification or to make unapproved product decisions.
- **Other auxiliary Sonnet Workers**: `medium` by default, moving to `high` only when the concrete task is genuinely difficult and to `low` only when it is a simple documentation edit or simple code writing.

Effort names are host/runtime controls, not universal capability units. The same label is calibrated per model and must not be treated as a cross-model measure of intelligence.

## Haiku reasoning-control boundary

Do **not** copy Sonnet's `low`/`medium`/`high` policy onto Haiku. In the current product the Haiku tier exposes no effort surface, so this Profile controls Haiku cost/capability primarily through **task eligibility and model choice**, not an assumed effort tier. Because the tier alias follows the host's current version, treat that effort surface as a host capability to re-confirm rather than a permanent property: if a future Haiku-tier version gains effort support, this Profile still does not authorize copying Sonnet's bands onto it without an explicit amendment here.

The Haiku and Sonnet tiers have different thinking semantics at the Anthropic API layer. This Profile does not require a fixed-thinking budget or invent an effort equivalent for Haiku. If a bounded task needs materially more reasoning than ordinary Haiku execution can provide, reroute it to Sonnet instead of emulating Sonnet effort on Haiku.

## Claude Code model-substitution boundary

Claude Code can replace or fail over a requested subagent model because of organization `availableModels`, provider restrictions, configured fallback chains, or runtime availability. That Host behavior is **not** a Profile fallback.

Because this Profile binds tier aliases rather than pinned versions, distinguish two different events:

- **Tier-consistent version drift** — `claude-sonnet` or `claude-haiku` resolves to a newer version of the same tier than the one previously observed. This is the intended behavior of the alias and is not a substitution; continue and record the new version.
- **Tier mismatch** — a Sonnet-tier request is served by a Haiku-tier, Opus-tier, or otherwise different tier, or by an unknown model. This is a capability mismatch and follows the unavailable rules below.

For every independent Profile-bound Worker:

1. request the tier alias required by its role (`claude-sonnet` or `claude-haiku`);
2. request Sonnet effort only when the selected tier requires it;
3. verify the effective runtime when Claude Code exposes it, and record which concrete version each alias resolved to;
4. if the actual model does not match the selected tier, do not silently reinterpret the Worker as Profile-compatible;
5. if Sonnet effort is clamped below the task's required level, apply the unavailable rules below.

A warning-free tool call is not sufficient evidence that the requested runtime was honored, especially in non-interactive/background execution where clamps or substitutions may be less visible.

## Profile constraints and unavailable handling

- Do not silently replace substantive Primary Output `claude-sonnet` with Opus, Fable, a Haiku-tier model, or an inherited parent model. A newer version of the same Sonnet tier resolved by the alias is intended behavior, not a substitution; a different tier is.
- Do not silently replace a Haiku-tier Worker with Sonnet and call that a cost-preserving success. If Haiku is unavailable, the parent may deliberately reroute the bounded task to Sonnet only after recognizing that the cheaper tier is unavailable; that is an explicit policy decision, not Host fallback acceptance.
- If an independent substantive Primary Output is required but `claude-sonnet` cannot be selected or verified, stop the corresponding substantive Coding or verification work and briefly report the runtime block. Do not let Primary Output self-verify a material change because the verifier binding is unavailable.
- If Sonnet effort cannot actually be applied because of provider support or an organization cap, stop the affected substantive task rather than pretending the requested level took effect.
- If a Haiku-eligible task cannot use the Profile-bound Haiku tier, either keep it with an already-authorized current Session when that does not violate Context Firewall/role policy, explicitly reroute it to Sonnet, or report the capability/cost-tier mismatch. Never accept an unknown substituted model as equivalent.
- Do not move high-volume substantive project-state work back into an advanced parent Session merely because Claude Code inherited or substituted that model. Token I/O separation remains intentional deployment policy.

## Provider boundary

On the Anthropic API, this Profile binds the `claude-sonnet` and `claude-haiku` tier aliases and leaves the concrete version to the Host. Other providers may resolve the same alias names to different versions, expose different identifiers or availability, or not support tier aliases at all, and they can differ in context limits and thinking controls. Do not assume Amazon Bedrock, Google Cloud Agent Platform, Microsoft Foundry, gateways, or organization overrides satisfy this Profile without verifying the effective runtime.

A future provider-specific deployment should add its own Profile or an explicitly validated variant instead of weakening these exact bindings.