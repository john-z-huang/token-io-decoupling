# Documentation Module

[English](documentation.md) | [简体中文](documentation_zh_cn.md)

This Layer-04 module writes only authorized documentation/comments or requested reusable project knowledge against a current verified state, then classifies post-write impact by affected dimension. It does not perform final Verification, decide semantic changes, or authorize Git effects.

## Entry declaration

| Field | Requirement |
| --- | --- |
| Entry prerequisites | The applicable Single-Agent or Multi-Agent Mode gate has released current evidence; current Session identity and authority are confirmed; the caller continuation and completed effects are known, with no unresolved effect ambiguity. |
| Required inputs | Current Contract and scope, current implementation/content Verification for the state under consideration, and before fingerprints. Approved paths, audience, purpose, source evidence, and writer/role authorization are required when a documentation, comment, or Memory output applies. |
| Permitted effects | Edit the released documentation/comment paths; conditionally persist specifically requested or triggered reusable project Memory; run applicable documentation checks and impact classification. Ordinary non-Skill documentation remains parent-authored. |
| Results | `complete` with current documentation epoch, checks, before/after fingerprints, affected/unaffected dimensions, and any reusable Memory write/readback result; otherwise `needs_prerequisite` or `blocked` with the required owner and continuation. |
| Freshness | Bind the source verification and documentation result to current fingerprints and applicable epochs. A post-write change invalidates only affected dimensions; executable-content, Contract, or acceptance changes also invalidate implementation/content evidence. |

## Workflow map

```mermaid
flowchart TD
    DOC00["DOC00 Resolve module entry"]
    DOC01["DOC01 Confirm current verified state and approved documentation scope"]
    D_PREFLIGHT{"Is an authorized pre-write candidate check selected?"}
    DOC_PREFLIGHT["Check exact documentation candidate against current trusted baseline"]
    DOC_PREFLIGHT_NA["not_applicable: no selected candidate-preflight branch; reason recorded"]
    DOC_NEEDS_PREFLIGHT["needs_prerequisite: resolve candidate/scope/baseline/preflight; resume DOC02"]
    DOC02["DOC02 Author approved documentation/comments or record evidenced no-op"]
    D_MEMORY{"Requested project Memory or reusable-knowledge trigger?"}
    DOC03["DOC03 Persist authorized project Memory and confirm operation"]
    D_MEMORY_VERIFY{"Does the applicable owner require stored-content verification?"}
    DOC_MEM_VERIFY["Complete owner-required verification with matching evidence or content comparison"]
    DOC_MEM_VERIFY_NA["not_applicable: no owner-triggered stored-content check; reason recorded"]
    DOC04["DOC04 Classify post-write impact and advance affected epochs"]
    DOC05["DOC05 Run current documentation checks and justify unaffected-dimension reuse"]
    DOC06["DOC06 Return documentation result and route affected verification"]
    DOC_NEEDS["needs_prerequisite: obtain current Verification or approved scope"]
    DOC_NEEDS_IMPL["needs_prerequisite: return behavior/Contract/acceptance impact to implementation Verification"]
    DOC_NEEDS_MEM["needs_prerequisite: Memory capability, persistence, or required verification unavailable/failed"]
    DOC_BLOCK["blocked"]
    DOC_MEM_NA["not_applicable: no requested or triggered Memory output"]
    DOC_OUTPUT_NA["not_applicable: no output applies, or authorized output produced no change; matching fingerprints required"]
    DOC00 -- ready --> DOC01
    DOC00 -- missing evidence --> DOC_NEEDS
    DOC00 -- conflict or unsafe state --> DOC_BLOCK
    DOC01 -- output applies; current Verification and approved scope/authority --> D_PREFLIGHT
    DOC01 -- no output applies; current Verification and unchanged before/after fingerprints --> DOC_OUTPUT_NA
    DOC01 -- Verification stale/missing or scope incomplete --> DOC_NEEDS
    DOC01 -- requested/triggered output lacks required authorization/path/source --> DOC_NEEDS
    DOC01 -- ordinary docs assigned to child or unauthorized writer --> DOC_BLOCK
    D_PREFLIGHT -- selected; exact candidate, scope and trusted baseline current --> DOC_PREFLIGHT
    D_PREFLIGHT -- not selected/no applicable candidate; record reason --> DOC_PREFLIGHT_NA
    D_PREFLIGHT -- selected but candidate, scope, or baseline missing --> DOC_NEEDS_PREFLIGHT
    DOC_PREFLIGHT -- all selected structural checks pass --> DOC02
    DOC_PREFLIGHT -- selected check fails, is unknown, omitted, or stale --> DOC_NEEDS_PREFLIGHT
    DOC_PREFLIGHT_NA --> DOC02
    DOC02 -- source-based edit or evidenced no-op complete --> D_MEMORY
    DOC02 -- material meaning needs decision --> DOC_NEEDS_IMPL
    D_MEMORY -- requested or triggered reusable Memory --> DOC03
    D_MEMORY -- no such output --> DOC_MEM_NA
    DOC03 -- write operation succeeded --> D_MEMORY_VERIFY
    D_MEMORY_VERIFY -- no stored-content check required; record N/A --> DOC_MEM_VERIFY_NA
    D_MEMORY_VERIFY -- owner requires stored-content verification --> DOC_MEM_VERIFY
    DOC_MEM_VERIFY -- matching verified evidence or content comparison passes --> DOC04
    DOC_MEM_VERIFY -- required verification fails, is unavailable, or outcome is uncertain --> DOC_NEEDS_MEM
    DOC03 -- required capability or write fails --> DOC_NEEDS_MEM
    DOC_MEM_VERIFY_NA --> DOC04
    DOC_MEM_NA --> DOC04
    DOC_OUTPUT_NA --> D_MEMORY
    DOC04 -- only documentation dimension changed or matching no-change fingerprints --> DOC05
    DOC04 -- executable content/Contract/acceptance changed --> DOC_NEEDS_IMPL
    DOC04 -- impact unknown --> DOC_BLOCK
    DOC05 -- applicable checks pass; unaffected dimensions justified --> DOC06
    DOC05 -- required documentation check fails or unavailable --> DOC_BLOCK
```

## Ordered module checklist

1. **DOC00 — Resolve entry.** Call [Module Entry Resolution](../../layer-03-workflow-checkpoints/module-entry-resolution.md) with current Contract/scope, applicable implementation/content Verification, current epochs, known effects and before fingerprints, and continuation. Include approved paths, audience, purpose, source evidence, and writer authorization only when an output applies. Missing required evidence returns `needs_prerequisite`; contradictory scope, unsafe state, or unauthorized effects return `blocked`.
2. **DOC01 — Confirm current state and determine applicable output.** Apply [Documentation](../../layer-02-workflow-concepts/completion-and-effects/documentation.md) and [Session Role Ownership](../../layer-01-fundamental-concepts/session-runtime/session-role-ownership.md). Confirm current Contract/scope, applicable implementation/content Verification, and before fingerprints. First decide from current Contract/user intent and owner triggers whether documentation, comments, or reusable project Memory output applies. For applicable output, require exact approved paths, audience, purpose, sources, and writer/role authorization; missing required authorization/path/source returns `needs_prerequisite` or `blocked`, never `not_applicable`. Ordinary non-Skill documentation/comments remain parent-authored. A child may author/edit Skill instructions or references only after all release gates; the parent reviews that result at Documentation and Acceptance. If required current Verification is absent or stale, return to Verification.
3. **DOC02 — Author approved output or record an evidenced no-op.** For an authorized documentation candidate, first determine whether the optional candidate-preflight branch is genuinely selected and applicable. When selected, prepare the exact bounded candidate and capture the trusted current baseline, then run [Candidate Compliance Preflight](../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md) on that pair before applying the candidate. If the selected branch lacks a candidate or baseline, return `needs_prerequisite` at DOC02 until it is prepared; do not mark the selected branch `not_applicable`. Use the Skill-maintenance scope only for Skill maintenance; use the generic project scope otherwise. Resolve every selected failed, unknown, omitted, truncated, or stale result before applying the candidate. Only when the branch is genuinely unselected or its trigger is absent/inapplicable, record `not_applicable` with why and continue under the authorized direct documentation path. A passing preflight is limited candidate evidence; it cannot replace DOC05's post-write checks, semantic mirror review, or current Verification. Edit only authorized Markdown/comment paths using verified sources; keep required English/Chinese mirrors aligned. Do not encode behavior, policy, Contract, acceptance, scope, or Git changes as documentation. Return a material semantic choice to the caller's Contract/Decision path. If no output applies, or authorized output has no actual difference, record `not_applicable` only with matching before/after fingerprints. Preserve already completed effects so resumption does not replay them.
4. **DOC03 — Persist only authorized project Memory.** If the user requested reusable Agent project knowledge or an owner-defined trigger applies, use [LSP MCP Tools](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools.md), [Content Memo](../../layer-01-fundamental-concepts/context-exchange/content-memo.md), and [Content Memo Lifecycle](../../layer-01-fundamental-concepts/context-exchange/content-memo-lifecycle.md) as applicable: retain the authorized name/path, write through the exposed Memory capability, and confirm the operation succeeded. Perform stored-content verification only when the applicable owner requires it; use its matching verified evidence when available, or perform the necessary content comparison. A normal successful write does not trigger an immediate full readback. A `write_content_memo: false` dispatch value does not establish that project Memory is not applicable. If no project Memory output was requested or triggered, record `not_applicable` with reason. If required capability, write, or owner-required verification is unavailable or fails, keep the requested output incomplete; do not use a file as fallback.
5. **DOC04 — Classify post-write impact.** Apply [Documentation Impact](../../layer-03-workflow-checkpoints/documentation-impact.md) and [Verification Epoch](../../layer-02-workflow-concepts/verification-and-repair/verification-epoch.md) with before/after fingerprints, after any requested Memory write and any owner-required content verification. Advance the documentation epoch for actual maintained docs/comments/Memory changes. If fingerprints match and no output changed, do not advance the epoch and record `not_applicable` with evidence. Advance only affected dimensions and preserve evidence for unaffected dimensions. If executable content, Contract, or acceptance conditions changed, also classify implementation/content impact and return it to current Verification. Unknown impact blocks.
6. **DOC05 — Run documentation checks and assess evidence reuse.** Run applicable Markdown, link, whitespace, multilingual, and scope checks after all documentation and Memory writes. For documentation-only impact, retain unaffected current evidence only with a fingerprint rationale and rerun changed documentation checks. With no changed output, record checks `not_applicable` with matching fingerprints. Behavior/Contract/acceptance impact returns for implementation/content Verification; do not complete while required re-verification is unresolved.
7. **DOC06 — Return documentation evidence.** Return changed paths, source basis, current documentation fingerprint/epoch, checks and results, before/after dimension classification, rationale for reused unaffected evidence, and any Memory result or reasoned `not_applicable`. Complete only when all applicable checks pass or are justified `not_applicable`, Memory persistence is confirmed and any owner-required stored-content verification passes or is justified `not_applicable`, and all content-affecting re-verification has a resolved continuation/result. This does not authorize Git or overall Acceptance.

## Related concepts

- [Documentation](../../layer-02-workflow-concepts/completion-and-effects/documentation.md)
- [Documentation Impact](../../layer-03-workflow-checkpoints/documentation-impact.md)
- [Verification Epoch](../../layer-02-workflow-concepts/verification-and-repair/verification-epoch.md)
