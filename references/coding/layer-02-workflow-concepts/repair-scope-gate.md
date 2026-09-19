# Repair Scope Gate

[English](repair-scope-gate.md) | [简体中文](repair-scope-gate_zh_cn.md)

This checkpoint owns the compatibility and authorization gate for a proposed repair. It consumes a diagnosed repair candidate; it does not diagnose failures, execute repairs, or define Verification epochs.

## Contract and Decision compatibility

1. Confirm that the proposed repair remains inside the approved Contract and Decision.
2. If it changes scope, architecture, security, compatibility, or another material decision, pause and return to Contract and Decision before authorizing execution.

## Pass condition

The proposed repair is explicitly authorized within the approved boundary, or the required Contract, Decision, or capability is named before execution.

## Boundary

This checkpoint does not diagnose failure evidence, choose repair content, execute repairs, run focused checks, or create Verification epochs.

## Related concepts

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate.md) — locate material decision and release-condition ownership.
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control.md) — locate approved scope and mutation boundaries.
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary.md) — locate parent-controlled authorization boundaries.
