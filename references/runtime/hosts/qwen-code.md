# Qwen Code Host Adapter

This file describes the host-specific mechanics for the Qwen Code deployment. It does not own Coding role definitions or concrete Alibaba Qwen model policy. Role mapping is resolved by [`../../coding/runtime.md`](../../coding/runtime.md); concrete model bindings and effort policy are defined by the selected Model Profile.

## Host identity

Use this Adapter only when the running Code Agent environment is actually Qwen Code. Do not infer Host identity merely from Qwen model names, Alibaba Cloud credentials, repository files, or the presence of `QWEN.md`.

When Qwen Code exposes the active model, provider, effort, Session, or subagent configuration, use those facts for Runtime resolution. If a required capability cannot be confirmed, return that fact to the Coding Runtime Contract rather than guessing.

## Agent Skills and persistent instructions

For personal installation, keep a single canonical copy of this Skill at `~/.agents/skills/token-io-decoupling/`.

Qwen Code natively discovers personal Skills under `~/.qwen/skills/` and project Skills under `.qwen/skills/`. Current Qwen Code also supports additional Skill scan roots through `skills.directories`. Prefer that mechanism for this shared personal source instead of copying the Skill into `~/.qwen/skills/`:

```json
{
  "skills": {
    "directories": ["~/.agents/skills"]
  }
}
```

Qwen Code recursively scans configured additional Skill directories for `SKILL.md`. Its default Skill locations keep higher precedence for same-name Skills, so do not leave a stale duplicate `token-io-decoupling` under `~/.qwen/skills/` when the shared source is intended to be authoritative.

Project-scoped Skills remain native project assets under `.qwen/skills/<skill-name>/SKILL.md`; they are intentionally not redirected to the personal shared directory because their repository/version-control scope is different.

For a deployment that needs the Skill's invariants available at every new run, use Qwen Code's persistent instruction mechanism rather than duplicating the full Skill. `~/.qwen/QWEN.md` provides user-wide instructions, a project-root `QWEN.md` provides shared project instructions, and `.qwen/QWEN.local.md` provides project-local personal instructions. Qwen Code also reads an existing `AGENTS.md`, so a repository already using that portable instruction file does not need a duplicate QWEN-specific copy.

A persistent bootstrap should remain short: point Qwen Code to the installed `token-io-decoupling` Skill and let `SKILL.md` route into the required references. Do not copy the complete Coding Flow into `QWEN.md`.

## Independent subagent mapping

When the active Model Profile requires an independent Primary Output, verifier, auxiliary Worker, or escalation Session, use a regular named/general-purpose Qwen Code subagent rather than a fork unless parent-context inheritance is specifically required.

Regular subagents are suitable for the Coding Runtime boundary because they:

- start with a context separate from the parent conversation;
- can use an explicit model selector such as a concrete model ID, `fast`, or provider-qualified selector;
- can have controlled tool access;
- can run in the foreground when the parent must consume the result immediately or in the background for independent work;
- can remain addressable for related follow-up work when retained state supports continuation.

Fork subagents inherit parent conversation context and therefore do not provide the same Context Firewall semantics. They are useful for bounded parallel investigation but should not be the default sticky Primary Execution Session. Forks also share the parent's working directory and currently do not provide worktree isolation.

## Primary Execution Session continuation

For a background regular subagent that owns related Primary Output work, preserve Session affinity instead of launching a duplicate Worker:

1. use `list_agents` to discover the existing addressable agent and its `task_id`;
2. use `send_message` for related follow-up work;
3. treat a reported `resume_blocked_reason` or otherwise unavailable retained state as a capability failure rather than pretending the old context survived;
4. launch a replacement only when continuation is unavailable or Core rules give a real reason to create a fresh Session.

A completed background agent may continue on its resident runtime or revive from its retained transcript. The Adapter must not claim stronger persistence than Qwen Code actually reports for that agent.

## Model selection

Qwen Code subagents may select:

- `inherit` or an omitted model field to reuse the main Session model;
- `fast` to resolve through the configured `fastModel`;
- a concrete model ID;
- an explicit `authType:model-id` selector when the deployment uses multiple providers.

For a Model Profile with an exact Primary Output binding, prefer a concrete model ID or a `fastModel` configuration whose resolved model can be verified. Do not treat `fast` itself as a model identity: if `fastModel` is absent or invalid, Qwen Code can fall back to inheritance, which may violate the Profile.

Qwen Code also supports model grades, but grades are deployment indirection rather than proof of a concrete model. If a Profile requires an exact binding, confirm the resolved model rather than trusting a semantic grade name.

## Reasoning-effort control

Qwen Code exposes reasoning intensity through its Session/provider configuration, including the `/effort` control and provider `generationConfig.reasoning` settings. For Alibaba Cloud Model Studio / DashScope Qwen3.8 models, the provider ultimately maps the selected effort onto Qwen's supported reasoning parameters.

The important boundary is that subagent `model` configuration and reasoning effort are not the same control. A regular subagent definition can bind a model directly, while task-specific effort may depend on the active Session/provider configuration rather than a dedicated subagent frontmatter field.

Therefore:

- request the Profile-required effort through the strongest Qwen Code control actually available for that Session/provider;
- confirm the effective effort when Qwen Code exposes it;
- do not claim that every independent subagent has an isolated effort knob unless the active configuration really provides one;
- when independent per-Worker effort cannot be guaranteed, keep the exact model binding authoritative and follow the Profile's degraded/unavailable rule for effort-sensitive dispatches rather than inventing a tier.

## Worktree and filesystem mapping

Qwen Code regular subagents support `working_dir` for an existing linked git worktree of the current repository. This maps cleanly onto Coding Context Exchange when the parent has already created per-Worker worktrees:

- bind each Worker to its assigned existing worktree when code changes must be isolated;
- keep its Context Exchange writes inside the parent-assigned context subdirectory;
- use tool/permission restrictions for access control where available;
- do not claim that a git worktree by itself is a permission boundary.

Qwen Code can also provide product-specific isolation modes, but Token I/O Decoupling does not require Agent Team, Arena, Herdr, or other Qwen-specific orchestration systems. The portable Runtime Contract remains the source of topology semantics.

## Runtime/provider configuration

The Alibaba Qwen deployment normally uses Alibaba Cloud Model Studio / DashScope through Qwen Code's model-provider configuration. Keep credentials outside Skill text, repository documents, prompts, and committed provider files.

For the Qwen3.8 series, provider-level reasoning configuration must avoid conflicting simultaneous controls such as `reasoning_effort` and `thinking_budget`. Prefer one effective mechanism and verify what the provider actually applies.

Qwen3.8 models preserve historical reasoning by default in some Alibaba Cloud API modes. Because retained `reasoning_content` is billable input, do not duplicate or manually concatenate hidden reasoning into ordinary content. Let the Host/provider manage the supported conversation format.

## Lifecycle and validation

Qwen Code watches its default personal/project Skill locations in normal interactive sessions and refreshes changes after a short delay. Additional directories configured through `skills.directories` are part of Skill discovery; validate discovery after changing that setting, and restart when the active mode/version does not live-refresh the new scan root. Bare mode may require a restart.

For personal shared-source installation, validate that `~/.agents/skills/token-io-decoupling/SKILL.md` exists, the configured `skills.directories` includes `~/.agents/skills`, and no higher-precedence stale duplicate shadows it under `~/.qwen/skills/`.

Persistent instruction changes should be validated in a fresh or explicitly resumed Session whose loaded context can be inspected.

This Adapter is based on current Qwen Code and Alibaba Cloud public capability documentation. Until an actual Qwen Code CLI smoke test is performed for this repository deployment, the Runtime Registry should label the integration accordingly rather than calling it locally verified.
