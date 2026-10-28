# Coding Task Assignment

[English](task-assignment.md) | [简体中文](task-assignment_zh_cn.md)

This module owns deciding whether Root or a child should execute a released task and selecting among eligible existing current-session children. It does not select a role for a new child, create or dispatch a child, or change output-token routing.

## General rules

### Assignment boundary

For this owner, a released task means Root has authorized and bounded its objective and scope after Context and Decision. It does not require release of the child-specific Interaction Slice. Executor selection cannot release that later Slice: before implementation or dispatch, Root must still pass the applicable Slice gate and provide the concrete authorized boundary.

Honor an explicit user executor or agent instruction and skip the corresponding advice request. Still check mode, scope, permissions, availability, and current-session identity. An explicit `sub_agent` instruction conflicts with locked Single-Agent mode and must be returned for Root review; do not silently replace it with `root`. An explicit `root` instruction in Single-Agent mode remains valid. Without an explicit executor, Single-Agent mode has no child executor and the local deterministic route may use Root subject to other gates. A Fork is a new Session and must complete fresh mode/count re-entry under [Delegation Mode Re-entry](delegation-mode-reentry.md); inherited agents are not current-session candidates under the [Session Model](session-model.md) and [Delegation State Record](delegation-state-record.md).

When the executor is not explicit, Root reviews current task facts and a decision context before considering an advisory executor suggestion. If decision-context generation fails or lacks a fact directly needed by the judgment, do not fabricate a description or hash and do not send the downstream advice request with unusable context. Root may still decide directly from this Skill and verified current facts when they suffice; otherwise keep the decision unresolved for review. A `sub_agent` suggestion with a positive unused approved slot and no existing suitable child may proceed through [Child Role Selection](child-role-selection.md) without asking for more budget. Select and reserve its role for the Root-authorized proposed task after Context and Decision and before releasing the child-specific Interaction Slice; the Slice gate must still verify the concrete objective/scope against that role. Executor advice alone does not select a role. When no slot is available but a different role remains unoccupied, Root must use the explicit user-approval route in [Delegation Count Gate](delegation-mode-count-gate.md) before reserving that role. If all four roles are occupied, added capacity cannot make another role legal; block creation instead of requesting expansion. An advice failure or insufficient result requires Root review under this owner and never defaults to Root.

### Executor Decisions instructions

Choose `root`, `sub_agent`, or `insufficient_evidence` for the released task. Compare semantic responsibility, task context, required capability, and verified permission facts. Use only the current reviewed task and supplied current-session state. Do not invent a current child, permission, capability, budget, or user instruction. If the task is not released, facts conflict, required capability or permission is unknown, or neither executor can be established as safe, choose `insufficient_evidence`. A `sub_agent` choice with unused approved capacity may continue through role selection and child creation; this tool grants no authority. Never choose `root` only because the Decisions API failed.

### Executor choice descriptions

#### root

Use when Root is the appropriate executor under the released scope, current permissions, context access, and output-token route. Root retains semantic decisions, contract interpretation, orchestration, and final acceptance.

#### sub_agent

Use when a child should perform a concrete released implementation or other eligible slice and the current-session role, capability, permission, and budget gates can be satisfied. If an existing suitable child is available, continue to child selection. If none exists but an approved unused slot remains, continue through role selection and creation. Otherwise request user approval for one different role or return for Root review.

#### insufficient_evidence

Use when the task or current evidence does not establish a safe executor, the required capability or permission is missing or unknown, facts are stale or conflicting, or the request is out of scope. Root must review; do not treat absence of a successful API answer as a Root decision.

### Child-selection Decisions instructions

Choose one eligible child by its opaque `candidate_ref`, or `insufficient_evidence`. Eligibility requires a verified current-session identity, a matching responsibility, required capability, and permission to perform this task. Exclude foreign-session inherited agents and unavailable candidates. A single eligible candidate is used directly without Decisions. With multiple eligible candidates, consider suitable idle candidates before busy candidates; if none are idle, wait until one is. If exactly one idle candidate remains after filtering (because the other eligible candidates are busy), that single idle candidate can be selected directly. This exception does not apply when multiple idle candidates remain. When at least two idle candidates remain, invoke the concrete child-selection Decisions request even if `Primary Output` is preferred. If a suitable idle Primary exists, offer only that candidate and `insufficient_evidence`; otherwise offer all eligible idle candidates and `insufficient_evidence`. If no suitable Primary exists, compare how directly each candidate's supplied context supports the requested task and prefer the candidate with more relevant current context. Do not use raw transcript size, unrelated context volume, or a numeric confidence cutoff. If context relevance is tied or cannot be established, choose `insufficient_evidence` for Root review.

An advice failure may fall back to a suitable current-session `Primary Output` child only when the source policy and current facts remain current. The fallback remains subject to permission and availability: use it only when idle; if busy, wait until idle. A stale policy, stale facts, or identity conflict requires refresh and Root review, never fallback. If no suitable Primary exists, return unresolved review and do not invent a Root fallback. A single eligible candidate is used directly without a Decisions request. Multiple busy candidates require waiting until a suitable child is idle.

### Child-candidate choice descriptions

#### insufficient_evidence

Use when candidates are not distinguishable from the supplied responsibility, capability, permission, availability, and task-relevant context facts, or when the facts do not establish a unique safe selection. Root reviews the current evidence and the explicit task-context preference branch; there is no arbitrary confidence threshold.

### Review and action boundary

Root checks the current fact revision/fingerprint, current-session relationship, candidate identity, permission, capability, release scope, and latest availability before using a result. A tool result is advisory and never dispatches work. Root retains final semantic decisions and acceptance regardless of executor.

## Codex CLI / ChatGPT Desktop optimizations

For an exposed Codex workflow, call `workflow_select_executor` only when no explicit user executor instruction applies. For `workflow_select_child`, an explicit user candidate skips the advice request after eligibility is checked; one eligible candidate total and exactly one idle candidate after filtering can be selected directly. When two or more eligible idle candidates remain, call the tool even if an idle Primary is preferred. Pass bounded task-relevant context, matching role, capability, permission, and availability facts; offer only the idle Primary plus `insufficient_evidence` when a suitable idle Primary exists, otherwise offer all suitable idle candidates plus `insufficient_evidence`. Compare result hashes to current facts, then verify the selected child through the active parent-controlled identity and permission boundary before dispatch. The tool omits non-offered candidates from the Decisions request, does not read host history, and cannot prove caller-provided identity facts.

## Claude Code CLI / Claude Desktop optimizations

There are currently no concept-specific optimizations for this concept; follow the General rules.

## Related concepts

- [Child Role Selection](child-role-selection.md) — owns role selection and its fallback.
- [Session Role Ownership](session-role-ownership.md) — owns maintained role responsibilities.
- [Session Model](session-model.md) — owns Session identity and affinity.
- [Delegation State Record](delegation-state-record.md) — owns current allocation identities and status.
- [Delegation Count Gate](delegation-mode-count-gate.md) — owns locked capacity and explicit budget expansion.
- [Delegation Mode Re-entry](delegation-mode-reentry.md) — owns the fresh mode/count gate for a Fork.
- [Output Token Routing](output-token-routing.md) — owns the independent large-output gate.
- [Decision Context Generation](decision-context-generation.md) — owns generation and review of bounded decision context.
