# Coding Session Model

This module defines Coding role ownership, Session semantics, the Context Firewall, and Primary Execution Session affinity. It is independent of runtime/model eligibility, execution parameters, dispatch formatting, context-file transport, and acceptance procedures.

## Architecture roles

### Input-side Reasoning Agent

Owns user-intent and business-semantic analysis, the Semantic Contract, architecture and risk decisions, unresolved trade-offs, stage and slice boundaries, release decisions, checkpoint outcomes, user interaction, and final semantic acceptance. It may request evidence and candidate options, but decides what they mean and must not absorb high-volume raw project state or expand already-approved decisions into long output.

### Primary Output Role

Owns high-volume project exploration, evidence compression, execution inside an approved direction, code/configuration materialization, repairs within the released slice, and provisional implementation checks. It reads progressively, cannot change unresolved goals, constraints, architecture, or acceptance criteria, and does not own final acceptance or non-trivial Git work.

### Context Bootstrap/Refresh Responsibility

When assigned, builds or refreshes a bounded, fingerprinted capsule of neutral project facts, exact source pointers, policy-routing pointers, and freshness data. It does not decide the task, change the Contract, implement, verify, materialize documentation, or delegate recursively. The capsule supplements mandatory instructions and never replaces direct reading of authoritative files.

### Change Verification Agent

When assigned, independently verifies the final state of a material change against the Contract and acceptance criteria. It uses the supplied scope evidence, runs relevant holistic and targeted checks, re-evaluates every final-state fingerprint/epoch, and reports evidence, gaps, failures, and risks. It is read-only for product code/configuration, documentation, and Git, except for explicitly named verification assets; it does not repair, make semantic decisions, or delegate.

### Documentation/Comments & Git Operations Agent

When assigned, materializes only approved documentation/comments or performs only the explicitly released non-trivial Git slice. It does not change product behavior, tests, or semantic decisions; a conflict requiring new content or meaning returns to the parent. Documentation and Git work remain separate execution scopes.

## Session semantics

The active workflow supplies mode, topology, role allocation, lifecycle, reuse, replacement, exceptions, and unavailable handling. A role label never authorizes a new Session or topology change.

In Single-Agent Coding, the current Session performs the logical decision, implementation, documentation, Git, and allowed-check phases; logical roles do not imply independent Agents. In Multi-Agent Coding, use only the independent Sessions explicitly supplied by the active workflow:

```text
root parent Session → Input-side Reasoning
assigned Primary Session → Primary Output
assigned verifier Session → Change Verification
assigned docs/Git Session → Documentation/Comments & Git Operations
```

An unassigned role is unavailable as an independent Session. Do not simulate independence by relabeling same-Session work.

## Context Firewall

In a multi-Session Coding run, the input-side Session does not perform open-ended project inspection. Primary Output consumes source/configuration state; Change Verification consumes final-state evidence; Documentation/Comments & Git Operations consumes Git state and approved documentation scope. Each returns only the facts needed for the next decision.

Only strictly bounded, read-only metadata may be inspected directly by the input-side Session. Potential output volume and repository-state impact determine the boundary, not the command name. A single Session has no cross-Session firewall, but still reads progressively and compresses raw state.

The firewall limits raw-state ingress, not semantic reasoning. The input-side role retains ownership of meaning, trade-offs, release decisions, and acceptance. Ephemeral UI/project localization belongs to the Session that observes it and is not promoted to long-lived Contract state.

## Primary Execution Session and affinity

Maintain one Primary Execution Session: the assigned Primary Output Session in multi-agent mode, otherwise the current Session. Reuse it for related exploration, implementation, diagnosis, tests, repairs, and local execution to preserve stable context. A Session is sticky but not immortal; lifecycle changes use the active workflow's recorded state.

Session separation and Git worktree separation are distinct. Workers for one development request normally share its primary worktree; an isolated worktree requires an explicitly released isolation scope. Do not claim cache hits or other runtime savings merely from Session reuse.
sed: --: No such file or directory
