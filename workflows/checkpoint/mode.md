sed: --: No such file or directory
# Execution Mode Checkpoint

[English](mode.md) | [简体中文](mode_zh_cn.md)

## Actions

1. Load and follow [`../../references/coding/agent-delegation-control.md`](../../references/coding/agent-delegation-control.md), the sole authority for mode confirmation and delegation state.
2. Record that authority document's current gate outcome before route selection. If it has not released the route, stop at this checkpoint and do not proceed.
3. If a new root directive changes delegation, return to the authority document and record its new outcome before continuing. This checkpoint does not restate or replace that document's creation, allocation, reuse, exception, or count rules.

## Pass condition

The authority document has recorded exactly one valid mode outcome and any required delegation state; the selected route's required capabilities and prohibitions are satisfied.

## Boundary

This checkpoint only navigates to and records the outcome of the delegation authority document. It does not independently decide mode, topology, creation, allocation, reuse, exceptions, or count.
