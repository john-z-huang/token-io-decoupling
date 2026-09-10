# Coding Runtime Contract

This module is the Coding Flow boundary between runtime-neutral orchestration and concrete Code Agent products, model families, and execution parameters. Coding architecture defines responsibilities and context ownership; this module defines how a selected runtime maps those responsibilities onto actual Sessions without embedding vendor or model names in the Core.

Role and Session semantics come from [`session-model.md`](session-model.md). Shared dispatch, Contract, reporting, and evidence rules come from [`../shared-protocols.md`](../shared-protocols.md).

## Runtime composition

An active Coding runtime is composed of two independent deployment concerns:

- **Host Adapter**: describes how the current Code Agent product exposes persistent instructions, independent Agent/Session creation and reuse, explicit runtime-parameter selection, filesystem or sandbox capabilities, and context transport.
- **Model Profile**: declares which concrete model/runtime configurations are eligible for each Coding role, which execution parameters apply to different task classes, targeted escalation policy, and what to do when a required binding is unavailable.

The Host Adapter answers **how the product instantiates work**. The Model Profile answers **which runtime should perform a responsibility**. A Flow rule must not infer one from the other.

The registered deployment files are selected through [`../runtime/index.md`](../runtime/index.md). Load only the Host Adapter and Model Profile that match the current environment; do not preload every registered runtime document.

## Runtime identity and capability resolution

Before substantive Coding execution that depends on Session topology or explicit model/runtime parameters:

1. identify the current Host through facts exposed by the running environment rather than repository names, prompt wording, or guesswork;
2. select the matching registered Host Adapter;
3. select a Model Profile compatible with that Host and the intended deployment;
4. obtain the current Session's model/runtime identity and relevant parameter capabilities through the Host when available;
5. apply the selected Profile's role eligibility and unavailable-handling rules.

Do not silently claim that the current Session satisfies a role merely because its model is generally capable of coding. Role eligibility is deployment policy: a model may be technically capable of a responsibility while the active Profile intentionally keeps that responsibility in a different Session to preserve Token I/O boundaries.

If no registered Host Adapter/Profile pair matches the current environment, do not invent product-specific operations or silently reuse a different vendor's bindings. The runtime-specific part of Coding execution is blocked until a compatible deployment is provided. The runtime-neutral Semantic Contract and planning concepts may still be used for analysis, but that does not constitute physical Token I/O isolation or a supported runtime mapping.

## Session mapping algorithm

After the active runtime is resolved, map the logical responsibilities defined in `session-model.md` as follows:

1. **Confirm input-side eligibility**: the current parent Session must satisfy the active Profile's requirements for the Input-side Reasoning responsibility. If it does not, follow the Profile's unavailable rule rather than silently reclassifying the Session.
2. **Prefer compatible same-Session execution**: if the active Profile explicitly declares the current Session eligible for both Input-side Reasoning and Primary Output, the Host can satisfy the task's required runtime parameters in that Session, and no independent structural benefit exists, use **Single-Session Coding Mode**.
3. **Use normal two-Session execution when required**: if the current Session is eligible for input-side reasoning but not for Primary Output under the active Profile, use the Host Adapter to create or reuse an independent Session that satisfies the Profile's Primary Output binding and parameters.
4. **Split despite dual eligibility only for a concrete reason**: fresh verification, real parallelism, context-capacity recovery, explicit isolation, or a Profile-defined targeted escalation may justify another Session even when the current Session is otherwise dual-role eligible.
5. **Block rather than silently substitute**: if the required independent Session, model binding, or runtime parameters cannot be satisfied, follow the active Profile's blocked/degraded-read-only rules. Do not silently move high-volume execution back into a Session that the Profile does not authorize for that role.

Repository size, long output, build/test work, or generic task complexity do not by themselves change this mapping.

## On-demand verification, documentation, and Git-operations mapping

The Input-side Reasoning Agent decides whether the change's materiality, risk, or explicit user requirement gives independent final verification concrete value. When it selects **Change Verification**, the Host must create a fresh independent Session eligible for that role under the active Profile after Primary Output reaches its implementation checkpoint. The verifier receives the final state and approved verification inputs; it must not inherit the Primary Output implementation history or silently become a repair Worker.

When documentation or code-comment work is needed after verification, or when any non-trivial repository Git work is needed, the Input-side Agent may select **Documentation/Comments & Git Operations** and create a separate Session with the Profile's auxiliary materialization binding and effort tier. Documentation slices are released only after the verifier has passed (or the Input-side Agent has explicitly classified the task as behavior-preserving and skipped independent verification), with write capability restricted to the approved documentation/comment scope. Git slices may be released at the stage where synchronization, branch/worktree preparation, history integration, conflict handling, or other repository Git work is needed, with an exact Git scope and capability boundary.

There is no separate delivery role or delivery Worker: commit, push, remote, and Issue/PR delivery are Git-operation slices of Documentation/Comments & Git Operations. That Agent may inspect or mutate Git metadata and remote state only when the parent has explicit user/task authorization and the Host can enforce the required boundary. Conflict-resolution edits are permitted only for an explicitly authorized operation using already approved content; a new semantic or product decision returns to the parent and Primary Output. If the active Runtime cannot provide the required separation or supported Worker, follow its unavailable rule and block; do not silently self-authorize, widen documentation scope, or substitute an arbitrary model.

In Single-Session Coding Mode, dual eligibility covers Input-side Reasoning and Primary Output implementation only. It does not authorize the current Session to self-verify a material final change once the fresh verifier is selected, nor does it make the current Session the Documentation/Comments & Git Operations Agent or authorize non-trivial Git work. If a selected independent binding or required parameter cannot be created, follow the active Profile's unavailable rule rather than silently falling back to Primary Output self-verification, input-side long-form materialization, or input-side Git operations.

## Runtime parameter ownership

Core Coding documents intentionally do not define vendor-specific parameter names or concrete model tiers. A Model Profile may classify tasks and bind them to host-supported parameters, while the Host Adapter describes how those parameters are requested on that product.

When the Host cannot expose a parameter required by the active Profile, the Profile's unavailable rule is authoritative. Do not reinterpret a missing control as permission to use an arbitrary default.

## Targeted escalation

A Model Profile may define a narrowly scoped escalation runtime for a specific task that has repeatedly failed, oscillated, or become clearly blocked. This is an exception to ordinary Session mapping, not a reason to upgrade every Worker or split Sessions by default.

When escalation replaces an existing independent Worker, preserve reusable state through [`context-exchange.md`](context-exchange.md) when possible. After the blocker is resolved, return to the Profile's normal role bindings and task parameters.

## Portability boundary

A new Code Agent product should normally be integrated by adding a Host Adapter and a compatible Model Profile entry without changing:

- Input-side Reasoning, Primary Output, Change Verification, and Documentation/Comments & Git Operations role definitions;
- Context Firewall semantics;
- Semantic Contract and Decision Checkpoints;
- Primary Execution Session affinity and on-demand Worker lifecycle;
- Context Exchange ownership;
- implementation feedback, independent change verification, and semantic acceptance boundaries;
- documentation/comment-only materialization and non-trivial Git-operation boundaries.

Change Core rules only when a new environment reveals a genuine architecture requirement that cannot be expressed through the runtime contract. Do not add `if <product>` or `if <model>` branches to Core documents as a shortcut for deployment policy.
