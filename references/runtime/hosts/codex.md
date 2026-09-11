# Codex Host Adapter

This file describes the host-specific mechanics used by the current verified Codex deployment. It does not own Coding role definitions or concrete model policy. Role mapping is resolved by [`../../coding/runtime.md`](../../coding/runtime.md), while concrete OpenAI model bindings are defined by the selected Model Profile.

## Host identity

Use this adapter only when the running Code Agent environment is actually Codex. Do not infer Host identity from repository contents, Skill location, a prompt that mentions Codex, or the presence of an `AGENTS.md` file alone.

When the running environment exposes the current model or Session configuration, use those facts for Runtime resolution. If required identity or capability information is unavailable, report that fact to the Coding Runtime Contract instead of guessing.

## Persistent instruction loading

For a Codex deployment that needs the Skill's invariants at every new run, use Codex's persistent instruction mechanism. A global `~/.codex/AGENTS.md` may provide the short bootstrap; when `~/.codex/AGENTS.override.md` is present at the same level, the active override takes precedence. Repository/project instructions remain responsible for repository-specific policy and must not duplicate the full Skill.

A normal Skill description affects discovery but does not guarantee that every new run has loaded the complete Skill. The bootstrap should therefore point to the installed `token-io-decoupling` Skill and let `SKILL.md` route into the required references rather than copying normative Flow text into the persistent instruction file.

## Independent Agent and Session operations

When the active Model Profile requires an independent Primary Output, verifier, auxiliary Worker, or targeted escalation Session:

- use the independent Agent/Session mechanism exposed by the current Codex environment;
- explicitly request the Profile-required model and host-supported runtime parameters when Codex exposes controls for them;
- do not rely on an unspecified host default when the Profile requires an exact model or reasoning-effort tier;
- reuse the established Primary Execution Session for related work unless the Core rules provide a concrete reason to rebuild or split it;
- reuse the established verifier Session for subsequent verification slices in the same task conversation, passing the new final-state fingerprint/epoch and requiring independent re-evaluation; create another verifier only when the parent identifies a genuinely isolated verification requirement;
- do not create a second Session merely because the logical role name changes inside a compatible same-Session execution.

If the current Codex environment cannot create the required independent Session, cannot select the required model, or cannot satisfy a required runtime parameter, return that capability failure to the active Model Profile's unavailable-handling rule. The Adapter must not substitute another model on its own.

## Runtime parameters

Codex may expose model selection and `reasoning_effort` controls for dispatched work. This Adapter owns only the mechanism for requesting those controls. Exact model names and the `medium`/`high`/`xhigh`/`max` policy belong to the active Model Profile and must not be duplicated here.

A host UI or tool may already display equivalent dispatch information. Shared `Dispatch Preview` rules determine whether an additional visible preview is necessary; the Adapter does not create a second, product-specific reporting protocol.

## Filesystem and worktree mapping

When multi-Agent Coding uses file-backed Context Exchange, apply the capability requirements from [`../../coding/context-exchange.md`](../../coding/context-exchange.md) through the strongest isolation available in the current Codex environment:

- give each Worker RW access only to its own code worktree and context subdirectory when such path scoping is available;
- expose cross-Worker context as targeted RO paths when possible;
- keep other Worker context and the parent-owned root index unexposed or denied when the host supports that boundary;
- use tool-level mechanical copies before falling back to parent-generated context transport when safe RO sharing is unavailable.

`git worktree` provides a physical working-copy boundary but is not itself a permission mechanism. The Adapter must not claim stronger isolation than the active sandbox actually provides.

## Run lifecycle

Codex builds its applicable instruction chain when a run or TUI Session starts. After changing global persistent instructions, an active override, the Skill, or repository instruction files, use a new run/Session to validate adoption rather than assuming an existing Session has incorporated the change.

For the current deployment's setup procedure and smoke checks, see [`../../../BEST_PRACTICES.md`](../../../BEST_PRACTICES.md).
