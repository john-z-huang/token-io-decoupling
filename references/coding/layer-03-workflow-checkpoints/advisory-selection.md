# Advisory selection

[English](advisory-selection.md) | [简体中文](advisory-selection_zh_cn.md)

This checkpoint owns stage-level applicability routing for optional advice.


## Trigger and inputs

Before Mode and Session pass and authorized Root context exists, record advice as `Not applicable`; use direct authoritative sources for task-intent/output classification. Advice cannot select or change the route selection result, reopen the Mode gate, or change locked mode/count. After Root context exists, S06/M07 consumes only relevant Decision advice, S09/M11 consumes only relevant Control advice, and S10/M12 consumes only relevant Verification/Epoch advice. Apply [Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md) and the current direct checkpoint owner; return each suggestion to its named stage for evidence-based review.

## Decision and result

1. Before Mode, Session, and authorized Root context pass, record `Not applicable`; classify task intent and output from direct authoritative sources.
2. At Decision, Control, and Verification/Epoch, assess optional advice only when enabled, eligible, relevant, and the current stage binding and Root authorization are verified.
3. Record the typed suggestion, current policy/input/context hashes, freshness result, and direct-owner comparison. Return it to that stage for a decision from authoritative owners and current evidence.
4. Keep Task Assignment, Output Token Routing, and role-reservation advice outside this five-node opt-in gate; their owners control those decisions independently.
5. Return the reviewed suggestion or `Not applicable` and reason to route scheduling; advice never authorizes work or replaces a pass condition.

## Failure boundary

Stale, unavailable, malformed, or failed advice falls back to direct owner review only when required facts remain sufficient; otherwise block. Do not make external advice calls mandatory or retry around opt-in/authorization limits.

## Related concepts

- [Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md)
