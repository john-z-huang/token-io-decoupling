sed: --: No such file or directory
# Shared Orchestration Protocols

This module defines reusable Coding message and context primitives. It does not choose a route, Session topology, runtime, or Agent count.

## Semantic Contract

The Decision/Input-side role stabilizes the minimum semantics needed for safe execution:

- `Goal`: final objective;
- `Constraints`: non-negotiable business, compatibility, safety, or user boundaries;
- `Decisions`: approved architecture and trade-offs;
- `Acceptance`: success criteria.

The Contract anchors decisions; it does not replace raw context. Share relevant context directly with the responsible role and send later only new goals, changes, and necessary constraints. Prefer amendments. Use one authoritative snapshot only when revisions conflict and the current state cannot otherwise be identified. If required context cannot be shared or represented safely, stop and report a context block.

## Parent return path

The root parent owns the parent-controlled route for the current request. Every Worker remains non-recursive and returns only through the runtime's parent-only channel, a control boundary, or its final result. For an out-of-scope matter, return only non-empty `Status`, `Issue`, `Need`, and `Parent action` fields. A Worker must not choose siblings, arbitrary threads, or another orchestration route. If the runtime cannot enforce this boundary, the Worker is blocked.

## Dispatch Preview

After an authorized workflow decides to create a child or send a new instruction to an independent Worker, show a minimal preview immediately before the action. It is a visible summary, not a full prompt or hidden reasoning, and cannot replace required user confirmation.

Use only the fields that matter:

```text
Dispatch → <role> | Task: <objective>; Scope: <needed paths>; Constraints: <direct execution limits>; Runtime: <only if required>
```

Target 1–3 lines and about 80 tokens or less; compress near 120 tokens. On Worker reuse, show only the new delta. Same-Session role changes and local work are not Dispatch and must not produce a fake self-dispatch.

## Event-driven feedback

Workers keep ordinary reads, local analysis, routine edits, repeated checks, and raw logs in their own context. Send the parent a short signal only for a material milestone, a decision requiring parent judgment, a block, a major deviation, or inability to meet the Contract. Return only the facts, evidence pointers, and next need required by the next decision; never attach complete logs, diffs, screenshots, OCR, or histories. Completion returns a compressed result, verification conclusion, and remaining risks.

## Evidence-on-Demand

The decision role requests targeted evidence from the role that owns the raw state. Return the minimum relevant paths, image/frame references, or factual excerpts. Do not reread or regenerate complete evidence merely to synchronize context. Each new final-state epoch requires fresh evaluation; an earlier verdict is context, never proof.

## Cache-aware stability

Prefer `stable prefix + small delta`: preserve stable decisions and working context, then append only new goals, amendments, or verification requirements. Do not periodically rewrite the full Contract or task history. Cache keys, hit conditions, quota, latency, and quality effects are runtime-defined and must not be claimed. If stable history impairs correctness, compress or rebuild once.

This module cannot bypass user authorization, permissions, product restrictions, repository rules, safety limits, or runtime capability checks.
