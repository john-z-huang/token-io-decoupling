# Shared Orchestration Protocols

This file defines only the protocols shared by Coding Flow and Multimodal Flow. Scenario-specific roles, context firewalls, execution loops, and acceptance boundaries are defined by the individual Flow documents. Do not copy a Flow-specific role or raw state into another Flow merely to produce a “unified architecture.”

## Semantic Contract baseline

The Decision / Input-side Reasoning Agent is responsible for stabilizing high-value decision information. A Contract contains only the minimum stable semantics required for safe execution:

- `Goal`: the final objective;
- `Constraints`: business, compatibility, safety, or user boundaries that must not be broken;
- `Decisions`: approved architecture and key trade-offs;
- `Acceptance`: acceptance criteria.

A Semantic Contract is a decision anchor, not a replacement for complete context or raw Observation. Relevant context that the host can safely share may be provided directly to the corresponding Primary Agent. Subsequent communication should normally contain only new goals, decision changes, and necessary constraints rather than periodically rewriting the full background.

Prefer amendments when updating a Contract. Send one explicit authoritative decision snapshot only when historical revisions conflict so badly that the currently effective state cannot be determined; rebuild the corresponding Primary Agent when necessary.

If context required for safe execution is neither present in the current Primary Agent nor shareable by the host, and a short Contract cannot compensate for it, stop and report a context block. Do not make the high-value decision Agent re-encode the entire history as long output to work around the limitation.

## Role and Session mapping

Decision, Input-side Reasoning, Primary Observation, Primary Output, and similar names represent responsibility and context ownership first. They do not require every role to map to a separate Agent or Session.

Creating another Session requires an independent structural benefit, such as model capability tiering, distinct high-volume context ownership, real parallelism, fresh verification, context-capacity management, or an explicit isolation requirement. Do not perform same-model delegation merely because of role names, workflow topology, long output, ordinary project exploration, implementation, testing, or generic “task complexity.”

When the current Agent already satisfies the target role's model and runtime requirements and no independent benefit exists, reuse the current Session by default. For Coding Flow, the concrete Single-Agent Luna Mode used when the current Agent is explicitly `gpt-5.6-luna` is defined in [`coding-flow.md`](coding-flow.md).

This rule does not mean every same-model role must be merged. In Multimodal Flow, Primary Observation and Optional Primary Output may remain separate Sessions even when both use the same model because visual/temporal raw state and output materialization have different context ownership.

## Dispatch Preview

Before actually creating a child Agent or sending a new execution instruction to an existing independent Primary Agent, the parent conversation must first display an extremely short `Dispatch` preview so the user can see what is being delegated. It is a visible summary of the instruction about to be sent, not the complete child-Agent prompt, and it must not expose hidden reasoning.

Switching logical roles within the current Session, performing the current Agent's own exploration/implementation/verification, or maintaining a Semantic Contract is not a Dispatch. In particular, Single-Agent Luna Mode must not print a fake `Dispatch → Luna`, construct a self-prompt, or create an unnecessary child Agent just to satisfy this rule.

Keep only the minimum information needed to identify the delegated task:

- `Task`: one sentence describing the objective or incremental objective;
- `Scope`: only when necessary, list key paths, modules, visual collections, or processing range;
- `Constraints`: only constraints that directly change how execution must proceed;
- `Runtime`: only when explicit model, reasoning effort, or similar parameters matter for this dispatch.

Default to **1–3 lines** and target **about 80 tokens or less**. If it is clearly approaching or exceeding **about 120 tokens**, compress it before dispatching. Do not mechanically fill empty fields, and do not print the full acceptance checklist, full Contract, or explanatory prose.

When reusing an independent Primary Agent, preview only the new delta; do not repeat information already visible from earlier dispatches. If the host already clearly displays an equivalent task summary in the same parent conversation, do not duplicate it. A message such as “Agent created” or “working” without task semantics is not equivalent.

Scenario-specific restrictions:

- Coding Flow: do not expand the Dispatch Preview into a file-by-file, line-by-line, or command-by-command execution plan.
- Multimodal Flow: do not enumerate large image/frame sets, copy OCR/DOM, output click sequences or screen coordinates, or replay full visual history.

Recommended forms:

```text
Dispatch → Luna | Task: fix authentication middleware refresh logic; Scope: auth/*; Constraints: preserve API compatibility; Runtime: xhigh
```

```text
Dispatch → Observation | Task: compare checkout reference with current UI; Scope: checkout; Constraints: screen broadly before focused inspection
```

## Event-driven progress reporting

An independent Primary Agent does not continuously stream work logs. Low-decision-density steps such as ordinary file reads, grep results, screenshot changes, scrolling, local analysis, compile-error fixes, and the next command remain in that Agent's own context.

Send an extremely short message to the parent Agent only when one of these events occurs:

- a material milestone, such as implementation complete, visual screening complete, or verification starting;
- a problem requiring high-value semantic, architectural, or risk judgment;
- a block, major deviation, or inability to continue satisfying the approved Contract.

Include only what the parent Agent needs for the next decision. Meaningful fields such as `Status`, `Issue`, and `Need` may be used; omit fields with no information. Do not attach full logs, diffs, screenshot sequences, OCR text, or other high-volume raw state.

At task completion, return only a compressed delivery summary: primary result, mechanical/visual verification conclusion, and remaining risks or boundary changes.

Single-Agent mode has no independent parent/child Session and does not simulate Agent-to-parent progress messages. The current Agent reports necessary progress to the user using the host's normal interaction rules.

## Evidence-on-Demand

A high-value decision Agent does not re-read complete raw evidence by default. When it must verify a conclusion, ask the independent Primary Agent that owns the raw state a targeted question. That Agent returns only the minimum necessary evidence, relevant paths, image/frame references, or small factual excerpts.

If the high-value decision responsibility and Primary responsibility are in the same Session, inspect the current context or tool state directly rather than creating a self-handoff for Evidence-on-Demand. Create a fresh verifier only for high-risk work or when independent review has concrete value; independent verification is not a fixed cost for every task.

## Cache-Aware Context Stability

Within one workflow, prefer `stable prefix + small delta`: preserve stable sessions, project history, visual-state ownership, and approved decisions, then append only new goals, amendments, or verification requirements. Do not periodically resummarize the entire task merely to “synchronize state,” and do not repeatedly regenerate highly overlapping complete Contracts.

Cache friendliness is a context-organization goal only. Actual cache keys, hit conditions, and quota accounting are host-defined and must not be presented as guaranteed benefits. If stable history begins to impair correct understanding, prioritize correctness and perform one state compression or Agent rebuild.

## Delegation boundary

A Primary Observation Agent or independent Primary Output Agent must not recursively delegate. Additional Agents, fresh verifiers, and cross-Flow handoffs are orchestrated by the current parent high-value decision Agent. When Single-Agent mode needs an exception Agent, the current Agent creates it directly rather than constructing a virtual Primary hierarchy first.

This Skill cannot bypass higher-priority permissions, user authorization, product restrictions, or safety rules. Role division, a Semantic Contract, or established Session Affinity does not constitute additional authorization.
