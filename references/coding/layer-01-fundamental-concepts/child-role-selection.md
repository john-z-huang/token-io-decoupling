# Coding Child Role Selection

[English](child-role-selection.md) | [简体中文](child-role-selection_zh_cn.md)

This module owns selecting one maintained child role for a proposed new child and the role-choice Decisions policy. It consumes responsibilities from [Session Role Ownership](session-role-ownership.md), current identity and allocations from [Session Model](session-model.md) and [Delegation State Record](delegation-state-record.md), and capacity from [Delegation Count Gate](delegation-mode-count-gate.md). It does not allocate budget, create children, or authorize an effect.

## General rules

### Role request boundary

Use only the four maintained roles: `Primary Output`, `Change Verification`, `Context Bootstrap/Refresh`, and `Documentation/Comments & Git Operations`. Match the released task to one role's responsibility. Read current-session identity and allocations from the canonical state record; a role already reserved or created in the current Session is unavailable for another child. The allocation owner requires role uniqueness, and a created role remains occupied after completion, failure, interruption, cancellation, or unavailability. Do not count inherited agents from another Session. A Fork must complete the fresh mode/count re-entry gate before role selection.

For this owner, the proposed task is released once Root has authorized and bounded its objective and scope after Context and Decision. This is distinct from binding and releasing that child's later Interaction Slice. Select and reserve a role for that authorized proposed task before releasing its Interaction Slice; do not wait for the child-specific slice release, which requires the assigned role.

An explicit user instruction to create a child skips role-selection Decisions. Use the explicit user role when supplied; when the user clearly requires creation but leaves the role open, `Primary Output` is the fallback only if creation is otherwise established and that role remains available. This does not bypass Single-Agent mode, the current-session role guard, the approved budget, user permissions, a released slice, or child-creation capability.

If no explicit role instruction applies, first generate and review a bounded decision context from provenance-labeled facts using the current [Decision Context Generation](decision-context-generation.md) procedure. Then use an authorized role-advice capability with that reviewed context and the current-state facts. Decision-question generation is optional. The role selector may use only choices that remain available under verified current-session facts.

If context generation fails or returns insufficient evidence, do not fabricate a description or hash and do not send the downstream role-advice request with unusable context. Root may still make the role decision directly from this Skill and verified current facts when those facts suffice; otherwise keep the decision unresolved and do not create a child. Do not automatically call the downstream advice operation after a generation failure. A generation failure alone does not establish that creation should proceed.

### Role Decisions instructions

Choose exactly one offered role for the requested child, or `insufficient_evidence`. Use only the released task objective, deliverables, dependencies, verification needs, supplied current-session state, and the loaded role owners. Match the role to the work the child will actually perform. Do not infer repository facts, permissions, capacity, or user intent that were not supplied. If facts conflict, the task crosses roles without a released boundary, the required owner policy is unavailable, or no offered role fits, choose `insufficient_evidence`. The choice is advice for Root review; it does not reserve a slot or create a child.

### Role choice descriptions

#### Primary Output

Use for the main authorized code/configuration implementation or authorship/editing of this Skill's instructions and references. The child's released slice remains bounded. Ordinary non-Skill documentation and comments stay with Root, even when the task also includes code changes.

#### Change Verification

Use for a read-only review that independently checks a released change against its contract and evidence. The verifier must have a genuinely separate current-session identity and must not implement, repair, stage, or commit the reviewed change. If no eligible independent verifier is available, report that limitation; do not relabel another role to claim independence.

#### Context Bootstrap/Refresh

Use for a bounded retrieval or refresh of project context that Root needs for a later decision or released slice. Return cited source paths or stable references and distinguish observed facts from missing context. Do not authorize implementation or make Root's semantic decision.

#### Documentation/Comments & Git Operations

Use only for explicitly released non-trivial Git work that is within the child's assigned responsibility and permissions. Root owns ordinary documentation and comments; Primary Output may author or edit this Skill's instructions and reference documents after the required release gates. This role does not authorize Git effects and cannot expand the approved path or operation scope.

#### insufficient_evidence

Choose when the supplied facts do not establish a permitted role, role duties conflict with the released slice, current-session role state is uncertain, or a required policy or capability is unavailable. Root may review the maintained policy and current evidence; the API result itself never authorizes creation.

### Review and fallback

Before reservation, Root verifies the current mode and Session identity, role uniqueness, available approved capacity, user direction, authorized proposed task, permissions, and host capability. The later Interaction Slice is released only after its assigned role is reserved. A context-generation failure, Decisions failure, or insufficient result does not select a role or prevent independent Root review. If Root independently establishes that creation should proceed from verified facts, Root may use `Primary Output` as the default only when the proposed work matches that role and it is not already reserved or created; all other gates still apply. If all four maintained roles are occupied, Root must block another child and must not request a budget increase: added capacity cannot make a role available or permit a duplicate. A budget request is available only when at least one different role remains unoccupied and capacity alone is insufficient. Never select the same role again, silently exceed the budget, or replace a created child. See [Delegation Count Gate](delegation-mode-count-gate.md), [Delegation Mode Re-entry](delegation-mode-reentry.md), [Delegation State Record](delegation-state-record.md), and [Child Role Allocation](delegation-child-role-allocation.md) for the authoritative gates and fields.

## Codex CLI / ChatGPT Desktop optimizations

When exposed and outbound use is authorized, call `workflow_select_child_role` only after reviewing the generated decision context and current-session role facts. Pass the reviewed context and its input hash with the current role state. Compare the returned `fact_fingerprint`, `context_input_hash`, `source_policy_hashes`, and `input_hash` with the current evidence before using the suggestion. The tool is stateless and advisory; complete the guarded Root reservation and creation path separately.

## Claude Code CLI / Claude Desktop optimizations

There are currently no concept-specific optimizations for this concept; follow the General rules.

## Related concepts

- [Session Role Ownership](session-role-ownership.md) — owns the maintained role responsibilities.
- [Session Model](session-model.md) — owns Session identity and affinity.
- [Delegation Count Gate](delegation-mode-count-gate.md) — owns the locked budget and approved expansion.
- [Delegation Mode Re-entry](delegation-mode-reentry.md) — owns fresh gates for a Fork.
- [Delegation State Record](delegation-state-record.md) — owns current-session allocation state.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — owns reservation of a selected role in an approved slot.
- [Coding Child Creation](delegation-child-creation.md) — owns the capability and prerequisites for creating a child.
- [Decision Context Generation](decision-context-generation.md) — owns generation and review of bounded decision context.
