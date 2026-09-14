# Claude Code + Anthropic Coding Deployment

This file is the registered Coding deployment document for Claude Code with the Anthropic model family. It covers both deployment concerns for this product/provider pair:

- **Host mechanics**: how Claude Code exposes persistent instructions, independent subagent execution, model and effort selection, filesystem or sandbox capability, and context transport.
- **Model policy**: which Anthropic execution tier is eligible for each Coding role, which controls apply to which task class, substitution handling, and what to do when a required binding is unavailable.

It does not own Coding role definitions or Session semantics. Role mapping is resolved by [`../../coding/runtime.md`](../../coding/runtime.md) and [`../../coding/session-model.md`](../../coding/session-model.md).

Host mechanics described here are backed by the official Claude Code documentation for Skills, custom subagents, model configuration, settings, and `CLAUDE.md` memory/instructions; the adoption checks below record what live use has and has not exercised.

This deployment targets Claude Code using the Anthropic API model family. Other Claude Code providers may resolve aliases differently or expose different model availability; do not reuse these bindings for those deployments unless the actual runtime satisfies them.

## Host identity

Use this deployment only when the running Code Agent environment is actually Claude Code. Do not infer Host identity from repository contents, a `CLAUDE.md` file, a `.claude/` directory, Skill installation paths, or prompt wording alone.

When Claude Code exposes the active model, effort, provider, organization restrictions, subagent task state, or actual subagent runtime, use those facts for Runtime resolution. In interactive Claude Code, `/status`, `/model`, `/effort`, and `/tasks` are useful host surfaces for inspecting effective configuration. If required identity or capability information cannot be confirmed, report that uncertainty to the Coding Runtime Contract instead of guessing.

## Skill installation and persistent bootstrap

For personal installation, keep a single canonical copy of this Skill at `~/.agents/skills/token-io-decoupling/`. Do not maintain a second Claude-specific copy merely because Claude Code's native personal discovery directory is `~/.claude/skills/`.

Claude Code supports symlinked Skill directories, so the recommended local mapping is:

```bash
mkdir -p ~/.claude/skills
ln -s ~/.agents/skills/token-io-decoupling ~/.claude/skills/token-io-decoupling
```

The resulting Claude Code discovery entry remains `~/.claude/skills/token-io-decoupling/SKILL.md`, but `~/.agents/skills/token-io-decoupling/` is the source of truth. If the link already exists, update or repair the link rather than copying the Skill tree into both locations.

Project-scoped Skills remain native project assets under `.claude/skills/<skill-name>/SKILL.md`; they are intentionally not redirected to the personal shared directory because their repository/version-control scope is different.

Use the normal `SKILL.md` entry. Do not create a Claude-specific duplicate of the Core instructions.

When this Skill must be loaded reliably at the start of local Claude Code Coding sessions, use Claude Code's persistent instruction mechanism rather than copying the full Skill into every prompt. A short user bootstrap may live in `~/.claude/CLAUDE.md`; project policy belongs in `./CLAUDE.md` or `./.claude/CLAUDE.md`. Keep the bootstrap concise and point it to the installed Skill so the Skill can perform Flow and Runtime routing itself.

Claude Code reads `CLAUDE.md`, not `AGENTS.md`, as its native persistent instruction file. A project may import an existing `AGENTS.md` from `CLAUDE.md` when both products need the same project rules, but do not duplicate the complete Token I/O Decoupling policy in both files.

Cloud Claude Code sessions do not read a machine's personal `~/.claude/skills/` or the local shared `~/.agents/skills/`; use a project Skill committed under `.claude/skills/`, a supported synced skill, or another deployment mechanism that the cloud session actually loads.

## Role bindings and execution tiers

At Coding Flow startup, confirm the current Session's actual model identity through the host surfaces above before applying these bindings:

- **Input-side Reasoning**: the current advanced Claude parent Session owns high-value semantic decisions. This deployment assumes the parent is an advanced reasoning-capable Claude runtime selected for the main session; it does not authorize Haiku-class or otherwise lightweight runtimes to own the input-side responsibility merely because they can code.
- **Substantive Primary Output**: the required Anthropic execution model is **`claude-sonnet`**.
- **Change Verification**: when selected, start one fresh independent **`claude-sonnet`** Session for the task conversation's final change-result verification, then reuse that verifier for later verification slices. Each new final-state fingerprint/epoch must be independently re-evaluated; an earlier verdict is not evidence. Create additional verifier Sessions only for genuinely isolated requirements, such as incompatible environments/snapshots, distinct permission or security domains, or an explicit independent audit.
- **Documentation/Comments & Git Operations**: when selected, use a separate **`claude-sonnet`** Session for approved post-verification documentation/code-comment materialization and all non-trivial repository Git operations. It owns synchronization, branch/worktree operations, staging, commits, history integration, reset/clean/stash, conflict handling, tags, remotes, pushes, and applicable Issue/PR delivery; only tiny read-only Git metadata queries remain outside this role.
- **Context Bootstrap/Refresh**: when selected, use a dedicated or reusable **`claude-sonnet`** Worker with `effort=medium` by default for bounded factual and policy-routing capsule materialization. Deterministic metadata/source-hash or delta-refresh capsule work may instead use **`claude-haiku`** when it stays mechanically verifiable, or `effort=low` when it must stay on Sonnet. Semantic interpretation remains with Input-side Reasoning.
- **Lightweight Output / Auxiliary Workers**: strictly bounded, low-semantic-risk, mechanically verifiable work should prefer **`claude-haiku`** when an independent Worker has concrete model-tiering value.
- **Dual-role eligibility**: when the current Session can explicitly confirm that it is `claude-sonnet` and the host can satisfy the task's required Sonnet effort level in that Session, this deployment declares the current Session eligible for both Input-side Reasoning and substantive Primary Output. The generic runtime mapping therefore enters **Single-Session Coding Mode** unless a concrete structural reason requires another Session.
- **Normal two-Session mapping**: when the current advanced parent Session is not `claude-sonnet`, keep the parent constrained to the input-side reasoning responsibility and create/reuse an independent `claude-sonnet` Primary Output subagent for substantive execution.

The bindings deliberately use the provider's tier aliases `claude-sonnet` and `claude-haiku` rather than pinned version IDs. Claude Code resolves each alias to the newest model version the host currently serves, so this deployment follows the product's current model for each tier without an edit here. What it commits to is therefore a **tier-level** guarantee — substantive execution on the Sonnet tier, lightweight execution on the Haiku tier — not a specific version. Record which concrete version each alias resolves to at Coding Flow startup, and re-run the adoption checks when it moves.

Single-Session Coding Mode remains a statement about the **substantive Primary Execution Session**, not a prohibition on useful auxiliary model tiering. A current Sonnet-tier Session directly performs source/project exploration, implementation, debugging, provisional focused checks, and implementation output rather than delegating ordinary work to another Sonnet Session merely to preserve a two-role topology. It does not absorb non-trivial Git operations, and it does not remove the verification or delivery roles: for a material functional change the Input-side Agent still starts one fresh independent Change Verification Session and reuses it for later verification epochs in the same task conversation, and may create a separate Documentation/Comments & Git Operations Session when documentation or non-trivial Git work is needed.

A Session in Single-Session Coding Mode may create another Agent only for the initial selected independent verification, post-verification documentation/comment or non-trivial Git-operation isolation, real parallelism, clearly degraded/overgrown current context, explicit isolation benefit, **or bounded Haiku model tiering**. Repository size, long output, build/test work, or generic task complexity are not by themselves reasons to split substantive Primary Output into another Sonnet Session.

## Independent execution mapping

When this deployment requires an independent Primary Output, verifier, auxiliary Worker, lightweight model-tier Worker, or targeted escalation runtime, use a Claude Code subagent with its own isolated context.

For a sticky Primary Execution Session, use a resumable custom subagent or the resumable general-purpose agent path rather than the built-in Explore or Plan agents:

- each normal custom/general-purpose subagent invocation starts with a fresh isolated context;
- a completed resumable subagent returns an agent ID; follow-up work should resume/message that same agent instead of spawning a new one when Session Affinity applies;
- state the assigned model binding — the tier alias, plus the concrete version when the host has already resolved it — and effort level in each newly created subagent's instruction body in readable text, even when also setting them through host controls; the subagent must not be expected to infer this assignment from tool arguments or its runtime identity. When reusing a subagent with the same assignment already stated, do not repeat it mechanically; state it when the assignment changes or the prior instruction was missing or unclear;
- built-in Explore and Plan are one-shot and do not return a resumable agent ID, so they may perform bounded read-only research but must not become the long-lived Primary Execution Session;
- the subagent does not automatically inherit the parent's conversation history or previously invoked Skills. The parent must provide the narrow task/Contract information required by Core rules, and the worker must load the relevant Skill references when its execution depends on them.

If the current Claude Code environment cannot create the required independent subagent context, cannot select the required model, or cannot satisfy a required runtime parameter, return that capability failure to the unavailable-handling rules below instead of substituting another model.

## Model routing and lightweight workers

This deployment selects the **model tier first**, then applies the controls that tier actually supports. Custom subagents support explicit per-invocation or frontmatter model selection, so request the bound tier explicitly rather than relying on the subagent's inherited model. For persistent/reusable custom subagents the same requirements may be encoded in the subagent definition, but a repository-specific custom agent file is not required by this Skill.

A host UI, task list, or tool result may already display equivalent dispatch information; shared `Dispatch Preview` rules determine whether an additional visible preview is necessary, and this deployment does not create a second, product-specific reporting protocol.

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

### One-shot read-only exploration

Do **not** assume Claude Code's built-in Explore agent is always a Haiku-cost worker. Current Claude Code versions make built-in Explore inherit the main conversation model (subject to the product's documented cap/override behavior). Therefore:

- built-in Explore may still be used for bounded one-shot read-only research when cost tier is not required to be Haiku;
- if this deployment requires exploration to stay on the Haiku tier, use a custom/user/project `Explore` definition with an explicit Haiku model or another explicit Haiku custom subagent;
- a custom subagent named `Explore` overrides the built-in Explore and keeps its own model field;
- for repeated lightweight execution that needs context continuity, prefer a resumable custom/general-purpose Haiku subagent instead of repeated one-shot Explore calls.

This distinction keeps the cost policy explicit rather than depending on a built-in agent default that can change across Claude Code releases.

## Effort selection

Claude Code custom subagents can support an `effort` override when the selected model supports Claude Code effort levels, and the host owns how that request is applied. Apply effort only **after** the task has been routed to a tier, and only on a tier that actually exposes it.

On the Sonnet tier this deployment uses `low`, `medium`, and `high`, and these are the only bands it uses. Choose the band from the task's actual difficulty:

- **`low`**: simple documentation edits and simple code writing — documentation/comment synchronization whose meaning is already fixed, and small, well-specified code changes that need little reasoning depth.
- **`medium`**: ordinary development. This is the default band for general feature implementation, routine refactoring or debugging, and implementation-feedback test code.
- **`high`**: difficult tasks — cross-module changes, non-trivial debugging, compatibility- or security-sensitive work, approved migrations, complex test/verification logic, and any task that has already resisted `medium`. This is the highest band this deployment uses; a task that `high` cannot resolve is a runtime or semantic blocker to report rather than a reason to seek a stronger setting.

Role placement:

- **Substantive Primary Output**: `medium` for ordinary development, `low` for a released task that is a simple documentation edit or simple code writing, and `high` when the task is genuinely difficult. This ladder does not transfer ownership of problem formulation, architecture choice, unresolved semantic trade-offs, or acceptance to the Primary Output role; output length or project size alone does not justify moving up a band.
- **Change Verification**: a selected verifier defaults to `high` because it must independently choose and interpret holistic checks across the final changed state. It owns verification evidence only; it does not own repair, architecture decisions, or semantic acceptance.
- **Documentation/Comments & Git Operations**: `low` for bounded developer documentation/code-comment materialization, and `medium` for non-trivial repository Git work, which is routine operation rather than a simple edit. Its documentation write scope excludes functionality and tests; its Git scope is limited to the explicitly released repository/worktree/ref/remote operations. It must not be used to compensate for failed verification or to make unapproved product decisions.
- **Other auxiliary Sonnet Workers**: `medium` by default, moving to `high` only when the concrete task is genuinely difficult and to `low` only when it is a simple documentation edit or simple code writing.

Organization effort caps can clamp a requested Sonnet level. If the required level is not actually applied, follow the unavailable rules instead of assuming the requested value took effect.

Effort names are host/runtime controls, not universal capability units. The same label is calibrated per model and must not be treated as a cross-model measure of intelligence.

## Haiku reasoning-control boundary

Do **not** copy Sonnet's `low`/`medium`/`high` policy onto Haiku. In the current product the Haiku tier exposes no effort surface, so this deployment controls Haiku cost/capability primarily through **task eligibility and model choice**, not an assumed effort tier. The host has not been observed to narrow a Worker's tool set by model tier: a Haiku-tier Worker dispatched in the same execution form as any other subagent has been observed to receive the same tool set, so this deployment's Haiku scope comes from the dispatched task's bounded scope rather than from tier-imposed tool restrictions. Tool availability can still differ with execution form; see the `## Foreground, background, and tool availability` section. A Haiku-tier Worker must not inherit Sonnet's bands merely because the subagent schema has an `effort` field. Because the tier alias follows the host's current version, treat that effort surface as a host capability to re-confirm rather than a permanent property: if a future Haiku-tier version gains effort support, this deployment still does not authorize copying Sonnet's bands onto it without an explicit amendment here.

The Haiku and Sonnet tiers have different thinking semantics at the Anthropic API layer. This deployment does not require a fixed-thinking budget or invent an effort equivalent for Haiku. If a bounded task needs materially more reasoning than ordinary Haiku execution can provide, reroute it to Sonnet instead of emulating Sonnet effort on Haiku.

## Runtime substitution and fallback

Claude Code can replace or fail over a requested subagent model because of organization `availableModels`, provider restrictions, configured fallback chains, or runtime availability. That host behavior is **not** a fallback this deployment authorizes, so a successful dispatch is not enough to prove deployment compliance.

Because the bindings use tier aliases rather than pinned versions, distinguish two different events:

- **Tier-consistent version drift** — `claude-sonnet` or `claude-haiku` resolves to a newer version of the same tier than the one previously observed. This is the alias working as intended, not a substitution: continue and record the resolved version.
- **Tier mismatch** — a Sonnet-tier request is served by a Haiku-tier, Opus-tier, or otherwise different tier, or by an unknown model. This is a capability mismatch and follows the unavailable rules below.

For every independent bound Worker:

1. request the tier alias required by its role (`claude-sonnet` or `claude-haiku`), and request effort only on a tier this deployment actually gives an effort level;
2. inspect the effective subagent runtime when Claude Code exposes it, for example through task/result surfaces, and record which concrete version each alias resolved to;
3. if the actual runtime does not satisfy the bound tier, do not silently reinterpret the Worker as deployment-compatible;
4. if a required Sonnet effort level is clamped below the task's need, follow the unavailable rules below.

A warning-free tool call is not sufficient evidence that the requested runtime was honored, especially in non-interactive/background execution where clamps or substitutions may be less visible.

Do not reinterpret Claude Code's automatic model substitution or fallback chain as permission for this Skill to silently relax these bindings.

## Foreground, background, and tool availability

Claude Code may run subagents in foreground or background. Background subagents receive a narrower built-in tool set than foreground subagents. Select the execution form according to the tools required by the approved stage; do not move a task to background merely for parallelism if the narrowed tool set prevents correct execution.

The Token I/O Decoupling architecture does not require Agent Teams, cross-session messaging, dynamic workflows, hooks, or other Claude Code-specific orchestration layers. They may exist in the Host, but this deployment must remain functional through ordinary Skill + subagent operations.

## Filesystem and worktree mapping

When multiple Agents work on the same development request, reuse the task's primary Git worktree by default. A separate Agent/Session, a fresh verifier, a Worker-specific Context Exchange directory, or the availability of `isolation: worktree` does not itself require another worktree. Follow the validation and explicit-isolation exceptions in [`../../coding/context-exchange.md`](../../coding/context-exchange.md); for concurrent write conflicts, assign non-overlapping path scopes or sequence dependent slices first.

Claude Code custom subagents support `isolation: worktree`, which creates an isolated repository worktree for the subagent. Use it only for a concrete isolation need, such as incompatible snapshots/environments, validation writes that cannot be redirected or contained, a separately scoped filesystem view required by a distinct permission/security boundary, or an explicitly isolated audit.

`isolation: worktree` improves working-copy separation but does not automatically satisfy every Context Exchange capability requirement. Continue to follow [`../../coding/context-exchange.md`](../../coding/context-exchange.md):

- when path scoping is available, give each Worker RW access only to its named mutation paths in the shared primary worktree and its own Context Exchange subdirectory; give the verifier RO access to the fixed final state, with RW access limited to verification-script/test paths explicitly authorized in its released slice;
- cross-Worker context should be exposed as narrowly as the Host can support;
- do not claim path-level RO/DENY isolation unless the active Claude Code sandbox/permissions actually enforce it;
- when safe targeted RO access is unavailable, use the Core-defined mechanical-copy fallback before parent-generated retransmission.

Claude Code applies additional command/path checks to worktree-isolated subagents, but this deployment must still describe only the guarantees available in the active version and configuration.

## Delegation boundary

A Primary Output or auxiliary subagent follows the Core delegation boundary: it must not recursively create another execution hierarchy merely because Claude Code exposes the `Agent` tool. Fresh verifiers, parallel Workers, Haiku auxiliaries, and targeted escalation remain parent-orchestrated decisions.

If a subagent needs the full Token I/O Decoupling Skill to execute its role reliably, prefer loading/invoking the Skill in that subagent or using a custom subagent configuration that preloads it. Do not make the parent regenerate the full Skill text into every delegation message.

## Unavailable handling

- Do not silently replace substantive Primary Output `claude-sonnet` with Opus, Fable, a Haiku-tier model, or an inherited parent model. A newer version of the same Sonnet tier resolved by the alias is intended behavior, not a substitution; a different tier is.
- Do not silently replace a Haiku-tier Worker with Sonnet and call that a cost-preserving success. If Haiku is unavailable, the parent may deliberately reroute the bounded task to Sonnet only after recognizing that the cheaper tier is unavailable; that is an explicit policy decision, not host-fallback acceptance.
- If an independent substantive Primary Output is required but `claude-sonnet` cannot be selected or verified, stop the corresponding substantive Coding or verification work and briefly report the runtime block. Do not let Primary Output self-verify a material change because the verifier binding is unavailable.
- If Sonnet effort cannot actually be applied because of provider support or an organization cap, stop the affected substantive task rather than pretending the requested level took effect.
- If a Haiku-eligible task cannot use the bound Haiku tier, either keep it with an already-authorized current Session when that does not violate Context Firewall/role policy, explicitly reroute it to Sonnet, or report the capability/cost-tier mismatch. Never accept an unknown substituted model as equivalent.
- Do not move high-volume substantive project-state work back into an advanced parent Session merely because Claude Code inherited or substituted that model. Token I/O separation remains intentional deployment policy.

## Adoption checks

After installing or changing the Skill or Claude Code runtime configuration, validate a new Coding session with a small non-destructive task:

1. confirm the shared source exists at `~/.agents/skills/token-io-decoupling/` and Claude Code discovers the symlinked personal entry when personal installation is used;
2. confirm the Skill is discoverable and Coding Flow loads the Runtime Registry;
3. confirm this deployment document is selected because the actual Host is Claude Code;
4. confirm the deployment requests the intended Sonnet or Haiku tier for each task class;
5. when substantive two-Session mode is selected, confirm the Primary Output subagent actually runs on the bound Sonnet tier/effort rather than a substituted runtime, and record which concrete version the tier alias resolved to;
6. when a Haiku-tier auxiliary is selected, confirm its actual model belongs to the bound Haiku tier and that no unsupported Sonnet-style effort assumption was applied;
7. confirm related follow-up work resumes the same Primary Execution subagent when Session Affinity applies;
8. confirm Coding Core documents remain vendor-neutral.

Live use of this deployment has exercised Skill discovery and Runtime resolution, host identity resolution, Sonnet-tier Single-Session Coding Mode, vendor-neutral Core loading, a Haiku-tier auxiliary dispatch, an independent Sonnet-tier Primary Output dispatch under the normal two-Session mapping, and resumption of the same Primary Output Session across follow-up slices together with reuse of the same verifier Session for a later verification epoch on a changed final state. Two limits remain. The dispatch surfaces used resolved each tier alias at tier level and reported no concrete version ID, so no pinned model version has been observed, and the version-recording step of adoption check 5 could not be completed on those surfaces — that step therefore remains unfulfilled rather than passed. No effort value was requested through any host control, because the dispatch surface used in live use exposes none; the band therefore travelled as instruction text rather than as an applied setting, and no clamp occurred. A band carried only in text is not proof the requested level took effect — the same caution the substitution rules above apply to a warning-free tool call — while an effort override configured through a custom subagent definition remains the documented mechanism. Anything this document or the host does not expose must still be reported as unverified, and the deployment as a whole must not be presented as uniformly smoke-tested.

## Official capability references

Current Claude Code behavior described by this deployment is documented in the official Claude Code pages for Skills, custom subagents, model configuration, settings, and `CLAUDE.md` memory/instructions. Because these product surfaces can change, update this document when those mechanics change; do not move product-specific changes into Coding Core.
