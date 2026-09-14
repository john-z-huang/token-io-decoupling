# Codex + OpenAI Coding Deployment

This file is the registered Coding deployment document for Codex with the OpenAI model family. It covers both deployment concerns for this product/provider pair:

- **Host mechanics**: how Codex exposes persistent instructions, independent Agent/Session creation and reuse, explicit runtime-parameter selection, filesystem or sandbox capability, and context transport.
- **Model policy**: which OpenAI runtime is eligible for each Coding role, which execution parameters apply to which task class, escalation, and what to do when a required binding is unavailable.

It does not own Coding role definitions or Session semantics. Role mapping is resolved by [`../../coding/runtime.md`](../../coding/runtime.md) and [`../../coding/session-model.md`](../../coding/session-model.md).

## Host identity

Use this deployment only when the running Code Agent environment is actually Codex. Do not infer Host identity from repository contents, Skill location, a prompt that mentions Codex, or the presence of an `AGENTS.md` file alone.

When the running environment exposes the current model or Session configuration, use those facts for Runtime resolution. If required identity or capability information is unavailable, report that fact to the Coding Runtime Contract instead of guessing.

## Persistent instruction loading

For a Codex deployment that needs the Skill's invariants at every new run, use Codex's persistent instruction mechanism. A global `~/.codex/AGENTS.md` may provide the short bootstrap; when `~/.codex/AGENTS.override.md` is present at the same level, the active override takes precedence. Repository/project instructions remain responsible for repository-specific policy and must not duplicate the full Skill.

A normal Skill description affects discovery but does not guarantee that every new run has loaded the complete Skill. The bootstrap should therefore point to the installed `token-io-decoupling` Skill and let `SKILL.md` route into the required references rather than copying normative Flow text into the persistent instruction file. Keep the bootstrap host-independent; the shared bootstrap text is maintained in [`../../../BEST_PRACTICES.md`](../../../BEST_PRACTICES.md).

## Role bindings and dual-role eligibility

At Coding Flow startup, confirm the current Session's model identity through the facts the running environment exposes before applying these bindings:

- **Input-side Reasoning**: the current advanced parent model/session owns high-value semantic decisions.
- **Primary Output**: the required OpenAI execution model is `gpt-5.6-luna`.
- **Change Verification**: when selected, start one fresh independent `gpt-5.6-luna` Session for the task conversation's final change-result verification, then reuse that verifier for later verification slices. Each new final-state fingerprint/epoch must be independently re-evaluated; an earlier verdict is not evidence. Create additional verifier Sessions only for genuinely isolated requirements, such as incompatible environments/snapshots, distinct permission or security domains, or an explicit independent audit.
- **Documentation/Comments & Git Operations**: when selected, use a separate `gpt-5.6-luna` Session for approved post-verification documentation/code-comment materialization and all non-trivial repository Git operations. It owns synchronization, branch/worktree operations, staging, commits, history integration, reset/clean/stash, conflict handling, tags, remotes, pushes, and applicable Issue/PR delivery; only tiny read-only Git metadata queries remain outside this role.
- **Context Bootstrap/Refresh**: when selected, use a dedicated or reusable `gpt-5.6-luna` Worker with `reasoning_effort=high` by default for bounded factual and policy-routing capsule materialization. `reasoning_effort=medium` is permitted only for deterministic metadata/source-hash or delta-refresh work when the host explicitly supports it; semantic interpretation remains with Input-side Reasoning.
- **Dual-role eligibility**: when the current Session can explicitly confirm that it is `gpt-5.6-luna` and the host can satisfy the task's required reasoning-effort tier in that Session, this deployment declares the current Session eligible for both Input-side Reasoning and Primary Output. The generic runtime mapping therefore enters **Single-Session Coding Mode** unless a concrete structural reason requires another Session.
- **Normal two-Session mapping**: when the current Agent cannot explicitly confirm that it is `gpt-5.6-luna`, keep the current Agent constrained to the input-side reasoning responsibility and use an independent `gpt-5.6-luna` Session for Primary Output.

Single-Session Coding Mode preserves this deployment's implementation behavior: the current Luna directly performs source/project exploration, implementation, debugging, provisional focused checks, and implementation output rather than delegating ordinary work to another Luna merely to preserve a two-role topology. It does not absorb non-trivial Git operations, and it does not remove the verification or delivery roles: for a material functional change the Input-side Agent still starts one fresh independent Change Verification Luna, reuses it for later verification epochs in the same task conversation, and may create a separate Documentation/Comments & Git Operations Luna when documentation or Git work is needed. Because the current Session also owns high-value reasoning, its ordinary substantive implementation uses `reasoning_effort=xhigh`.

A Session in Single-Session Coding Mode may create another Agent only for the initial selected independent verification, post-verification documentation/comment or non-trivial Git-operation isolation, real parallelism, clearly degraded/overgrown current context, explicit isolation benefit, or targeted `max` escalation for a specific repeatedly blocked task. Reuse the selected verifier across later verification epochs; additional verifier Sessions require genuinely isolated requirements. Project exploration, implementation, testing, long output, or generic task complexity are not exceptions.

## Independent Agent and Session operations

When this deployment requires an independent Primary Output, verifier, auxiliary Worker, or targeted escalation Session, use the independent Agent/Session mechanism exposed by the current Codex environment:

- explicitly request the bound model and host-supported runtime parameters when Codex exposes controls for them;
- in each newly created Agent's instruction body, state the concrete assigned model name/identifier and `reasoning_effort` in readable text, even when also setting them through host controls; the Agent must not be expected to infer this assignment from tool arguments or its runtime identity. When reusing an Agent with the same assignment already stated, do not repeat it mechanically; state it when the assignment changes or the prior instruction was missing or unclear;
- do not rely on an unspecified host default when this deployment binds an exact model or reasoning-effort tier;
- reuse the established Primary Execution Session for related work unless the Core rules provide a concrete reason to rebuild or split it;
- do not create a second Session merely because the logical role name changes inside a compatible same-Session execution.

If the current Codex environment cannot create the required independent Session, cannot select the bound model, or cannot satisfy a required runtime parameter, return that capability failure to the unavailable-handling rules below instead of substituting another model.

## Reasoning-effort selection

- In normal two-Session Coding, the independent Primary Output Luna defaults to `reasoning_effort=xhigh`. Use `xhigh` for general feature implementation, non-trivial refactoring or debugging, implementation-feedback test code, and other work where substantial **execution judgment within an approved semantic plan** is expected. This effort tier does not transfer ownership of problem formulation, architecture choice, unresolved semantic trade-offs, or acceptance to the Primary Output role. Output length or project size alone does not justify increasing effort.
- A selected Change Verification Luna defaults to `reasoning_effort=xhigh` because it must independently choose and interpret holistic checks across the final changed state. It owns verification evidence only; it does not own repair, architecture decisions, or semantic acceptance.
- A selected Documentation/Comments & Git Operations Luna defaults to `reasoning_effort=high` for both bounded developer documentation/code-comment materialization and non-trivial repository Git work. Its documentation write scope excludes functionality and tests; its Git scope is limited to the explicitly released repository/worktree/ref/remote operations. It must not be used to compensate for failed verification or to make unapproved product decisions.
- Other auxiliary materialization Workers should default to `high` unless their concrete task meets the `xhigh` criteria.
- Use `reasoning_effort=medium` or a lower host-supported tier only when the host explicitly exposes that tier and the task is strictly bounded, low semantic risk, and easy to verify mechanically. Suitable examples include running already-selected tests/formatters/linters and compressing results, collecting file/path metadata, exact search or extraction, literal replacements, template-driven formatting, or generated-table updates. Tiers below `medium` should normally be read-only or deterministic transformations. Do not assign Semantic Contract ownership, architecture/product decisions, cross-module implementation, complex debugging, complex test design, or public API/schema/permission changes to these lightweight Workers.

## Targeted max escalation

`reasoning_effort=max` is an exception escalation, not a default Worker setting.

Use it only for a specific task that an existing `high`/`xhigh` Worker has repeatedly failed, oscillated on, or become clearly blocked by. The parent creates a new, narrowly scoped max Worker; when possible, the predecessor first writes reusable context/handoff documents in the primary worktree as defined by [`../../coding/context-exchange.md`](../../coding/context-exchange.md), and the max Worker reads those documents instead of restarting project exploration from zero.

After the blocker is resolved, follow-on work returns to the normal `xhigh`/`high` tiers rather than keeping max for unrelated tasks.

## Runtime parameter ownership

Codex may expose model selection and `reasoning_effort` controls for dispatched work. The host owns which controls exist; the role bindings and effort policy above own which values this deployment binds. Do not treat an unspecified host default as this deployment's policy.

A host UI or tool may already display equivalent dispatch information. Shared `Dispatch Preview` rules determine whether an additional visible preview is necessary; this deployment does not create a second, product-specific reporting protocol.

## Unavailable handling

- Do not silently replace a Coding role that this deployment binds to Luna with another model.
- If an independent Luna role is required but `gpt-5.6-luna` identity cannot be confirmed, the model cannot be selected explicitly, or the host cannot satisfy the reasoning-effort tier required for that dispatch, stop the corresponding substantive Coding or verification work and briefly report the block. Do not let Primary Output self-verify a material change because the verifier binding is unavailable.
- Purely read-only, strictly bounded diagnosis may continue when Luna identity is confirmed but the host cannot set reasoning effort. Do not use that exception to move complex project-state work back to the advanced parent model or to silently assign lightweight effort to a task whose binding requires `high` or `xhigh`.
- Do not infer that an advanced parent model should absorb Primary Output merely because it is technically capable of implementation. The bindings above are intentional deployment policy for Token I/O separation.

## Filesystem and worktree mapping

When multiple Agents work on the same development request, reuse the task's primary Git worktree by default. A separate Agent/Session, a fresh verifier, or a Worker-specific Context Exchange directory does not itself require another worktree. Follow the validation and explicit-isolation exceptions in [`../../coding/context-exchange.md`](../../coding/context-exchange.md); for concurrent write conflicts, assign non-overlapping path scopes or sequence dependent slices first.

When multi-Agent Coding uses file-backed Context Exchange, apply its capability requirements through the strongest isolation available in the current Codex environment:

- when path scoping is available, give each Worker RW access only to its named mutation paths and its own context subdirectory; give the verifier RO access to the fixed final state, with RW access limited to verification-script/test paths explicitly authorized in its released slice;
- create a separate validation worktree only for a concrete isolation need, such as incompatible snapshots/environments, validation writes that cannot be redirected or contained, a separately scoped filesystem view required by a distinct permission/security boundary, or an explicitly isolated audit;
- expose cross-Worker context as targeted RO paths when possible;
- keep other Worker context and the parent-owned root index unexposed or denied when the host supports that boundary;
- use tool-level mechanical copies before falling back to parent-generated context transport when safe RO sharing is unavailable.

`git worktree` provides a physical working-copy boundary but is not itself a permission mechanism. Do not claim stronger isolation than the active sandbox actually provides.

## Run lifecycle

Codex builds its applicable instruction chain when a run or TUI Session starts. After changing global persistent instructions, an active override, the Skill, or repository instruction files, use a new run/Session to validate adoption rather than assuming an existing Session has incorporated the change.

For the shared setup and smoke-check procedure, see [`../../../BEST_PRACTICES.md`](../../../BEST_PRACTICES.md).
