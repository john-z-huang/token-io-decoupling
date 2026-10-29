# Repair disposition

[English](repair-disposition.md) | [简体中文](repair-disposition_zh_cn.md)

This checkpoint owns route-level recovery and re-verification routing after failure or a material decision change.


## Trigger and inputs

After a failed current Verification or a material decision change, use this checkpoint to route recovery. Apply [Repair](../layer-02-workflow-concepts/verification-and-repair/repair.md), [Repair Scope Gate](../layer-02-workflow-concepts/verification-and-repair/repair-scope-gate.md), [Repair Execution](../layer-02-workflow-concepts/verification-and-repair/repair-execution.md), and [Repair Verification Handoff](../layer-02-workflow-concepts/verification-and-repair/repair-verification-handoff.md).

## Decision and result

1. Require concrete failing evidence, affected paths, and the smallest repair candidate. A semantic change without a concrete failure is not a Repair; route it as a material decision change.
2. Apply the Repair scope gate against the current Contract and Decision. Release only the authorized narrow repair and its focused checks.
3. Capture the repair handoff, new fingerprint, and affected epochs; send current evidence to Verification and re-run every required check for changed epochs before dependent work.
4. A material decision change returns to S01/S06 or M01/M07 for route scheduling. Without a concrete failure, return Repair `Not applicable` and the evidence basis.

## Failure boundary

Missing diagnosis, authorization, bounded scope, handoff evidence, or changed-epoch re-verification blocks the dependent route. Do not treat repair intent as authorization or reuse stale pass evidence.

## Related concepts

- [Repair Scope Gate](../layer-02-workflow-concepts/verification-and-repair/repair-scope-gate.md)
