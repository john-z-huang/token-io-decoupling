# Workflow Module Migration Coverage

[English](WORKFLOW_MODULE_MIGRATION.md) | [简体中文](WORKFLOW_MODULE_MIGRATION_zh_cn.md)

This development record explains the migration from the complete, repeated Layer-04 route checklists at baseline `675627dc` to reusable module contracts and seven-step route composition. It is not loaded by the Coding runtime and does not grant authority. The routes remain authoritative for module order and continuation; each module remains authoritative for its lower-layer checks.

The machine-readable old-step, semantic substep, owner-chain, and new-checkpoint mapping is maintained in [workflow-module-migration.json](docs/workflow-module-migration.json). The validator checks coverage against actual module checklist checkpoints and links; this development-only manifest is not a runtime route or authorization source.

## Route composition

| Route checkpoint | Module | Route-owned responsibility |
| --- | --- | --- |
| SM01 / MM01 | [Entry Readiness](docs/skill/references/coding/layer-04-workflows/modules/entry-readiness.md) | Confirm released Contract, Environment/capability, and mode evidence. |
| SM02 / MM02 | [Session Readiness](docs/skill/references/coding/layer-04-workflows/modules/session-readiness.md) | Complete canonical state/readback, then audit; Multi-Agent also confirms capacity. |
| SM03 / MM03 | [Work Definition](docs/skill/references/coding/layer-04-workflows/modules/work-definition.md) | Current context, decision, planning; Multi-Agent Bootstrap and role/executor decisions belong to its execution module. |
| SM04 | [Single-Agent Execution](docs/skill/references/coding/layer-04-workflows/modules/single-execution.md) | Single-Agent executor, bounded Slice, implementation, feedback, and Control. |
| MM04 | [Delegated Execution](docs/skill/references/coding/layer-04-workflows/modules/delegated-execution.md) | Multi-Agent shared Slice gate, conditional role-bound child lifecycle, implementation/result, and Control. |
| SM05 / MM05 | [Verification and Repair](docs/skill/references/coding/layer-04-workflows/modules/verification-repair.md) | Current-state verification; repair and changed-epoch loop. |
| SM06 / MM06 | [Documentation](docs/skill/references/coding/layer-04-workflows/modules/documentation.md) | Applicable documentation/Memory output, readback, impact, checks, and return to Verification when required. |
| SM07 / MM07 | [Delivery and Acceptance](docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md) | Authorized Git effect, criterion mapping, and conditional plan archive after passing Acceptance. |

Modules are independently enterable when their declared work and effects are covered by existing user authorization and their entry declarations are satisfied; no separate module-name authorization is required. The complete route still requires all route prerequisites and acceptance. A suspended module returns its exact owner and continuation position; the route resumes there without replaying completed effects. State, effect, or epoch changes route only to the affected checkpoint. Modules do not invoke sibling modules.

## Single-Agent legacy coverage

The `S` labels below refer to numbered checklist steps in the baseline route, not the new `SM01`…`SM07` route IDs. Each row preserves the old semantic substep and points to its new module checkpoint. “Direct” means the module checklist calls the owner; “transitive” means a called Layer-03 owner composes that lower owner. The module link is the maintained current location.

| Baseline step/substep and owner | New checkpoint and consumption |
| --- | --- |
| S01 Contract; shared protocols; intent/output preclassification | SM01 → ER01; ER00 entry. Contract gate is pre-route evidence; Semantic Contract and return protocol stay caller-owned. |
| S02 Environment, capability inventory, Enhanced path/availability/host binding | SM01 → ER02, direct through Enhanced Path Selection. |
| S03 Mode confirmation/count/state/re-entry | SM01 → ER03, direct through released route evidence. |
| S04 Session state, authority, Context Firewall, audit, visibility, role boundaries, migrations/reconciliation/transfer | SM02 → SR01–SR04. SR02 directly calls Session State Resolution; its owner chain transitively covers identity, authority, schema, reconciliation, transfer, and readback. SR03 directly calls audit resolution, audit visibility, reasoning-summary visibility and state-record owner. SR04 conditionally confirms capacity. |
| S05 Context source selection, plan/memory/rule lookup, reconnaissance, context generation | SM03 → WD01, direct Context Source Selection and conditional Decision Context Selection. |
| S06 Decision, Decision Brief, execution planning, task assignment, output route, planning Memory, optional advice | SM03 → WD02–WD03 for Decision and planning output. Executor/output dispositions consumed for execution are separately checked at SM04 → SE01. Planning lifecycle is direct; contextual owner chains are transitive through WD. |
| S07 implementation and code-structure evidence | SM04 → SE02–SE03; implementation direct, code-structure evidence conditionally direct. |
| S08 stage feedback | SM04 → SE04, direct with explicit trigger/N/A disposition. |
| S09 Control and Control advice | SM04 → SE05, direct Control/Execution Control/Advisory Selection and Decisions Advisory; next-Slice continuation returns to the same module checkpoints. |
| S10 final fingerprint, verification, independence/reporting/epochs/advice | SM05 → VR01–VR04; current passing Verification returns through VR06. Verification, Reporting, Independence and Epoch are directly consumed; advice is conditional. |
| S11 repair disposition, scope gate, repair, execution, handoff, re-verification | SM05 → VR05; disposition is direct, repair owners are direct and ordered; handoff returns to VR01, and current Verification passes before VR06 returns the result. |
| S12 documentation, impact, Memory, checks, changed-epoch evidence | SM06 → DOC01–DOC06; documentation, Memory/readback, impact classification and checks are direct. Content-affecting changes return to SM05. |
| S13 Git target/effect/authorization and fingerprint match | SM07 → DA02, direct Git owner; divergence returns to SM05 before additional Git effects. |
| S14 Acceptance criterion map, residual risks and plan archive/readback | SM07 → DA03–DA05; Acceptance/Epoch direct; matching plan archive only after all applicable criteria pass. This is distinct from baseline Multi-Agent M07 Decision/Bootstrap work. |

## Multi-Agent legacy coverage

The `M` labels here refer to baseline checklist steps. Detailed conditional branches stay with their current owners, while the following map records where the old operation is consumed now.

| Baseline step/substep and owner | New checkpoint and consumption |
| --- | --- |
| M01 Contract, shared protocol, dispatch boundary | MM01 → ER01 plus pre-route Contract evidence. Dispatch rules are consumed later by MM04. |
| M02 Environment, capability inventory, Enhanced selection/host | MM01 → ER02; Enhanced owners are direct/conditional through Enhanced Path Selection. |
| M03 Mode/count/state/re-entry and reserved-slot state | MM01 → ER03; route/count release only, not child authorization. |
| M04 Session identity/authority, Context Firewall, audit, visibility, Native/Enhanced transfer and readback | MM02 → SR01–SR03; SR02's Session State Resolution owner chain transitively consumes these; SR03 consumes audit and safe-summary owners after state readback. |
| M05 capacity/allocation read-only confirmation | MM02 → SR04; direct capacity gate and allocation check, no role reservation. |
| M06 bounded Context, sources, transport, reusable Memory, handoff/exchange | MM03 → WD01; Context source and decision-context owners directly/conditionally consumed. Worker exchange-specific owners remain conditional and are invoked only by later module operations where applicable. |
| M07 Decision and two-level plan; planning Memory; Bootstrap proposal; actual-task authorization; advice; executor/output/role decision | MM03 → WD02–WD03 for Decision/planning/advice and the unreleased boundary. Bootstrap, actual-task authorization, executor/output/role, and Slice release are owned at MM04 → DE01–DE04. This Decision/Bootstrap checkpoint is not the later Acceptance/plan-archive checkpoint at baseline M16. |
| M08 Slice/stage release, recovery Continue, Control rule/epochs, Native/Enhanced persistence | MM04 → DE04, direct Execution Control/Planning/Native Reconciliation; typed persistence/readback is conditional/transitive through state owners. |
| M09 conditional child creation, runtime/effort binding, identity/allocation, reuse | MM04 → DE05, direct Child Creation and Runtime/Model owner; store/schema operations conditional. |
| M10 dispatch, Worker boundary, message visibility, memo field and memo lifecycle | MM04 → DE06; direct dispatch/lifecycle/memo owners. Existing bundle value is resumed; new bundle value is set at DE04 and retained here. |
| M11 implementation, LSP evidence, stage feedback, Control, follow-up/reuse | MM04 → DE07–DE08; implementation and feedback are direct; Control/Advisory are direct at DE08. Pending child resumes at DE07; next Slice returns through DE08 and DE04 without replaying effects. |
| M12 final-state verification, independence, reporting, epochs, advice and child-body visibility | MM05 → VR01–VR04; current passing Verification returns through VR06; verification owners direct, message visibility applies conditionally to verifier exchange. |
| M13 repair diagnosis/disposition, scope, execution, handoff and changed-epoch verification | MM05 → VR05 then VR01; repair owners direct and ordered; current Verification passes before VR06 returns the result. |
| M14 parent-owned docs, docs impact, project Memory, checks and epoch reuse | MM06 → DOC01–DOC06; no child receives ordinary non-Skill docs. Content-affecting changes return MM05. |
| M15 Git target/effects/authorization, fingerprints, message visibility if a Git Worker | MM07 → DA02, direct Git owner; Worker message visibility is only conditional when that role is used. |
| M16 Acceptance criteria/epochs, residual risks, matching active plan archive/readback | MM07 → DA03–DA05; plan archive occurs only after every applicable criterion has current passing evidence. This is distinct from baseline M07 Decision/Bootstrap work now at MM03. |

## Cross-module return and epoch coverage

| Event | Route continuation |
| --- | --- |
| Missing prerequisite | Preserve the module's returned owner and exact suspended checkpoint; after resolution, resume that checkpoint. Do not replay earlier module effects. |
| Session recovery/material state change | SM02/MM02 completes current canonical readback before audit/capacity evidence is reused; route module continuation then proceeds at its recorded position. |
| Control Amendment or next Slice | Return to the same execution module Control checkpoint; update required Contract/Decision/Context; verify prior Continue still covers the bounded Slice and current state/epochs before resuming execution. |
| Verification repair | Return through repair handoff to current fingerprint capture and required checks; rerun only dimensions invalidated by changed epochs. |
| Documentation content/Contract/acceptance impact | Return from SM06/MM06 to SM05/MM05 for affected current Verification; do not proceed to delivery until current evidence passes. |
| Git/content fingerprint divergence | Return from SM07/MM07 to the affected Verification dimension before any further Git effect or Acceptance. |
| Acceptance plan archive | Archive/read back only a matching completed plan after all required criteria pass; failed, missing, unavailable, or unknown required evidence cannot reach archive. |

This coverage is a migration aid, not an additional runtime policy source. The route and module files linked above are the current executable documentation.
