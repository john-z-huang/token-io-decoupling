# Coding Workflow — Multi-Agent Mode

[English](coding-multi-agent.md) | [简体中文](coding-multi-agent_zh_cn.md)

This route is selected by the Coding workflow and is valid only after the Mode checkpoint releases Multi-Agent Coding. Before route entry, the Mode checkpoint consumes only mode confirmation, count, re-entry, and the state record; child allocation, creation, dispatch, reuse, and lifecycle are loaded at their numbered route steps.

## Workflow map

```mermaid
flowchart TD
    M01["01 Contract"]
    M02["02 Environment / Enhanced selection"]
    D_ENHANCED{"Optional Enhanced operation needed?"}
    D_ENHANCED_HOST{"Trusted identity and required operation guards verified?"}
    ACT_NATIVE["Native candidate; verify prior Enhanced authority before use"]
    M03["03 Mode"]
    M04["04 Session / state and audit resolution"]
    D_ROOT_STORE{"Enhanced Root store selected and its identity, guards, and schema are valid?"}
    ACT_ROOT_OPEN["Open or resume Root store after Session boundary; retain audit as pending until Root records its actual resolution"]
    D_AUTHORITY_TRANSFER{"Does a previously canonical Enhanced record require transfer back to Native?"}
    ACT_NATIVE_TRANSFER["Freeze Enhanced writers; settle in-flight operations; write and read back the complete canonical record"]
    D_NATIVE_RECON{"Is Native currently canonical, or is a Root comparison unresolved?"}
    ACT_NATIVE_RECON["Review the full set; confirm an exact comparison or resolve supported differences"]
    ACT_RECOVERY_RECHECK["Within M04, recheck M01 Contract, M06 current Context, and M07 Decision; re-establish state without reopening Mode or repeating a completed prompt"]
    ACT_STATE_READBACK["Confirm the current canonical Session state and read it back before audit resolution"]
    D_AUDIT_CONFIG{"Reuse valid explicit/completed settings, resume pending prompt, or ask if unasked?"}
    ACT_AUDIT_PROMPT["Ask fixed audit question only if unasked; record actual prompt and deadline"]
    D_AUDIT_REPLY{"Valid reply, invalid/ambiguous reply, verified timeout, or unavailable?"}
    ACT_AUDIT_REPLY["Record valid reply; update only selected Root fields"]
    ACT_AUDIT_CLARIFY["Clarify only invalid/ambiguous fields; retain pending prompt"]
    D_AUDIT_CORRECTION{"Valid correction, still invalid/ambiguous, or explicit default?"}
    ACT_AUDIT_DEFAULT["Record explicit Root balanced/milestone_only; preserve Worker value and timeout history"]
    ACT_AUDIT_WAIT["Wait before deadline; preserve pending state"]
    ACT_AUDIT_TIMEOUT["No reply and actual elapsed time >=60s; default Root balanced/milestone_only; preserve Worker or fill full"]
    ACT_AUDIT_CONFIRM["Confirm the selected canonical Root audit record and read it back before leaving Session"]
    M05["05 Allocation / unassigned capacity only"]
    M06["06 Context / source and decision context"]
    M07["07 Decision / plan, Bootstrap, advisory selection"]
    M08["08 Slice / concrete Interaction Slice release"]
    M09["09 Child Creation / reserved role, effort, and current hashes"]
    D_WORKER_STORE{"Is Enhanced selected and the real child identity bound to the released allocation?"}
    ACT_WORKER_OPEN["Initialize or resume only that Worker store after schema validation"]
    D_CONTEXT_GEN{"Does an unresolved downstream decision need reviewed context?"}
    ACT_CONTEXT_GEN["Generate bounded context from provenance-labeled facts; review source, relevance, and exact input hash"]
    ACT_CONTEXT_DIRECT["Use direct owner and verified facts; skip settled advice or directly review generation failure"]
    ACT_TASK_ASSIGN["Apply Task Assignment; explicit direction or unusable context skips matching advice; use direct facts"]
    D_EXECUTOR{"Executor established from current task, Session, and permission facts?"}
    D_CHILD_POOL{"Suitable current-session child pool?"}
    ACT_CHILD_DIRECT["Use an explicit, unique, or sole idle eligible child; recheck identity and permissions"]
    ACT_CHILD_ADVICE["For 2+ idle candidates, prefer a suitable idle Primary; otherwise compare task-relevant context"]
    ACT_CHILD_REVIEW["Review advice against current role, capability, permission, identity, and availability"]
    ACT_CHILD_WAIT["Wait while a suitable existing child is busy; recheck when idle"]
    D_OUTPUT_EXPLICIT{"Has the user settled who produces or whether this output is produced?"}
    ACT_OUTPUT_ADVICE["Assess direct output size independently under Output Token Routing"]
    D_OUTPUT_RESULT{"Output-size result?"}
    ACT_OUTPUT_CHILD["Large output: use a suitable idle existing child"]
    ACT_OUTPUT_HOLD["Large output with no idle child: hold; output advice alone does not authorize creation"]
    ACT_OUTPUT_WAIT["Keep the requested output pending until a suitable child is idle"]
    ACT_OUTPUT_NO["No large output: Root may proceed subject to other gates"]
    D_NEW_CHILD{"Does Task Assignment independently require a new child?"}
    D_INDEPENDENT_CHILD{"Does Task Assignment independently require a new child for this authorized task?"}
    ACT_ROLE_NA["Role selection N/A: no new child; record why"]
    D_ROLE_SELECT{"Is child creation or role explicit in the user instruction?"}
    ACT_ROLE_ADVICE["Select one available maintained role using reviewed context and current-session state"]
    ACT_ROLE_REVIEW["Root verifies role fit, current-session uniqueness, permission, and direct-fact fallback"]
    D_ROLE_CAPACITY{"Is a locked slot available and a different role unoccupied?"}
    ACT_ROLE_RESERVE["Reserve the unique role in the authorized slot before Slice release"]
    ACT_BUDGET_APPROVAL["Request explicit user approval for exactly +1 slot for a different role"]
    M10["10 Dispatch / preset-selected preview or full body; N/A when no child"]
    M11["11 Implementation / Worker output, Control advice"]
    M12["12 Verification / advice and current report"]
    M13["13 Repair / disposition and reverify"]
    D_REPAIR{"Repair outcome: narrow repair, material Contract change, material Decision change, or blocked evidence?"}
    M14["14 Documentation / parent-authored docs and impact"]
    M15["15 Git / read actual exchange and apply audit preset"]
    M16["16 Acceptance"]
    D_PLAN{"User goal requests planning, exploration, or producing/updating a plan?"}
    ACT_PLAN["Persist and read-verify plan Memory"]
    D_PLAN_SAVED{"Plan Memory saved and read-verified?"}
    D_ARCHIVE{"Active plan Memory for this task exists?"}
    ACT_ARCHIVE["Move plan to archive and read-verify"]
    D_ARCHIVED{"Archived plan verified?"}
    D_BOOT{"Does Bootstrap/Refresh meet the current-facts trigger?"}
    ACT_BOOT_PLAN["Plan only when trigger applies; select/reserve its role in M07; no child yet"]
    D_PLAN_MATCH{"Relevant active plan exists?"}
    ACT_PLAN_SCAN["List active plans/"]
    ACT_PLAN_READ["Read and check matching plan"]
    D_RULE_ACCESS{"Select bounded current rule lookup?"}
    ACT_RULE_CONTEXT["Read selected current node and mapped owner heading"]
    ACT_RULE_DIRECT["Confirm direct owner text and required references"]
    ACT_INITIAL_CLASSIFY["Use direct owners for intent/output classification; advice N/A before authorized Root"]
    D_DECISION_ADVICE{"Use optional advice for a current Decision question?"}
    ACT_DECISION_ADVICE["Review typed advice only as input; stale/failure falls back"]
    ACT_DECISION_DIRECT["Confirm direct owner and current facts before planning/release"]
    D_CONTROL_ADVICE{"Use optional Control advice?"}
    ACT_CONTROL_ADVICE["Review advice only as input; stale/failure falls back"]
    ACT_CONTROL_DIRECT["Confirm current evidence and choose explicit trusted outcome"]
    D_EPOCH_ADVICE{"Use optional coverage-dimension advice?"}
    ACT_EPOCH_ADVICE["Review coverage suggestion only; stale/failure falls back"]
    ACT_EPOCH_DIRECT["Confirm current fingerprints and run required verification"]
    D_RECON{"More facts required?"}
    ACT_RECON_PLAN["Plan bounded reconnaissance; no implementation release"]
    D_MEMO{"Eligible child output? If yes, memo enabled?"}
    ACT_MEMO["Verify named memory and write capability"]
    D_CONTROL{"Control: Continue / Amend / Stop"}
    D_RECOVERY_GATE{"Before the next slice, is post-floor Control Continue current for the Control rule and relevant Epochs?"}
    D_VERIFY{"Current epoch passed?"}
    D_DOC{"Documentation changed content or Contract?"}
    D_GIT{"Git authorized and verified?"}
    BLOCK["Blocked: report missing boundary"]
    DONE["Acceptance complete"]
    M01 --> ACT_INITIAL_CLASSIFY
    ACT_INITIAL_CLASSIFY -- direct sources confirmed / advice N/A before Root --> M02
    ACT_INITIAL_CLASSIFY -- required source unavailable --> BLOCK
    M02 --> D_ENHANCED
    D_ENHANCED -- no / Native default / N/A --> M03
    D_ENHANCED -- yes / Enhanced needed --> D_ENHANCED_HOST
    D_ENHANCED_HOST -- verified --> M03
    D_ENHANCED_HOST -- Native candidate; verify prior Enhanced authority before use --> ACT_NATIVE
    ACT_NATIVE --> M03
    D_ENHANCED_HOST -- required capability missing or unknown --> BLOCK
    M03 --> M04
    M04 --> D_ROOT_STORE
    D_ROOT_STORE -- Enhanced selected; current identity and schema verified --> D_NATIVE_RECON
    D_ROOT_STORE -- Native / Enhanced not selected / check existing authority --> D_AUTHORITY_TRANSFER
    D_ROOT_STORE -- required identity, guard, or schema unavailable --> BLOCK
    ACT_ROOT_OPEN -- open or validation failed --> BLOCK
    ACT_ROOT_OPEN -- open or resume Root store --> ACT_STATE_READBACK
    D_AUTHORITY_TRANSFER -- no prior Enhanced authority / N/A --> ACT_STATE_READBACK
    D_AUTHORITY_TRANSFER -- prior Enhanced authority; transfer authorized and verified --> ACT_NATIVE_TRANSFER
    D_AUTHORITY_TRANSFER -- history, freeze, or readback unknown / failed --> BLOCK
    ACT_NATIVE_TRANSFER -- complete record frozen, copied, and read back --> ACT_STATE_READBACK
    ACT_NATIVE_TRANSFER -- incomplete or indeterminate --> BLOCK
    D_NATIVE_RECON -- no Native history / N/A --> ACT_ROOT_OPEN
    D_NATIVE_RECON -- prior resolution current; no unresolved comparisons --> ACT_STATE_READBACK
    D_NATIVE_RECON -- unresolved Native history or comparison --> ACT_NATIVE_RECON
    ACT_NATIVE_RECON -- exact comparison confirmed --> ACT_STATE_READBACK
    ACT_NATIVE_RECON -- material resolution committed; recheck Contract --> ACT_RECOVERY_RECHECK
    ACT_NATIVE_RECON -- unsupported difference or incomplete review --> BLOCK
    ACT_RECOVERY_RECHECK -- Within M04, recheck M01 Contract, M06 current Context, and M07 Decision; re-establish canonical state --> ACT_STATE_READBACK
    ACT_STATE_READBACK -- current canonical state confirmed and read back --> D_AUDIT_CONFIG
    ACT_STATE_READBACK -- required state or readback unavailable / failed --> BLOCK
    D_AUDIT_CONFIG -- yes / migration reuse --> ACT_AUDIT_CONFIRM
    D_AUDIT_CONFIG -- unasked / first eligible question only --> ACT_AUDIT_PROMPT
    D_AUDIT_CONFIG -- pending / no reply observed; resume original deadline --> D_AUDIT_REPLY
    D_AUDIT_CONFIG -- pending / invalid reply already observed --> D_AUDIT_CORRECTION
    D_AUDIT_CONFIG -- invalid config / focused clarification --> ACT_AUDIT_CLARIFY
    D_AUDIT_CONFIG -- unavailable / unresolved schema conflict --> BLOCK
    ACT_AUDIT_PROMPT --> D_AUDIT_REPLY
    D_AUDIT_REPLY -- valid actual reply --> ACT_AUDIT_REPLY
    ACT_AUDIT_REPLY --> ACT_AUDIT_CONFIRM
    D_AUDIT_REPLY -- invalid / ambiguous reply --> ACT_AUDIT_CLARIFY
    ACT_AUDIT_CLARIFY -- same prompt / original deadline --> D_AUDIT_CORRECTION
    D_AUDIT_CORRECTION -- valid correction --> ACT_AUDIT_REPLY
    D_AUDIT_CORRECTION -- still invalid / ambiguous --> ACT_AUDIT_CLARIFY
    D_AUDIT_CORRECTION -- explicit default choice --> ACT_AUDIT_DEFAULT
    ACT_AUDIT_DEFAULT --> ACT_AUDIT_CONFIRM
    D_AUDIT_REPLY -- pending / before deadline --> ACT_AUDIT_WAIT
    ACT_AUDIT_WAIT -- check reply / retain deadline --> D_AUDIT_REPLY
    D_AUDIT_REPLY -- no reply / actual elapsed >=60s --> ACT_AUDIT_TIMEOUT
    ACT_AUDIT_TIMEOUT --> ACT_AUDIT_CONFIRM
    ACT_AUDIT_CONFIRM -- canonical Root audit record confirmed and read back --> M05
    ACT_AUDIT_CONFIRM -- canonical record missing or not confirmed --> BLOCK
    D_AUDIT_REPLY -- prompt or timing unavailable --> BLOCK
    M05 --> M06
    M06 --> D_RULE_ACCESS
    D_RULE_ACCESS -- yes / bounded lookup selected --> ACT_RULE_CONTEXT
    D_RULE_ACCESS -- no / direct source / N/A --> ACT_RULE_DIRECT
    ACT_RULE_CONTEXT -- loaded or unavailable / direct fallback --> ACT_RULE_DIRECT
    ACT_RULE_DIRECT -- current owner and required references confirmed --> ACT_PLAN_SCAN
    ACT_RULE_DIRECT -- required owner unavailable --> BLOCK
    ACT_PLAN_SCAN --> D_PLAN_MATCH
    ACT_PLAN_SCAN -- failed / unavailable --> BLOCK
    D_PLAN_MATCH -- yes --> ACT_PLAN_READ
    D_PLAN_MATCH -- no / N/A --> D_CONTEXT_GEN
    ACT_PLAN_READ --> D_CONTEXT_GEN
    ACT_PLAN_READ -- failed / unavailable --> BLOCK
    D_CONTEXT_GEN -- unresolved downstream advice needs context --> ACT_CONTEXT_GEN
    D_CONTEXT_GEN -- explicit direction settles choices / no advice needed: N/A --> ACT_CONTEXT_DIRECT
    ACT_CONTEXT_GEN -- reviewed context and exact input hash are current --> M07
    ACT_CONTEXT_GEN -- failed / insufficient; direct review only --> ACT_CONTEXT_DIRECT
    ACT_CONTEXT_DIRECT -- verified facts suffice / explicit instruction honored --> M07
    ACT_CONTEXT_DIRECT -- essential facts unavailable or conflicting --> BLOCK
    M07 --> D_DECISION_ADVICE
    D_DECISION_ADVICE -- yes / explicitly enabled and relevant --> ACT_DECISION_ADVICE
    D_DECISION_ADVICE -- no / Native / disabled / unavailable / N/A --> ACT_DECISION_DIRECT
    ACT_DECISION_ADVICE -- current advice or failure / direct review --> ACT_DECISION_DIRECT
    ACT_DECISION_DIRECT -- owner and facts confirmed --> D_PLAN
    ACT_DECISION_DIRECT -- required owner or evidence unavailable --> BLOCK
    D_PLAN -- yes --> ACT_PLAN
    D_PLAN -- no / N/A --> D_RECON
    ACT_PLAN --> D_PLAN_SAVED
    D_PLAN_SAVED -- yes --> D_RECON
    D_PLAN_SAVED -- no / unavailable --> BLOCK
    D_RECON -- yes --> ACT_RECON_PLAN
    ACT_RECON_PLAN --> D_BOOT
    D_RECON -- no / N/A --> D_BOOT
    D_BOOT -- current facts justify Bootstrap/Refresh --> ACT_BOOT_PLAN
    ACT_BOOT_PLAN -- plan only; no early role reservation --> ACT_TASK_ASSIGN
    D_BOOT -- trigger absent / N/A with reason --> ACT_TASK_ASSIGN
    ACT_TASK_ASSIGN --> D_EXECUTOR
    D_EXECUTOR -- root --> D_OUTPUT_EXPLICIT
    D_EXECUTOR -- sub_agent --> D_CHILD_POOL
    D_EXECUTOR -- insufficient / unresolved --> BLOCK
    D_CHILD_POOL -- explicit eligible idle, one eligible idle, or one idle after filtering --> ACT_CHILD_DIRECT
    D_CHILD_POOL -- 2+ eligible idle candidates --> ACT_CHILD_ADVICE
    D_CHILD_POOL -- suitable child busy; assess output before waiting --> D_OUTPUT_EXPLICIT
    D_CHILD_POOL -- no suitable existing child; a new child may be required --> D_OUTPUT_EXPLICIT
    D_CHILD_POOL -- identity, capability, or permission uncertain --> BLOCK
    ACT_CHILD_ADVICE --> ACT_CHILD_REVIEW
    ACT_CHILD_REVIEW -- current suitable idle child confirmed; apply Primary/context preference --> ACT_CHILD_DIRECT
    ACT_CHILD_REVIEW -- advice API failed; suitable Primary is busy; assess output before waiting --> D_OUTPUT_EXPLICIT
    ACT_CHILD_REVIEW -- stale facts or no safe candidate --> BLOCK
    ACT_CHILD_DIRECT --> D_OUTPUT_EXPLICIT
    ACT_CHILD_WAIT -- candidate becomes idle; recheck current facts --> D_CHILD_POOL
    D_OUTPUT_EXPLICIT -- explicit user direction; skip corresponding advice --> D_NEW_CHILD
    D_OUTPUT_EXPLICIT -- no explicit direction; assess direct output --> ACT_OUTPUT_ADVICE
    ACT_OUTPUT_ADVICE --> D_OUTPUT_RESULT
    D_OUTPUT_RESULT -- no --> ACT_OUTPUT_NO
    D_OUTPUT_RESULT -- yes / suitable idle child --> ACT_OUTPUT_CHILD
    D_OUTPUT_RESULT -- yes / no idle suitable child --> ACT_OUTPUT_HOLD
    D_OUTPUT_RESULT -- insufficient evidence --> BLOCK
    ACT_OUTPUT_NO --> D_NEW_CHILD
    ACT_OUTPUT_CHILD --> ACT_ROLE_NA
    ACT_OUTPUT_HOLD -- Task Assignment independently requires a new child --> D_INDEPENDENT_CHILD
    ACT_OUTPUT_HOLD -- no independent child need; remain pending --> ACT_OUTPUT_WAIT
    ACT_OUTPUT_WAIT -- eligible child becomes idle; reassess output --> ACT_OUTPUT_ADVICE
    D_INDEPENDENT_CHILD -- yes / continue through role, budget, Slice, and creation gates --> D_ROLE_SELECT
    D_INDEPENDENT_CHILD -- no / output advice alone; remain pending --> ACT_OUTPUT_WAIT
    D_NEW_CHILD -- yes / Assignment independently needs new child --> D_ROLE_SELECT
    D_NEW_CHILD -- no / suitable existing child busy --> ACT_CHILD_WAIT
    D_NEW_CHILD -- no / Root or suitable child idle: N/A --> ACT_ROLE_NA
    D_ROLE_SELECT -- explicit creation/role; skip role advice --> ACT_ROLE_REVIEW
    D_ROLE_SELECT -- no explicit role; reviewed context available --> ACT_ROLE_ADVICE
    D_ROLE_SELECT -- context generation failed; direct facts suffice; no downstream advice --> ACT_ROLE_REVIEW
    ACT_ROLE_ADVICE -- suggestion, failure, or insufficient result; Root review --> ACT_ROLE_REVIEW
    ACT_ROLE_REVIEW -- role and current facts established --> D_ROLE_CAPACITY
    ACT_ROLE_REVIEW -- role, facts, or permission unresolved --> BLOCK
    D_ROLE_CAPACITY -- locked unassigned slot; different role remains available --> ACT_ROLE_RESERVE
    D_ROLE_CAPACITY -- no slot; different role remains available --> ACT_BUDGET_APPROVAL
    D_ROLE_CAPACITY -- all roles occupied or no role fits --> BLOCK
    ACT_BUDGET_APPROVAL -- user approves exactly +1 through Count Gate --> ACT_ROLE_RESERVE
    ACT_BUDGET_APPROVAL -- approval denied, unavailable, or broader than +1 --> BLOCK
    ACT_ROLE_RESERVE -- unique role recorded; remains occupied after creation --> D_RECOVERY_GATE
    ACT_ROLE_RESERVE -- stale/conflicting state or reservation failure --> BLOCK
    ACT_ROLE_NA --> D_RECOVERY_GATE
    D_RECOVERY_GATE -- no recovery floor / N/A or post-floor Continue is current for Control rule and relevant Epochs --> M08
    D_RECOVERY_GATE -- fresh or current Continue required --> D_CONTROL_ADVICE
    M08 --> M09
    M09 -- reserved role consumed; child created and identity bound --> D_WORKER_STORE
    D_WORKER_STORE -- Enhanced selected; identity bound; guards valid --> ACT_WORKER_OPEN
    D_WORKER_STORE -- Native / Enhanced not selected / N/A --> D_MEMO
    ACT_WORKER_OPEN --> D_MEMO
    ACT_WORKER_OPEN -- open or validation failed --> BLOCK
    D_WORKER_STORE -- required identity, guard, or schema unavailable --> BLOCK
    M09 -- no eligible output: Not applicable --> D_MEMO
    M09 -- required evidence or adequate effort unavailable, stale/mismatched fingerprint or decision-input hash, or creation boundary fails --> BLOCK
    M10 -- task authorization and body visible / no extra message: N/A --> M11
    M10 -- authorization or body check fails --> BLOCK
    D_MEMO -- enabled --> ACT_MEMO
    ACT_MEMO --> M10
    D_MEMO -- disabled / N/A --> M10
    M11 --> D_CONTROL_ADVICE
    D_CONTROL_ADVICE -- yes / explicitly enabled --> ACT_CONTROL_ADVICE
    D_CONTROL_ADVICE -- no / Native / disabled / unavailable / N/A --> ACT_CONTROL_DIRECT
    ACT_CONTROL_ADVICE -- current advice or failure / direct review --> ACT_CONTROL_DIRECT
    ACT_CONTROL_DIRECT -- explicit trusted outcome selected --> D_CONTROL
    ACT_CONTROL_DIRECT -- required owner or essential evidence unobtainable --> BLOCK
    M11 -- actual return body unavailable/incomplete, or preset evidence missing --> BLOCK
    D_CONTROL -- Continue / Evidence-on-Demand (retrievable evidence pause) --> M06
    D_CONTROL -- amend --> M07
    D_CONTROL -- done / normal post-implementation only; no recovery Slice pending --> M12
    D_CONTROL -- stop --> BLOCK
    M12 -- verifier exchange visible / no child verifier required: N/A --> D_EPOCH_ADVICE
    D_EPOCH_ADVICE -- yes / explicitly enabled --> ACT_EPOCH_ADVICE
    D_EPOCH_ADVICE -- no / Native / disabled / unavailable / N/A --> ACT_EPOCH_DIRECT
    ACT_EPOCH_ADVICE -- coverage hint or failure / direct verification --> ACT_EPOCH_DIRECT
    ACT_EPOCH_DIRECT -- current evidence confirmed --> D_VERIFY
    ACT_EPOCH_DIRECT -- required evidence unavailable --> BLOCK
    M12 -- actual request/report body unavailable/incomplete, or preset evidence missing --> BLOCK
    D_VERIFY -- repairable --> M13
    D_VERIFY -- passed --> M14
    D_VERIFY -- required evidence unavailable --> BLOCK
    M13 -- repair exchange visible / no child exchange: N/A --> D_REPAIR
    M13 -- actual repair body unavailable/incomplete, or preset evidence missing --> BLOCK
    D_REPAIR -- narrow repair complete with handoff and new fingerprint, or evidence-backed no-failure N/A --> M12
    D_REPAIR -- material Contract change; renew Contract --> M01
    D_REPAIR -- material Decision change within Contract; renew Decision --> M07
    D_REPAIR -- required diagnosis, authorization, scope, or handoff unavailable --> BLOCK
    M14 -- parent documentation complete / no docs child: N/A --> D_DOC
    M14 -- required parent evidence unavailable --> BLOCK
    D_DOC -- content change --> M12
    D_DOC -- Contract change --> M07
    D_DOC -- no change / N/A --> M15
    M15 -- Git exchange visible / no Git child: N/A --> D_GIT
    M15 -- actual Git body unavailable/incomplete, or preset evidence missing --> BLOCK
    D_GIT -- authorized / N/A --> M16
    D_GIT -- no permission --> BLOCK
    M16 --> D_ARCHIVE
    D_ARCHIVE -- yes --> ACT_ARCHIVE
    D_ARCHIVE -- no / N/A --> DONE
    ACT_ARCHIVE --> D_ARCHIVED
    D_ARCHIVED -- yes --> DONE
    D_ARCHIVED -- no / failed / unavailable --> BLOCK
```
Numbered nodes match the sole ordered checklist below. Record the `Not applicable` reason for a skipped conditional concept. The map selects and orders concepts; the checklist and same-language owner links provide concrete actions, evidence, and failure handling.

## Mode contract

- A Worker receives one released Interaction Slice and returns through its parent; it does not create a recursive hierarchy or treat another Worker's progress as permission.
- Mode/count belongs to the Mode checkpoint and M03 owners; role, Slice, creation, dispatch, reuse, and lifecycle boundaries are consumed from linked owners at M07–M10.
- User prohibitions remain active. A conflict with locked mode/count blocks and is reported; do not silently change routes or simulate multi-agent behavior.

## Composed inputs

Read each owner at its numbered consuming step. The checklist below supplies same-language links, actions, evidence, and failure boundaries there; conditional exchange/memo/code-structure owners load only when triggered. This section is not a preload catalog.

## Responsibility boundary

Use the role ownership defined in [session role ownership](../layer-01-fundamental-concepts/session-runtime/session-role-ownership.md); this route adds only the Multi-Agent conditions below.

## Route-specific environment requirements

Use the inventory and shared runtime rules from the [Environment capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md), including the model bindings in [Runtime and Model Provider Support](../layer-01-fundamental-concepts/session-runtime/runtime-provider-support.md). Continue only when it exposes the capabilities required by the task record and released slice. A Worker returns only to its direct parent and cannot create/manage Agents or contact arbitrary threads.

## Ordered route checklist

L3 checkpoint owners define semantic outcomes; this checklist maps each result to its numbered route stage and next action. Run every numbered stage in order. For every linked owner, check its applicable actions and pass condition, record the result and evidence, and stop when a required result is missing. Record `Not applicable` with a reason for each conditional action; a link or earlier summary is not proof that its check was completed. The Coding selector completed stages 1–3 before route entry: inspect their released evidence without repeating the gates. The root parent makes semantic decisions and controls every release; Workers return only through that parent.

1. **Contract and common protocol.** Confirm the [Contract checkpoint](../layer-02-workflow-concepts/entry-and-context/contract.md) has an explicit goal, hard user/runtime/repository/permission/safety limits, authorized effects, settled decisions, open questions, and acceptance conditions. Apply the [shared protocols](../../share/shared-protocols.md): keep one current Semantic Contract, separate observed facts from assumptions, send bounded amendments with a stable prefix and small delta, use a parent-only return path and the Dispatch Preview or complete safe body selected by the audit preset, and stop the dependent slice if required context or a return path is unavailable. Do not turn an unresolved question into dispatch authority. Before using an advisory, establish task intent and eligible output classification from their direct owners; record advisory use as `Not applicable` until Mode, Session, and authorized Root context pass.
2. **Environment and capabilities.** At [Environment](../layer-02-workflow-concepts/entry-and-context/environment.md) and [capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md), confirm one runtime and record capabilities required by this task. Call [Enhanced Path Selection](../layer-03-workflow-checkpoints/enhanced-path-selection.md): Native/`Not applicable` continues without Enhanced initialization; Enhanced requires current eligibility, identity, and guard evidence. Missing evidence blocks the dependent branch. Load [Enhanced Workflow Availability](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-workflow-availability.md) and [Enhanced Host Binding](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-host-binding.md) for eligibility/identity guards; record evidence or Native `Not applicable`, and block when required capability is unknown.
3. **Mode, count, and record.** Confirm [Mode](../layer-02-workflow-concepts/entry-and-context/mode.md) released Multi-Agent; check [mode confirmation](../layer-01-fundamental-concepts/delegation/delegation-mode-confirmation.md), [count gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md), [state record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md), and [re-entry](../layer-01-fundamental-concepts/delegation/delegation-mode-reentry.md) for a locked positive count, `gate_status: released`, and exactly `child_count` initially `agent: unbound`, `role: unassigned`, `slice_status: pending` reserved slots. This releases route/count only, not a concrete slice or Child Creation. Later directives reuse locked topology; missing state/capabilities block the route. Do not request semantic advice before Session has passed and authorized Root state exists; follow these existing owners, and do not let advice override locked Mode/count.
   - Confirm [Route Entry](../layer-03-workflow-checkpoints/route-entry.md) returned this route from released Mode evidence. A mismatch, missing result, or unresolved prerequisite blocks execution and returns to the Coding entry.
4. **Session roles and Context Firewall.** Call [Session State Resolution](../layer-03-workflow-checkpoints/session-state-resolution.md) to establish canonical authority, complete triggered reconciliation/transfer checks, and guardedly open or resume Root; map the result to M04. All successful paths consume only verified identity, current canonical record, and readback before audit. Record Not applicable only when a conditional trigger is absent, with the observed reason. For material recovery, recheck Contract, current Context, and Decision (M01/M06/M07) within M04, then re-establish and read back canonical state; do not bypass M04, advance early to Context/Decision, or reopen Mode. Missing authority, guards, state, or readback blocks. Then call [Session Audit Resolution](../layer-03-workflow-checkpoints/session-audit-resolution.md) once to resolve audit settings and confirm canonical readback; unavailable prompt, timing, guards, or readback blocks. Apply [Reasoning Summary Visibility](../layer-01-fundamental-concepts/session-runtime/reasoning-summary-visibility.md) at required boundaries. Keep semantic decisions and final acceptance with the input-side phase; an unallocated role is not an independent Session. Confirm boundaries with [Session Model](../layer-01-fundamental-concepts/session-runtime/session-model.md), [Session Role Ownership](../layer-01-fundamental-concepts/session-runtime/session-role-ownership.md), [Session Context Firewall](../layer-01-fundamental-concepts/session-runtime/session-context-firewall.md), and [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md). For Enhanced state, check [Enhanced State Store](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md) and [Enhanced Schema Migrations](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-schema-migrations.md); evaluate [Native Reconciliation](../layer-01-fundamental-concepts/enhanced-native-state/native-reconciliation.md) and [Native Authority Transfer](../layer-01-fundamental-concepts/enhanced-native-state/native-authority-transfer.md) only on trigger, returning authority/readback evidence or `Not applicable`. Use [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md) for audit-field semantics; missing guards/readback blocks.
5. **Capacity reservation only.** After material Native recovery, re-read current allocations before relying on child assignments; do not recreate identities or infer missing history. Confirm the existing Root record and current allocations through the [Enhanced State Store](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md), if selected; Native mode uses the canonical parent-context record. Read only the bounded current state needed. Apply the [Delegation Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md) and [Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md) to confirm the locked positive capacity, current occupied roles, and any genuinely unassigned slots. M05 only preserves and verifies unassigned capacity: do not choose or reserve a role, release a Slice, or create a child. Keep unassigned slots `agent: unbound`, `role: unassigned`, `slice_status: pending`; never recycle a created child's slot. Decide whether Context Bootstrap/Refresh is warranted only after current facts and the Root-authorized proposed task are established in M06–M07; planning that task does not reserve its role. Missing or inconsistent state blocks dependent work; a confirmed capacity shortage proceeds only through the explicit M07 budget gate, never automatic expansion.
6. **Context and transport.** At [Context](../layer-02-workflow-concepts/entry-and-context/context.md), refresh facts affected by material recovery and read only bounded current Root state. Call [Context Source Selection](../layer-03-workflow-checkpoints/context-source-selection.md) for active plans, reusable project Memory, rule lookup, and independently triggered exchange/handoff needs; Map its result to M06: retain sourced current facts, record `Not applicable` with the reason when a conditional source is not triggered, or block dependent work when required context is missing. Call [Decision Context Selection](../layer-03-workflow-checkpoints/decision-context-selection.md) when a downstream advice choice needs reviewed background; stale or unverified context is not sent. For Worker memo/exchange/handoff, follow [Coding Context Exchange](../layer-01-fundamental-concepts/context-exchange/context-exchange.md), [Context Exchange Workspace Boundary](../layer-01-fundamental-concepts/context-exchange/context-exchange-workspace-boundary.md), and [Context Exchange Handoff](../layer-01-fundamental-concepts/context-exchange/context-exchange-handoff.md): use only the record triggered by the task, confirm required persistent-memory evidence, and block dependent work if unavailable; never use file fallback for owner-required persistent records. If no exchange/handoff is triggered, record why. A Context ID never grants Agent-creation rights. For background generation, use [Decision Context Generation](../layer-01-fundamental-concepts/execution-planning/decision-context-generation.md); [Session Context Firewall](../layer-01-fundamental-concepts/session-runtime/session-context-firewall.md), [LSP MCP Tools](../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools.md), and [Enhanced Rule Context](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-rule-context.md) apply only to their stated triggers. Return sourced/fresh facts or block essential gaps. Link [Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md) alongside Decision Context Selection; this is an independent five-node advice gate, and without authorization record `Not applicable` and do not enable it. For Worker memo, link [Content Memo Dispatch](../layer-01-fundamental-concepts/context-exchange/content-memo-dispatch.md) and [Content Memo Lifecycle](../layer-01-fundamental-concepts/context-exchange/content-memo-lifecycle.md) conditionally: confirm Memory evidence when triggered, otherwise record `Not applicable` with the trigger reason. Actual memo dispatch remains in M10. Keep ordinary project Memory and active-plan requirements.
7. **Decision and two-level plan.** Map the L3 decision result to M07; retain the Contract-consistent decision, authorized scope, and unreleased boundary. After material Native recovery, re-evaluate the current Decision and Contract before authorizing a next Slice; do not reopen locked Mode or repeat a completed audit question. At [Decision](../layer-02-workflow-concepts/decision-and-execution/decision.md), state the material question, facts, constraints, options, chosen direction, rejected alternatives, authorized paths/mutations, and unreleased boundary. Apply the [decision gate](../layer-01-fundamental-concepts/execution-planning/execution-decision-gate.md): prepare a concise Decision Brief with Problem, Known facts, Assumptions and unknowns, Decision questions, Solution envelope, Risks, Acceptance, and Stages/checkpoints unless its simple fast path applies; release reconnaissance only while a material choice remains open. Use [execution planning](../layer-01-fundamental-concepts/execution-planning/execution-planning.md) to order bounded inspection, implementation, and focused checks with expected evidence. Confirm the Contract permits one concrete slice before any child assignment or material dispatch.
   - **Lower-owner results.** Under [Task Assignment](../layer-01-fundamental-concepts/execution-planning/task-assignment.md), verify executor and candidate eligibility; independently verify output disposition under [Output Token Routing](../layer-01-fundamental-concepts/execution-planning/output-token-routing.md). Unresolved results block the dependent Slice. When planning intent triggers [Planning Intent Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/planning-intent-plan-memory-lifecycle.md), require persistence and readback evidence; otherwise record `Not applicable` with the reason. Use optional stage advice under [Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md) only when enabled, authorized, relevant, and currently bound; otherwise record inapplicability or decide directly, blocking when required evidence is insufficient.
   - **Planning and Bootstrap decisions.** Call [Planning output selection](../layer-03-workflow-checkpoints/planning-output-selection.md) first; require stored-plan readback evidence or evidence-based `Not applicable`, and block dependent work on failure. After M06 supplies current facts and M07 confirms Decision, Root authorizes the current task scope as the Bootstrap assessment input. Then call [Bootstrap selection](../layer-03-workflow-checkpoints/bootstrap-selection.md): record task/role/slot/Memory facts and trigger/skip evidence, then return a bounded proposed Bootstrap/Refresh task or `Not applicable`; this assessment only recommends and never reserves a role or releases a Slice.
   - **Root-authorized actual task.** After Bootstrap returns its proposed task or `Not applicable`, Root rechecks current Context and Decision and explicitly authorizes the actual task: use the bounded Bootstrap/Refresh task when applicable, otherwise use the original current task. If Bootstrap proposed a distinct auxiliary task, separately review and authorize that task before Executor Selection or role reservation. Bound objective, scope, deliverables, permissions, and unreleased boundary; this task remains distinct from the child-specific Interaction Slice in M08.
   - **Decision advice.** After Root authorization and current context are established, call [Advisory selection](../layer-03-workflow-checkpoints/advisory-selection.md); return current advice review, evidence-based `Not applicable`, or block before using any suggestion.
   - **Executor, output, and role decisions.** After Root authorizes the actual task, call [Executor Selection](../layer-03-workflow-checkpoints/executor-selection.md) and [Output Route Selection](../layer-03-workflow-checkpoints/output-route-selection.md) independently. Record current evidence/results or `Not applicable`. Only when Executor Selection returns `new-executor-needed` and Output Route Selection has dispositioned direct Root output, call [Role Reservation](../layer-03-workflow-checkpoints/role-reservation.md); otherwise record why it is `Not applicable`. Output advice never authorizes creation; no decision here releases a Slice. Only when those role-reservation conditions hold, use [Child Role Selection](../layer-01-fundamental-concepts/delegation/child-role-selection.md), [Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md), [Delegation Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md), and [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md); confirm current role/slot/capacity/state evidence or `Not applicable` with reason, and block on missing or inconsistent required evidence.

8. **Slice and stage release.** Before releasing the next Slice, apply the conditional gate in [Native Reconciliation](../layer-01-fundamental-concepts/enhanced-native-state/native-reconciliation.md): after recovery, require a post-floor `Continue` current for the Control rule and relevant Epochs. If missing or stale, return through the existing Control branch; after `Amend`, recheck Context and Decision before Control. `Stop` blocks. Without a recovery floor, record the gate as `Not applicable` and why. For Enhanced state, persist the concrete Slice only through the typed Root transition using expected Revision and idempotency key; verify the returned state before any child action. Apply [Enhanced State Store](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md) and [Enhanced Schema Migrations](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-schema-migrations.md); do not write through an incompatible store. Native mode updates its canonical parent-context record under the existing record owner. Use [execution control](../layer-01-fundamental-concepts/execution-control/execution-control.md) to state `Objective`, `Authorized scope/mutations`, `Return conditions`, and `Unreleased boundary`; keep dependent writes sequential. Apply [execution stage feedback](../layer-01-fundamental-concepts/execution-control/execution-stage-feedback.md) for high-uncertainty work: predeclare short evidence-producing stages, keep routine mechanics inside a stage, and return compressed Progress Signals only at material boundaries. Route a new semantic choice back to stage 7. Set this allocation's `slice_status: released` only after Context and Decision confirm the task. At this gate classify the released output: only actual code/configuration implementation or authoring/editing this Skill's instructions/reference documents is eligible for child creation; ordinary non-Skill documentation remains parent-authored, including alongside code changes. If no eligible output exists, record `Not applicable` with the reason and keep the reserved slot unbound; do not initialize a child.
   - **Concrete Interaction Slice release.** Release the child-specific Slice only after M06–M07 establish current facts and an authorized task. When a new child is selected, confirm Role Reservation returned a unique role reservation and capacity evidence before M08 release; otherwise block and return to M07. An Output hold alone does not authorize a Slice. Apply the linked Slice owner for objective, scope, paths, and return conditions. If no child Slice applies, record `Not applicable` and why.
9. **Conditional child creation and lifecycle.** Only when step 8 released eligible code/configuration or Skill-document output and M07 returned a current unique role reservation, apply [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md), [Child Creation](../layer-01-fundamental-concepts/delegation/delegation-child-creation.md), and [Runtime and Model Provider Support](../layer-01-fundamental-concepts/session-runtime/runtime-provider-support.md). Confirm the released task/Slice, reserved role/slot, locked or explicitly approved capacity, creation capability, permissions, context, return conditions, and required runtime/effort evidence. Do not reselect or reserve a role at M09; the role decision is complete at M07. Create only the authorized child and record its real identity/allocation. If Enhanced persistence is selected, open the Worker store only after identity binding and compatible schema/guards pass; otherwise record `Not applicable`. Follow [Enhanced State Store](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store.md), [Enhanced Schema Migrations](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-schema-migrations.md), [Child Lifecycle](../layer-01-fundamental-concepts/delegation/delegation-child-lifecycle.md), and [Child Message Visibility](../layer-01-fundamental-concepts/delegation/delegation-child-message-visibility.md) for state, wait, reuse, and actual-body evidence. Never create a replacement child. Missing release, capability, permission, runtime, identity, or schema evidence blocks creation. With no eligible child output, record `Not applicable` and leave the slot unbound. For a new child, confirm creation bindings and effort selection are supported and applicable, then check current slice fingerprint plus input/policy evidence against the runtime owner; missing, stale, or mismatched evidence blocks creation. When using an already created child, record the new-creation check as `Not applicable` and continue to M10; do not require its existing slot to be unbound.
10. **Conditional dispatch, Worker record, and memo.** Only after step 8 released eligible output and step 9 created or resumed the allocated child, apply [Child Dispatch](../layer-01-fundamental-concepts/delegation/delegation-child-dispatch.md), [Worker Boundary](../layer-01-fundamental-concepts/delegation/delegation-worker-boundary.md), and [Content Memo Dispatch](../layer-01-fundamental-concepts/context-exchange/content-memo-dispatch.md). For every bundle, explicitly set `write_content_memo: true | false`; when true, follow [Content Memo](../layer-01-fundamental-concepts/context-exchange/content-memo.md) and [Content Memo Lifecycle](../layer-01-fundamental-concepts/context-exchange/content-memo-lifecycle.md), use the named Worker memo entry, and keep only stable facts/evidence/changed paths. Never store secrets, full transcripts/diffs, or command journals; do not use file fallback for required Memory. When false or no child applies, record why and create no no-op Worker. Preserve logical ownership and do not claim technical isolation. Apply [Child Message Visibility](../layer-01-fundamental-concepts/delegation/delegation-child-message-visibility.md) to every actual message: read the complete actual return before relying on it and display evidence under the configured preset; missing/incomplete bodies or required audit evidence block dependent work. Recheck authorization, released scope, return conditions, and current context for every dispatch/follow-up; child policy owns model/effort and is not repeated after creation.
11. **Conditional Worker implementation and Control.** For an active eligible child slice, at [Implementation](../layer-02-workflow-concepts/decision-and-execution/implementation.md) require the Worker to reread released objective/scope/return conditions, inspect only needed files, make the smallest authorized change, and return changed paths/evidence/issues/unreleased boundary. Load [LSP MCP Tools](../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools.md) only when code structure is needed; record `Not applicable` otherwise and block if required relationships remain unverified. At [Control](../layer-02-workflow-concepts/decision-and-execution/control.md), parent records required status/findings/change/verification/issue/need/boundary evidence and selects an explicit outcome. Reuse the same child for authorized follow-ups; after count locking, do not replace a failed child. Apply [child message visibility](../layer-01-fundamental-concepts/delegation/delegation-child-message-visibility.md) to actual message bodies and configured audit evidence. Call [Advisory selection](../layer-03-workflow-checkpoints/advisory-selection.md) for optional Control advice disposition and direct-owner review. Return to stages 6–11 for another approved slice; Evidence-on-Demand is intermediate only. Apply [Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md) and retain its current eligibility/use evidence or `Not applicable` reason; unauthorized, stale, or failed advice stays disabled.
12. **Final-state verification.** At [Verification](../layer-02-workflow-concepts/verification-and-repair/verification.md), capture current fingerprint and acceptance conditions, then run required holistic and targeted checks. Apply [Verification independence](../layer-02-workflow-concepts/verification-and-repair/verification-independence.md), [Verification reporting](../layer-02-workflow-concepts/verification-and-repair/verification-reporting.md), and [Verification epoch](../layer-02-workflow-concepts/verification-and-repair/verification-epoch.md) for current evidence, dimensions, and changed-epoch boundaries; use the allocated verifier when required. Apply [child message visibility](../layer-01-fundamental-concepts/delegation/delegation-child-message-visibility.md) to verifier request/report bodies and audit evidence. Call [Advisory selection](../layer-03-workflow-checkpoints/advisory-selection.md) for optional Verification/Epoch suggestion disposition; compare suggestions with fingerprints/direct-owner requirements and run required checks. Missing required independence or evidence blocks acceptance. Apply [Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md) and retain its current eligibility/use evidence or `Not applicable` reason; unauthorized, stale, or failed advice stays disabled.
13. **Repair and re-verification.** Map the [Repair disposition](../layer-03-workflow-checkpoints/repair-disposition.md) result to M13 and D_REPAIR. Require concrete failure evidence, affected paths, and the smallest candidate before a narrow repair; no concrete failure is Not applicable only with its evidence basis. This evidence-backed no-failure result returns to M12 to confirm the current epoch. Follow [Repair](../layer-02-workflow-concepts/verification-and-repair/repair.md), [Repair Scope Gate](../layer-02-workflow-concepts/verification-and-repair/repair-scope-gate.md), [Repair Execution](../layer-02-workflow-concepts/verification-and-repair/repair-execution.md), and [Repair Verification Handoff](../layer-02-workflow-concepts/verification-and-repair/repair-verification-handoff.md). A completed authorized repair with handoff and new fingerprint returns to M12 for changed-epoch verification; material Contract change returns to M01, and material Decision change within Contract returns to M07 after confirming Contract remains valid. Reuse the same child when safe; never replace after count locking. Apply [child lifecycle/reuse](../layer-01-fundamental-concepts/delegation/delegation-child-reuse-replacement.md) and [child message visibility](../layer-01-fundamental-concepts/delegation/delegation-child-message-visibility.md); incomplete actual repair messages block handoff. Missing diagnosis, authorization, scope, or handoff blocks.
14. **Parent-owned ordinary documentation.** The root parent authors ordinary non-Skill documentation/comments; this does not consume the child slot. At [Documentation](../layer-02-workflow-concepts/completion-and-effects/documentation.md), confirm approved paths, audience, source evidence, and persistent-knowledge request. Call [Documentation impact](../layer-03-workflow-checkpoints/documentation-impact.md) with before/after fingerprints, affected-dimension evidence, required checks, and evidence reuse; follow its Verification return or block on unknown impact. Synchronize language mirrors and run applicable document checks. Behavior/Contract/acceptance changes return to implementation/content Verification. Skill-document authoring by the child requires parent review; ordinary docs remain parent-owned. Only when approved output includes reusable Agent project knowledge or the user explicitly requests a cross-session note, use [LSP MCP Tools](../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools.md) to save it under the existing name/subdirectory intent and confirm the persisted result; if required capability is unavailable or writing fails, block that requested output. Otherwise record `Not applicable`. Keep repository docs/comments on approved repository paths. Under [Verification Epoch](../layer-02-workflow-concepts/verification-and-repair/verification-epoch.md), confirm affected dimensions, advance changed epochs, and reuse evidence only for dimensions proven unchanged; stale or missing required evidence blocks acceptance.
15. **Git effects.** At [Git](../layer-02-workflow-concepts/completion-and-effects/git.md), confirm exact repository, worktree, branch/ref, remote, operation, and authorization. Inspect status/history, preserve unrelated changes, and confirm staged/committed content matches the latest verified content and documentation fingerprints. Treat index/commit/branch/history changes as Git metadata changes; separately authorize commit, push, Issue, PR, and other effects. Stop on ambiguous target, conflict, missing permission, or unverified content. If no Git work applies, record why. If a Git Worker is used, apply [child message visibility](../layer-01-fundamental-concepts/delegation/delegation-child-message-visibility.md): display the preview or complete safe task body selected by the configured preset, read the complete actual return before reliance, and display according to the configured preset. An actual Git instruction/result body that is unavailable or incomplete, or preset-required visible evidence that is missing, blocks dependent Git work; a concise display selected by the preset does not. If the parent retains the work or no Git Worker is allocated, record Not applicable and why.
16. **Acceptance.** At [Acceptance](../layer-02-workflow-concepts/completion-and-effects/acceptance.md), map each Contract criterion to current evidence for the latest implementation/content, documentation, and Git metadata epochs. Check paths/effects against scope and report passed, failed, not-run, unavailable, assumed, and user-authorized items separately with residual risks. If this route has an active plan Memory confirmed to belong to the task being completed, apply [Planning Intent Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/planning-intent-plan-memory-lifecycle.md) to archive it under the matching archive name and verify the active name is absent and archive is readable; block completion if required archive/verification fails. If no matching active plan belongs to the task being completed, record `Not applicable` and why. Report `COMPLETE` only when every required item and boundary is resolved. Apply [Verification Epoch](../layer-02-workflow-concepts/verification-and-repair/verification-epoch.md) to confirm evidence remains current for accepted fingerprints and changed dimensions.

For each released Worker bundle in stages 8–10, make these fields explicit:

```text
Owner: Primary Output | Documentation/Comments & Git Operations | Change Verification
Objective: ...
Authorized scope/mutations: ...
write_content_memo: true | false
Return conditions: ...
Unreleased boundary: ...
```

## Completion

Apply the root Coding completion gate for documentation, Git, and final acceptance. The final report must distinguish real independent Sessions from same-Session logical phases and map every acceptance criterion to current evidence.
## Related concepts

- [Shared protocols](../../share/shared-protocols.md) — locate common Session conventions.
- [Session role ownership](../layer-01-fundamental-concepts/session-runtime/session-role-ownership.md) — locate parent and Worker responsibilities.
