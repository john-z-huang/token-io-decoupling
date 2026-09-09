# Claude Code Host Adapter

This file describes the Claude Code mechanics used by the Anthropic Coding deployment registered by this Skill. It does not own Coding role definitions or concrete model policy. Role mapping is resolved by [`../../coding/runtime.md`](../../coding/runtime.md), while concrete Anthropic model bindings are defined by the selected Model Profile.

This adapter is based on the current Claude Code product documentation. The repository environment used to author this adapter does not have the `claude` CLI installed, so the integration is documentation-backed rather than locally smoke-tested. Do not convert that limitation into a claim that Claude Code behavior has been empirically verified here.

## Host identity

Use this adapter only when the running Code Agent environment is actually Claude Code. Do not infer Host identity from repository contents, a `CLAUDE.md` file, a `.claude/` directory, Skill installation paths, or prompt wording alone.

When Claude Code exposes the active model, effort, provider, organization restrictions, subagent task state, or actual subagent runtime, use those facts for Runtime resolution. In interactive Claude Code, `/status`, `/model`, `/effort`, and `/tasks` are useful host surfaces for inspecting effective configuration. If required identity or capability information cannot be confirmed, report that uncertainty to the Coding Runtime Contract instead of guessing.

## Skill installation and persistent bootstrap

Claude Code supports Agent Skills directly:

- personal Skill: `~/.claude/skills/token-io-decoupling/SKILL.md`;
- project Skill: `.claude/skills/token-io-decoupling/SKILL.md`;
- a symlinked Skill directory is also supported by Claude Code for personal/project Skill locations.

Use the normal `SKILL.md` entry. Do not create a Claude-specific duplicate of the Core instructions.

When this Skill must be loaded reliably at the start of local Claude Code Coding sessions, use Claude Code's persistent instruction mechanism rather than copying the full Skill into every prompt. A short user bootstrap may live in `~/.claude/CLAUDE.md`; project policy belongs in `./CLAUDE.md` or `./.claude/CLAUDE.md`. Keep the bootstrap concise and point it to the installed Skill so the Skill can perform Flow and Runtime routing itself.

Claude Code reads `CLAUDE.md`, not `AGENTS.md`, as its native persistent instruction file. A project may import an existing `AGENTS.md` from `CLAUDE.md` when both products need the same project rules, but do not duplicate the complete Token I/O Decoupling policy in both files.

Cloud Claude Code sessions do not read a machine's personal `~/.claude/skills/`; use a project Skill committed under `.claude/skills/`, a supported synced skill, or another deployment mechanism that the cloud session actually loads.

## Independent Primary Output mapping

When the active Model Profile requires an independent Primary Output, verifier, auxiliary Worker, or targeted escalation runtime, use a Claude Code subagent with its own isolated context.

For a sticky Primary Execution Session, use a resumable custom subagent or the resumable general-purpose agent path rather than the built-in Explore or Plan agents:

- each normal custom/general-purpose subagent invocation starts with a fresh isolated context;
- a completed resumable subagent returns an agent ID; follow-up work should resume/message that same agent instead of spawning a new one when Session Affinity applies;
- built-in Explore and Plan are one-shot and do not return a resumable agent ID, so they may perform bounded read-only research but must not become the long-lived Primary Execution Session;
- the subagent does not automatically inherit the parent's conversation history or previously invoked Skills. The parent must provide the narrow task/Contract information required by Core rules, and the worker must load the relevant Skill references when its execution depends on them.

A logical role change inside a compatible Single-Session Coding Mode is not a reason to spawn a subagent.

## Model and effort selection

Claude Code custom subagents support explicit per-invocation or frontmatter model selection and an `effort` override. The Adapter owns the mechanism for requesting these controls; the selected Model Profile owns the exact model ID and effort policy.

Prefer explicit runtime requests for Profile-bound work rather than relying on the subagent's inherited model. For persistent/reusable custom subagents, the same requirements may be encoded in the subagent definition, but a repository-specific custom agent file is not required by this Skill.

Claude Code can substitute a requested subagent model when organization `availableModels`, provider behavior, or other model restrictions prevent the exact request. Therefore a successful dispatch is not enough to prove Profile compliance:

1. request the Profile-required model and effort;
2. inspect the effective subagent model/effort when Claude Code exposes them (for example through the running task display or result metadata);
3. if the actual runtime does not satisfy the Profile binding, treat it as a capability mismatch and follow the Profile's unavailable rule.

Do not reinterpret Claude Code's automatic model substitution as permission for this Skill to silently relax its Model Profile.

Organization effort caps can also clamp a requested level. If the Profile requires a level that is not actually applied, return that fact to the Profile instead of assuming the requested value took effect.

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

A Primary Output subagent follows the Core delegation boundary: it must not recursively create another execution hierarchy merely because Claude Code exposes the `Agent` tool. Fresh verifiers, parallel Workers, and targeted escalation remain parent-orchestrated decisions.

If a subagent needs the full Token I/O Decoupling Skill to execute its role reliably, prefer loading/invoking the Skill in that subagent or using a custom subagent configuration that preloads it. Do not make the parent regenerate the full Skill text into every delegation message.

## Adoption checks

After installing or changing the Skill or Claude Code runtime configuration, validate a new Coding session with a small non-destructive task:

1. confirm the Skill is discoverable and Coding Flow loads the Runtime Registry;
2. confirm this Host Adapter is selected because the actual Host is Claude Code;
3. confirm the active Model Profile requests the intended runtime;
4. when two-Session mode is selected, confirm the Primary Output subagent actually runs on the Profile-bound model/effort rather than a substituted runtime;
5. confirm related follow-up work resumes the same Primary Execution subagent when Session Affinity applies;
6. confirm Coding Core documents remain vendor-neutral.

If the environment cannot perform one of these checks, report the unverified capability instead of presenting the deployment as fully smoke-tested.

## Official capability references

Current Claude Code behavior described by this Adapter is documented in the official Claude Code pages for Skills, custom subagents, model configuration, settings, and `CLAUDE.md` memory/instructions. Because these product surfaces can change, update this Adapter when those mechanics change; do not move product-specific changes into Coding Core.