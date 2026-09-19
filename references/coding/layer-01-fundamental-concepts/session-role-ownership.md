# Coding Session Role Ownership

[English](session-role-ownership.md) | [简体中文](session-role-ownership_zh_cn.md)

This module owns the responsibilities of the Coding architecture roles: Input-side Reasoning, Primary Output, Context Bootstrap/Refresh, Change Verification, and Documentation/Comments & Git Operations. It does not define Session semantics, role allocation, Context Firewall policy, or final workflow acceptance.

## Input-side Reasoning Agent

Owns user-intent and business-semantic analysis, the Semantic Contract, architecture and risk decisions, unresolved trade-offs, stage and slice boundaries, release decisions, checkpoint outcomes, user interaction, and final semantic acceptance. It may request evidence and candidate options, but decides what they mean and must not absorb high-volume raw project state or expand already-approved decisions into long output.

## Primary Output Role

Owns high-volume project exploration, evidence compression, execution inside an approved direction, code/configuration materialization, repairs within the released slice, and provisional implementation checks. It reads progressively, cannot change unresolved goals, constraints, architecture, or acceptance criteria, and does not own final acceptance or non-trivial Git work.

## Context Bootstrap/Refresh Responsibility

When assigned, builds or refreshes a bounded, fingerprinted capsule of neutral project facts, exact source pointers, policy-routing pointers, and freshness data. It does not decide the task, change the Contract, implement, verify, materialize documentation, or delegate recursively. The capsule supplements mandatory instructions and never replaces direct reading of authoritative files.

## Change Verification Agent

When assigned, independently verifies the final state of a material change against the Contract and acceptance criteria. It uses the supplied scope evidence, runs relevant holistic and targeted checks, re-evaluates every final-state fingerprint/epoch, and reports evidence, gaps, failures, and risks. It is read-only for product code/configuration, documentation, and Git, except for explicitly named verification assets; it does not repair, make semantic decisions, or delegate.

## Documentation/Comments & Git Operations Agent

When assigned, materializes only approved documentation/comments or performs only the explicitly released non-trivial Git slice. It does not change product behavior, tests, or semantic decisions; a conflict requiring new content or meaning returns to the parent. Documentation and Git work remain separate execution scopes.

## Related concepts

- [Coding Session Model](session-model.md) — locate Session semantics and affinity.
- [Coding Session Context Firewall](session-context-firewall.md) — locate raw-state ingress ownership.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate role allocation ownership.
- [Coding Delegation State Record](delegation-state-record.md) — locate task-control state ownership.
- [Coding Execution Control](execution-control.md) — locate stage and slice boundary ownership.
