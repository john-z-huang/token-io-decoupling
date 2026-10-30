# Decision context selection

[English](decision-context-selection.md) | [简体中文](decision-context-selection_zh_cn.md)

This checkpoint owns whether a downstream decision needs generated background and whether that background is current and usable. It does not make the executor, output-route, role, advice-eligibility, or other downstream decision.

## Trigger and inputs

Consume the current decision question, verified facts with their source provenance, explicit user direction, and the downstream decision that may use generated context. Apply [Decision Context Generation](../layer-01-fundamental-concepts/execution-planning/decision-context-generation.md). This checkpoint does not enable advice. The separate optional five-node stage-advice gate is governed by route Advisory Selection and [Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md); it does not reopen or change Mode. Executor, output-route, candidate, and role decisions remain with their direct owners.

## Decision and result

1. Name the unresolved downstream question and identify which current facts and constraints bear on it, with source pointers and provenance labels. Keep user requirements, current evidence, plans, assumptions, and unverified claims distinct.
2. If explicit user direction settles the relevant choice, or no downstream decision requires generated context, record `Not applicable` and why. Otherwise call Decision Context Generation with only the bounded facts, provenance, and concrete decision goal needed for that question.
3. Review the returned context for factual fidelity, provenance, language, relevance, and missing information. Compare its input hash with the exact current source material and goal; compare its policy binding with the current applicable rules. Reject stale, mismatched, incomplete, or conflicting context and do not send it to downstream advice.
4. Return one of these results to the named downstream owner:

| Result | Required route action |
| --- | --- |
| Reviewed context and exact current input/policy bindings | Pass only that context and its provenance/hash evidence to the corresponding advice consumer. |
| Explicit direction settled the choice, or no downstream decision requires generated context | Record `Not applicable` and why; follow the explicit direction or proceed under the direct decision owner. |
| Generation failed, or required facts are missing/conflicting | Do not invent context or hashes. Decide directly only if verified facts are sufficient under the direct owner; otherwise block the dependent decision and request the missing evidence. |

## Failure boundary

Generated context is supporting input, not a decision, authorization, or substitute for current direct owners. This checkpoint does not determine whether any advice is enabled, relevant, or acceptable; each direct decision owner keeps its own gate, and the separate optional five-node stage-advice gate remains with Advisory Selection.

## Related concepts

- [Decision Context Generation](../layer-01-fundamental-concepts/execution-planning/decision-context-generation.md)
