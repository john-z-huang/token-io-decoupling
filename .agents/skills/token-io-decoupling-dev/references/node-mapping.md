# Rule-context node and branch mapping

[English](node-mapping.md) | [简体中文](node-mapping_zh_cn.md)

This development reference maps the stable `rules_get_context` nodes and original `legacy_branch` values to existing Skill policy. The linked owners remain authoritative; this mapping creates no policy, state, permissions or child release. A lookup only returns material and never executes a branch. Split mixed output into bounded slices and classify each separately.

Each branch records a trigger, the applicable action, its pass evidence and its distinct failure boundary. Conditional policy is carried as material; it acts only when its own trigger and authority apply.

## Node: contract

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/contract.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### ready

- Trigger: The requested outcome, scope, constraints, decisions and acceptance are known.
- Action: Record those facts and distinguish observations from assumptions.
- Pass: The four Contract dimensions and material decisions are explicit.
- Failure: If a required input is absent or conflicting, pause the dependent slice and identify it.

### amend

- Trigger: A verified fact or user instruction materially changes the current Contract.
- Action: Record and analyze the change and update the Contract, plan and dependent decision within existing authority.
- Pass: The revised outcome, scope, constraints and acceptance are explicit before affected work resumes.
- Failure: If the change or its authority cannot be established, keep affected work unreleased.

### blocked

- Trigger: A material Contract input, decision or necessary authorization is missing or conflicts.
- Action: Report the precise missing or conflicting item and pause the dependent slice.
- Pass: The blocker and its effect on release are explicit.
- Failure: Do not assume an answer or expand authority to resume work.

## Node: mode

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/mode.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### single-agent

- Trigger: The parent record confirms Single-Agent with a locked count of zero.
- Action: Check the recorded mode, count, empty allocations and required entry capabilities.
- Pass: The valid zero-child mode is recorded without releasing a slice.
- Failure: Missing or inconsistent mode, count or capability evidence blocks dependent work.

### multi-agent

- Trigger: The parent record confirms Multi-Agent and its locked positive child count.
- Action: Check the count and exactly that many initially unbound reserved slots and required capabilities.
- Pass: The locked mode and allocation shape are valid without releasing a child or slice.
- Failure: A missing, extra or inconsistent slot or required capability blocks dependent work.

### blocked

- Trigger: The selected mode, locked count, allocation shape or entry capability cannot be confirmed.
- Action: Preserve the current record and report the exact gate evidence that is missing or conflicting.
- Pass: The dependent route remains paused with its blocker recorded.
- Failure: Do not infer a new mode, initialize a store or create a child to bypass the gate.

## Node: context

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/context.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### sufficient

- Trigger: Current authoritative context answers the bounded question for the next slice.
- Action: Check source, scope, owner, freshness and relevant epoch before relying on it.
- Pass: The minimum necessary facts are current and usable for the pending decision.
- Failure: Stale, incomplete or conflicting material must be refreshed before dependent use.

### request evidence

- Trigger: A necessary factual gap can be named and requested through an authorized route.
- Action: Identify and request the smallest missing evidence while dependent release remains paused.
- Pass: The request and affected decision are explicit and the checkpoint will be revisited.
- Failure: If no authorized acquisition route exists, classify the dependent work as blocked.

### blocked

- Trigger: Necessary context cannot be obtained or an essential decision or authorization conflict is unresolved.
- Action: Report the exact unavailable evidence or conflict and pause dependent work.
- Pass: The blocker and its effect on the next slice are explicit.
- Failure: Do not treat unverified context or unavailable optional advice as authorization.

## Node: decision

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/decision-and-execution/decision.md#actions).
When the authorized route supplies workflow-routing advice, consult [workflow routing advice](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/workflow-routing-advice.md#general-rules).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### decided

- Trigger: Current facts and Contract support a single bounded direction.
- Action: Record the decision, relevant options, constraints, chosen direction and boundary.
- Pass: One authorized next slice and its return boundary are explicit.
- Failure: If a material fact changes the direction, return to Contract and Decision before proceeding.

### evidence-on-demand

- Trigger: A necessary factual gap for the pending decision can be identified and requested.
- Action: Request the bounded evidence and pause the dependent release until the checkpoint is revisited.
- Pass: The requested fact and affected decision are explicit; no final branch has been selected.
- Failure: If acquisition is unauthorized or the required decision or authorization conflict remains unresolved, use blocked.

### blocked

- Trigger: The necessary decision, evidence or authority for the next slice is unavailable or conflicting.
- Action: State the precise blocker and leave the dependent slice unreleased.
- Pass: The missing input and blocked effect are recorded.
- Failure: Optional advisory failure cannot select a Core branch or create authorization.

## Node: slice

Authority: [policy owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/execution-control/execution-control.md#interaction-slice).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### released

- Trigger: The Contract and decision authorize one concrete bounded Interaction Slice.
- Action: Record its objective, allowed paths and mutations, and return conditions.
- Pass: Only this slice is released with its boundary explicit.
- Failure: Pause before crossing an unreleased boundary or any return condition.

### amend

- Trigger: A material fact requires changing the proposed slice or its Contract boundary.
- Action: Return to the Contract and decision to record and evaluate the change.
- Pass: A revised slice is released only after its scope and authority are established.
- Failure: Do not execute the changed scope while that decision or authority is unresolved.

### stop

- Trigger: A return condition, unresolved blocker or unreleased boundary is reached.
- Action: Stop the dependent work and report current progress and the boundary.
- Pass: The stopped effect and evidence needed for the next decision are explicit.
- Failure: Do not continue past the boundary by relabeling the same work.

## Node: delegation

Authority: [policy owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-state-record.md#record-shape).
For Multi-Agent allocation states, consult [role allocation](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md#general-rules).
For actual new-child creation only, consult [child creation](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-child-creation.md#general-rules).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### not applicable

- Trigger: Single-Agent is selected, or this bounded slice stays with Root and has no child creation, allocation, reuse, dispatch or recovery effect.
- Action: Record the concrete reason delegation does not apply to this slice.
- Pass: The absence of a child effect is established from current scope and state.
- Failure: A required but unavailable child capability is blocked, not not applicable.

### reserved

- Trigger: A valid allocation for the current stage is reserved and its child identity is still unbound.
- Action: Read the canonical record and preserve the staged role and slice conditions.
- Pass: The current reservation is valid without assuming a role assignment or child creation release.
- Failure: Missing or conflicting allocation evidence blocks the dependent child effect; do not reset unknown state.

### bound

- Trigger: A trusted current-session child identity is already bound to its original allocation.
- Action: Verify and preserve that identity and canonical allocation for the authorized next step.
- Pass: The trusted binding and its applicable lifecycle state are established.
- Failure: An untrusted, missing or conflicting identity blocks dependent reuse or dispatch; a description cannot spawn a child.

### blocked

- Trigger: A required child capability, allocation, trusted identity or lifecycle decision is unavailable or conflicting.
- Action: Preserve confirmed canonical state and report the exact blocked child effect.
- Pass: The missing prerequisite and affected effect are explicit.
- Failure: Do not reset unknown state, invent a binding or replace a child to bypass the block.

## Node: implementation

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/decision-and-execution/implementation.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### complete

- Trigger: The released implementation slice has been carried out within its authorized scope.
- Action: Return the changed paths and focused provisional checks or concrete issue.
- Pass: The approved slice is implemented and focused evidence is available.
- Failure: Focused checks are not final Verification and unresolved issues remain explicit.

### blocked

- Trigger: A required capability, path, authorization or material input for implementation is unavailable.
- Action: Stop the affected work and report the exact obstacle and current paths.
- Pass: The blocked part and remaining authorized work are distinguishable.
- Failure: Do not broaden scope or substitute an unauthorized effect to continue.

### return for control

- Trigger: A return condition, changed requirement or material boundary is encountered during implementation.
- Action: Pause and return the evidence and proposed decision to Control.
- Pass: Affected implementation remains paused until the appropriate current decision and slice are released.
- Failure: Do not implement the changed boundary using the prior release.

## Node: control

Authority: [policy owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/execution-control/execution-control.md#control-checkpoint).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### continue

- Trigger: The current Contract and released boundary remain valid for the next bounded work.
- Action: Release only the next bounded slice and record the current progress signal.
- Pass: The scope, owner and return conditions for that slice are explicit.
- Failure: A new material decision or unreleased boundary requires another Control return.

### amend

- Trigger: Current evidence shows the Contract or boundary must change before work resumes.
- Action: Synchronize and decide the change under existing authority before releasing affected work.
- Pass: The revised Contract and next bounded decision are explicit.
- Failure: Missing authority or an unresolved change keeps the affected work stopped.

### stop

- Trigger: A required decision, capability, authorization or boundary condition prevents continuation.
- Action: Stop the dependent work and record the exact reason.
- Pass: The stopped scope and required next input are explicit.
- Failure: Do not turn an unresolved blocker into a Continue release.

### evidence-on-demand

- Trigger: Control needs an identifiable missing fact available through an authorized request.
- Action: Pause release, request the bounded evidence and return to Control.
- Pass: The evidence request is an intermediate state, not a fourth final authorization outcome.
- Failure: If evidence cannot be obtained or an essential decision or authority conflicts, stop the affected work.

## Node: verification

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification.md#actions).
Classify and report results using [reporting actions](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-reporting.md#actions) and its [pass condition](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-reporting.md#pass-condition).
Classify and report logical or independent verification using [independence actions](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-independence.md#actions) and its [pass condition](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-independence.md#pass-condition); a real independent Session is required when the Contract requires it.

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### pass

- Trigger: All required checks for the exact current state have passing evidence and required independence is satisfied.
- Action: Record current fingerprints, checks, result categories and residual risks.
- Pass: Every required item within the current verification coverage has current passing evidence.
- Failure: Stale evidence, failed checks or missing required independence prevent a pass.

### failure

- Trigger: A required current-state check has a concrete failing result.
- Action: Report the failure, affected paths and blocking effect for diagnosis.
- Pass: The failed item and its current evidence are explicit.
- Failure: Do not report completion or conceal failure because other checks pass.

### inconclusive

- Trigger: A required check, evidence or required independent verification is unavailable, incomplete or ambiguous.
- Action: Report unavailable, assumed and unresolved evidence and its blocking effect.
- Pass: The limitation and affected acceptance items are explicit.
- Failure: Do not label same-session logical checks independent or infer a pass.

### not applicable with reason

- Trigger: A specific verification item is demonstrably outside the current authorized scope.
- Action: Record the item and factual reason it does not apply.
- Pass: The not-applicable reason is reviewable without waiving other required checks.
- Failure: Unknown applicability or unavailable evidence is inconclusive, not not applicable.

## Node: repair

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/repair.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### not applicable with reason

- Trigger: There is no applicable failing evidence requiring a repair candidate.
- Action: Record the current evidence and reason no repair diagnosis applies.
- Pass: The reason and unaffected verification status are explicit.
- Failure: Missing or unknown verification evidence is not proof that repair is unnecessary.

### repair

- Trigger: A concrete failure has identifiable affected paths and a plausible minimal repair candidate.
- Action: Describe the failure, paths and smallest candidate and hand off under the applicable owner.
- Pass: The candidate and evidence are explicit without assuming repair authorization.
- Failure: A material change requiring a decision pauses dependent repair; this checkpoint neither authorizes nor executes it.

### blocked

- Trigger: The failure, affected scope, necessary decision or repair capability cannot be established.
- Action: Report the missing diagnostic input or decision and pause dependent repair.
- Pass: The blocker and unresolved failure are explicit.
- Failure: Do not perform broad cleanup or assume approval to bypass the missing input.

## Node: documentation

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/completion-and-effects/documentation.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### complete

- Trigger: Authorized documentation or comments have been updated for the applicable verified state.
- Action: Confirm mirrors, current documentation epoch, applicable checks and any requested knowledge-write receipt.
- Pass: Required documentation output and checks are current with limitations reported.
- Failure: A failed required write, stale evidence or unresolved content-affecting re-verification prevents completion.

### not applicable with reason

- Trigger: No documentation, comment or requested reusable-knowledge output applies to the slice.
- Action: Record the concrete scope-based reason.
- Pass: The reason is explicit and does not waive applicable implementation verification.
- Failure: Unperformed requested documentation is incomplete, not not applicable.

### blocked

- Trigger: A required documentation path, capability, check, knowledge write or material decision is unavailable.
- Action: Report the specific blocked output and preserve current evidence.
- Pass: The missing prerequisite and incomplete output are explicit.
- Failure: Do not substitute unapproved documentation scope or claim the write succeeded.

## Node: git

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/completion-and-effects/git.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### no Git effect

- Trigger: The authorized slice requests no Git or external repository effect.
- Action: Record that no Git effect is required.
- Pass: The no-effect conclusion matches the current requested scope.
- Failure: An unperformed requested Git effect is not a no-effect conclusion.

### authorized effect

- Trigger: A specific Git or external effect is authorized for an exact target.
- Action: Confirm the exact repository, branch, remote, operation, authorization and current verified fingerprints; perform only that authorized operation and record or verify its result as applicable.
- Pass: The authorized operation has completed against the exact target, records the latest applicable epochs and matches their verified content fingerprints.
- Failure: Stop for ambiguous target, conflict, stale content or missing authorization.

### blocked

- Trigger: A requested Git effect lacks a clear target, authority, current verification or required capability.
- Action: Report the precise obstacle and leave the affected operation unperformed.
- Pass: The requested effect and blocking prerequisite are explicit.
- Failure: Do not include unrelated changes or broaden the operation to recover.

## Node: acceptance

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/completion-and-effects/acceptance.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### complete

- Trigger: Every applicable latest epoch and Contract acceptance condition has current required evidence.
- Action: Report each acceptance item and content, documentation and Git status with residual risks.
- Pass: No required item, capability, verification boundary or authorization remains unresolved.
- Failure: Stale evidence or an unresolved required item prevents a complete claim.

### incomplete

- Trigger: Known applicable or required work, checks or repairs remain outstanding or have not run.
- Action: Report each outstanding item and the current evidence without claiming completion.
- Pass: Remaining work and its status are explicit.
- Failure: Do not call the task complete while any required item remains outstanding.

### blocked

- Trigger: A required next step cannot continue because actual authority, capability, critical evidence or a necessary decision is missing.
- Action: Report the specific missing prerequisite, affected next step and current incomplete status.
- Pass: The blocker and its effect are explicit.
- Failure: Difficulty or elapsed time alone is not a blocked reason, and blocked is not complete.

## Node: task_intent

Authority: [policy owner](../../../../docs/skill/SKILL.md#scope).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### coding

- Trigger: Authoritative task facts show repository or project exploration, implementation, refactoring, debugging, tests, documentation, developer-tool output or non-trivial Git work.
- Action: Classify the current task as Coding and apply the existing Coding scope.
- Pass: The classification is supported by a direct fact and its bounded scope.
- Failure: A mixed task containing Coding work remains Coding; missing examples do not prove an exclusion.

### not coding

- Trigger: Direct authoritative facts establish that the task is outside the Coding scope.
- Action: Record the source and bounded reason for the non-Coding classification.
- Pass: The scope exclusion is affirmatively supported by current evidence.
- Failure: A missing listing or unknown task fact is not proof of not coding.

### unclear

- Trigger: Available authoritative facts do not establish whether the task falls within Coding scope.
- Action: Identify the missing scope fact and keep dependent classification unresolved.
- Pass: The uncertainty and its effect on the next decision are explicit.
- Failure: Do not infer not coding from an absent example or insufficient evidence.

## Node: output_class

Authority: [policy owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-confirmation.md#session-mode-selection).
For role ownership and ordinary-documentation boundaries, consult [Session role ownership](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/session-role-ownership.md#general-rules).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### code_configuration

- Trigger: The current bounded output slice contains code or configuration.
- Action: Classify that slice as code_configuration and apply its existing ownership and gates.
- Pass: The classification identifies the actual code or configuration output.
- Failure: Do not conceal code within an ordinary documentation or other classification.

### skill_instructions

- Trigger: The current bounded output slice changes Skill instructions.
- Action: Classify that slice as skill_instructions; any delegation remains subject to existing child gates.
- Pass: The Skill instruction output and its responsible role are explicit.
- Failure: This classification alone does not authorize child creation or change policy.

### ordinary_documentation

- Trigger: The current bounded output slice is ordinary non-Skill documentation.
- Action: Classify that slice as ordinary_documentation and retain Root authorship.
- Pass: The ordinary documentation scope is separate from any code or Skill instruction slice.
- Failure: Do not delegate ordinary documentation to a child or use this class to hide code.

### other

- Trigger: The bounded output is known and belongs to none of code_configuration, skill_instructions or ordinary_documentation.
- Action: Record the known output and classify that slice as other.
- Pass: Evidence affirmatively establishes why the first three classes do not apply.
- Failure: Unknown output is not other, and this class grants no creation authority.

### unknown

- Trigger: Evidence is insufficient to classify the current bounded output.
- Action: Identify the missing output fact and leave the classification unresolved.
- Pass: The uncertainty is explicit without choosing a different class.
- Failure: Do not treat unknown as other or use it to authorize child creation.

## Node: contract_change

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/contract.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### unchanged

- Trigger: Current evidence affirmatively shows no material change to outcome, scope, constraints or acceptance.
- Action: Record the four-dimension comparison before dependent work continues.
- Pass: All four Contract dimensions remain valid for the current slice.
- Failure: Missing evidence about a dimension is not proof that it is unchanged.

### amend

- Trigger: A material change is confirmed and the required amendment is covered by existing authority.
- Action: Synchronize the Contract, plan and Decision before affected work resumes.
- Pass: The revised four dimensions and dependent decision are explicit.
- Failure: Any new effect lacking authorization remains unreleased despite the amendment.

### blocked

- Trigger: The necessary change, its scope or required authority cannot be confirmed.
- Action: Identify the exact unresolved change or authorization and pause affected work.
- Pass: The blocker and affected Contract dimensions are explicit.
- Failure: Do not treat unknown scope or authority as an unchanged or authorized amendment.

## Node: verification_impact

Authority: [policy owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-epoch.md#actions).

Entry action: Report the source-backed criteria for this bounded node; lookup performs no workflow effect.

### implementation/content

- Trigger: Current evidence shows only the implementation/content dimension changed.
- Action: Advance that epoch and queue or perform its applicable current-state checks.
- Pass: Prior verification of the affected content is not reused as current evidence.
- Failure: Do not skip content verification or infer other dimensions changed without evidence.

### documentation

- Trigger: Current evidence shows only the documentation dimension changed.
- Action: Advance that epoch and run applicable documentation checks.
- Pass: Current documentation evidence is available for the changed output.
- Failure: If executable content, Contract or acceptance also changed, classify multiple affected dimensions.

### Git metadata

- Trigger: Current evidence shows only Git metadata changed.
- Action: Advance the Git metadata epoch and compare targeted content with verified fingerprints.
- Pass: Git state points to the latest applicable verified content and documentation.
- Failure: Content divergence returns to the corresponding verification; metadata alone does not advance content epochs.

### multiple

- Trigger: Current evidence establishes changes in at least two verification dimensions.
- Action: Advance each affected epoch and schedule its applicable checks or Verification.
- Pass: Every affected dimension is tracked against current evidence.
- Failure: Do not reuse stale evidence for any changed dimension or omit an affected check.

### none

- Trigger: Positive current evidence establishes that no verification dimension changed.
- Action: Record the comparison and retain already applicable checks and evidence requirements.
- Pass: Zero changed dimensions is supported by facts, not by missing information.
- Failure: Unknown impact is not none, and none does not waive existing required checks.
