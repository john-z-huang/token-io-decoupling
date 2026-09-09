# Claude Code Host Adapter

This file describes the Claude Code mechanics used by the Anthropic Coding deployment registered by this Skill. It does not own Coding role definitions or concrete model policy. Role mapping is resolved by [`../../coding/runtime.md`](../../coding/runtime.md), while concrete Anthropic model bindings are defined by the selected Model Profile.

This adapter is based on the current Claude Code product documentation. The repository environment used to author this adapter does not have the `claude` CLI installed, so the integration is documentation-backed rather than locally smoke-tested. Do not convert that limitation into a claim that Claude Code behavior has been empirically verified here.

## Host identity

Use this adapter only when the running Code Agent environment is actually Claude Code. Do not infer Host identity from repository contents, a `CLAUDE.md` file, a `.claude/` directory, Skill installation paths, or prompt wording alone.

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

## Independent execution mapping

When the active Model Profile requires an independent Primary Output, verifier, auxiliary Worker, lightweight model-tier Worker, or targeted escalation runtime, use a Claude Code subagent with its own isolated context.

For a sticky Primary Execution Session, use a resumable custom subagent or the resumable general-purpose agent path rather than the built-in Explore or Plan agents:

- each normal custom/general-purpose subagent invocation starts with a fresh isolated context;
- a completed resumable subagent returns an agent ID; follow-up work should resume/message that same agent instead of spawning a new one when Session Affinity applies;
- built-in Explore and Plan are one-shot and do not return a resumable agent ID, so they may perform bounded read-only research but must not become the long-lived Primary Execution Session;
- the subagent does not automatically inherit the parent's conversation history or previously invoked Skills. The parent must provide the narrow task/Contract information required by Core rules, and the worker must load the relevant Skill references when its execution depends on them.

A logical role change inside a compatible Single-Session Coding Mode is not a reason to spawn another substantive Primary Output subagent. However, an independent lower-cost auxiliary Worker can still be justified by concrete model-tiering benefit when the active Profile declares the task eligible.

## Model selection and lightweight Haiku workers

Claude Code custom subagents support explicit per-invocation or frontmatter model selection and can therefore implement the Model Profile's Sonnet/Haiku execution tiers. The Adapter owns the mechanism for requesting these controls; the selected Model Profile owns the exact model IDs and task eligibility.

Prefer explicit runtime requests for Profile-bound work rather than relying on the subagent's inherited model. For persistent/reusable custom subagents, the same requirements may be encoded in the subagent definition, but a repository-specific custom agent file is not required by this Skill.

### One-shot read-only exploration

Do **not** assume Claude Code's built-in Explore agent is always a Haiku-cost worker. Current Claude Code versions make built-in Explore inherit the main conversation model (subject to the product's documented cap/override behavior). Therefore:

- built-in Explore may still be used for bounded one-shot read-only research when cost tier is not required to be Haiku;
- if the active Anthropic Profile requires exploration to stay on the Haiku tier, use a custom/user/project `Explore` definition with an explicit Haiku model or another explicit Haiku custom subagent;
- a custom subagent named `Explore` overrides the built-in Explore and keeps its own model field;
- for repeated lightweight execution that needs context continuity, prefer a resumable custom/general-purpose Haiku subagent instead of repeated one-shot Explore calls.

This distinction keeps the Profile's cost policy explicit rather than depending on a built-in agent default that can change across Claude Code releases.

## Effort selection

Claude Code custom subagents can support an `effort` override when the selected model supports Claude Code effort levels. The Adapter only owns how an effort request is applied; the Model Profile decides whether the selected model uses effort at all.

Do not assume every Anthropic model supports the same effort surface. Current Claude Code effort support includes Sonnet 5 but not Haiku 4.5. A Haiku-tier Worker therefore must not inherit Sonnet's `high`/`xhigh`/`max` policy merely because the subagent schema has an `effort` field. If a Profile needs more reasoning than its Haiku tier can provide, reroute the task to the Profile's Sonnet tier.

Organization effort caps can clamp a requested Sonnet level. If the Profile requires a level that is not actually applied, return that fact to the Profile instead of assuming the requested value took effect.

## Runtime substitution and fallback

Claude Code can substitute or fail over a requested subagent model when organization `availableModels`, provider behavior, configured fallback chains, or other runtime restrictions prevent the exact request. Therefore a successful dispatch is not enough to prove Profile compliance:

1. request the Profile-required model and any model-supported effort;
2. inspect the effective subagent runtime when Claude Code exposes it, for example through task/result surfaces;
3. if the actual runtime does not satisfy the selected Profile tier, treat it as a capability mismatch and follow the Profile's unavailable/rerouting rule.

Do not reinterpret Claude Code's automatic model substitution or fallback chain as permission for this Skill to silently relax its Model Profile.

## Foreground, background, and tool availability

Claude Code may run subagents in foreground or background. Background subagents receive a narrower built-in tool set than foreground subagents. Select the execution form according to the tools required by the approved stage; do not move a task to background merely for parallelism if the narrowed tool set prevents correct execution.

The Token I/O Decoupling architecture does not require Agent Teams, cross-session messaging, dynamic workflows, hooks, or other Claude Code-specific orchestration layers. They may exist in the Host, but this adapter must remain functional through ordinary Skill + subagent operations.

## Filesystem and worktree mapping

Claude Code custom subagents support `isolation: worktree`, which creates an isolated repository worktree for the subagent. Use it when the Core workflow requires an independent code working copy or when real parallel writes need physical separation.

`isolation: worktree` improves working-copy separation but does not automatically satisfy every Context Exchange capability requirement. Continue to follow [`../../coding/context-exchange.md`](../../coding/context-exchange.md):

- each Worker owns only its assigned code worktree and Context Exchange subdirectory;
- cross-Worker context should be exposed as narrowly as the Host can support;
- do not claim path-level RO/DENY isolation unless the active Claude Code sandbox/permissions actually enforce it;
- when safe targeted RO access is unavailable, use the Core-defined mechanical-copy fallback before parent-generated retransmission.

Claude Code applies additional command/path checks to worktree-isolated subagents, but the Adapter must still describe only the guarantees available in the active version and configuration.

## Delegation boundary

A Primary Output or auxiliary subagent follows the Core delegation boundary: it must not recursively create another execution hierarchy merely because Claude Code exposes the `Agent` tool. Fresh verifiers, parallel Workers, Haiku auxiliaries, and targeted escalation remain parent-orchestrated decisions.

If a subagent needs the full Token I/O Decoupling Skill to execute its role reliably, prefer loading/invoking the Skill in that subagent or using a custom subagent configuration that preloads it. Do not make the parent regenerate the full Skill text into every delegation message.

## Adoption checks

After installing or changing the Skill or Claude Code runtime configuration, validate a new Coding session with a small non-destructive task:

1. confirm the shared source exists at `~/.agents/skills/token-io-decoupling/` and Claude Code discovers the symlinked personal entry when personal installation is used;
2. confirm the Skill is discoverable and Coding Flow loads the Runtime Registry;
3. confirm this Host Adapter is selected because the actual Host is Claude Code;
4. confirm the active Model Profile requests the intended Sonnet or Haiku runtime for each task class;
5. when substantive two-Session mode is selected, confirm the Primary Output subagent actually runs on the Profile-bound Sonnet model/effort rather than a substituted runtime;
6. when a Haiku-tier auxiliary is selected, confirm its actual model is the Profile-bound Haiku runtime and that no unsupported Sonnet-style effort assumption was applied;
7. confirm related follow-up work resumes the same Primary Execution subagent when Session Affinity applies;
8. confirm Coding Core documents remain vendor-neutral.

If the environment cannot perform one of these checks, report the unverified capability instead of presenting the deployment as fully smoke-tested.

## Official capability references

Current Claude Code behavior described by this Adapter is documented in the official Claude Code pages for Skills, custom subagents, model configuration, settings, and `CLAUDE.md` memory/instructions. Because these product surfaces can change, update this Adapter when those mechanics change; do not move product-specific changes into Coding Core.