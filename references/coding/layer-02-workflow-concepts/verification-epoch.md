# Verification Epoch Checkpoint

[English](verification-epoch.md) | [简体中文](verification-epoch_zh_cn.md)

This checkpoint owns epoch invalidation by covered state dimension. A later change advances only the dimension whose verified coverage it changes; earlier evidence remains valid for unaffected dimensions. It does not define check contents, independent Sessions, result classification, or repair.

## Actions

1. Track three dimensions: implementation/content, documentation, and Git metadata.
2. Advance the implementation/content epoch when implementation, configuration, tests, or other content covered by product verification changes; invalidate earlier product verification for that changed content.
3. Advance the documentation epoch when maintained documentation or comments change. Run the applicable Markdown, link, whitespace, multilingual, and scope checks. If the change alters executable content, the Contract, or acceptance conditions, also treat it as an implementation/content change and return to implementation Verification.
4. Advance the Git metadata epoch when commit, branch, index, or history state changes. Do not advance the implementation/content or documentation epoch for Git metadata operations alone. Git state still requires the Git checkpoint to confirm that staged or committed content matches the latest verified fingerprints; content divergence or unverified content returns to the corresponding Verification epoch.
5. Do not use evidence from an earlier epoch for an affected dimension; require the applicable checks or Verification for the new epoch.

## Pass condition

The latest applicable implementation/content, documentation, and Git metadata epochs are explicit, their required checks or Verification are queued or complete, and no affected dimension relies on stale evidence.

## Boundary

This checkpoint does not capture fingerprints, choose checks, define independent verification, classify results, authorize repairs, write documentation, or perform Git effects.

## Related concepts

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate material state-boundary ownership.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate final-state evidence access.
- [Coding Child Reuse and Replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement.md) — locate repaired-epoch reuse ownership.
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate dependent-release conditions.
