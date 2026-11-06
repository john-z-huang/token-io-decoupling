# Documentation impact

[English](documentation-impact.md) | [简体中文](documentation-impact_zh_cn.md)

This checkpoint owns route-level impact classification and return routing after documentation/content changes.


## Trigger and inputs

After Documentation or an approved content change, determine whether implementation/content, documentation, or Contract evidence changed. Apply [Documentation](../layer-02-workflow-concepts/completion-and-effects/documentation.md) and [Verification Epoch](../layer-02-workflow-concepts/verification-and-repair/verification-epoch.md).

## Decision and result

1. Capture before/after fingerprints and classify each affected dimension: implementation/content, documentation, Git metadata, or multiple. Attach evidence for each classification.
2. Name required checks, evidence that remains reusable, and why each unaffected dimension is unchanged. A no-change result is `Not applicable` with fingerprint evidence.
3. Re-verify changed dimensions. If content changes behavior, Contract, or acceptance, return the evidence to implementation/content Verification; if only documentation changed, return documentation checks and unaffected-dimension rationale.
4. Return the classification, fingerprints, checks, reuse rationale, and Verification disposition to route scheduling.

## Failure boundary

Unknown impact, missing required checks, or stale evidence blocks Acceptance. Preserve the affected/unaffected dimension reasoning and permitted output scope; do not reuse evidence across a changed epoch.

## Related concepts

- [Documentation](../layer-02-workflow-concepts/completion-and-effects/documentation.md)
