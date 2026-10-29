# Output route selection

[English](output-route-selection.md) | [简体中文](output-route-selection_zh_cn.md)

This checkpoint owns the independent assessment of whether each requested direct Root output should route away from Root under [Output Token Routing](../layer-01-fundamental-concepts/execution-planning/output-token-routing.md). It does not select an executor.

## Trigger and inputs

At S06/M07, assess each requested direct Root output by its shape, expected output volume, explicit user direction, locked mode, and current verified facts. Check explicit direction before advice. Do not use unrelated input/transcript size or an arbitrary numeric threshold.

## Decision and result

1. If explicit user instruction settles who produces the output or whether it is produced, record that direction and skip only its corresponding advice; all other gates remain active.
2. Otherwise return `yes`, `no`, `insufficient_evidence`, or `failed` per output, with the evidence and current input/context/policy hashes. A stale input or policy-hash mismatch is unresolved, never `no`.
3. `yes` means Root should route the large output away from direct materialization. In Single-Agent mode, hold and report the topology boundary. In Multi-Agent mode, use a suitable idle current-Session child or wait/hold until one is idle. `no` permits Root to continue subject to all other gates.
4. Keep this result independent from executor selection. A `yes` alone does not authorize creating a child. Only a separately established need for a new executor can proceed to role/capacity, Slice, and creation gates in order.
5. Return the per-output result and evidence to route scheduling; do not release a Slice or dispatch here.

## Failure boundary

Insufficient facts, stale or mismatched hashes, failed advice, or conflicting output evidence returns unresolved. Review the direct owner from verified facts only when they suffice; otherwise block. Never default to `no`, create for output size alone, or bypass the locked-mode boundary.

## Related concepts

- [Output Token Routing](../layer-01-fundamental-concepts/execution-planning/output-token-routing.md)
- [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record.md)
- [Delegation Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md)
