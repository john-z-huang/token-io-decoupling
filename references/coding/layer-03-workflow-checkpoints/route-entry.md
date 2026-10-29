# Coding route entry

[English](route-entry.md) | [简体中文](route-entry_zh_cn.md)

This checkpoint owns pre-route validation composition and the unique authorized route-selection result.

## Trigger and inputs

The Coding entry invokes this checkpoint after the [Contract checkpoint](../layer-02-workflow-concepts/entry-and-context/contract.md), [Environment checkpoint](../layer-02-workflow-concepts/entry-and-context/environment.md), [capability inventory](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md), and [Mode checkpoint](../layer-02-workflow-concepts/entry-and-context/mode.md) have passed. Inputs are their current results, including the released mode/count and any unresolved failure.

## Decision and result

Confirm the gates are complete, choose exactly the route authorized by Mode, and pass the route identity plus gate evidence to its entry step. Return the selected route identity and gate evidence to the Coding entry. That entry links the selected route; its S03/M03 step checks this result.

## Failure boundary

If any prerequisite is missing, contradictory, or unreleased, return to the owning entry checkpoint and stop dependent route work. Do not reinterpret Mode, choose a fallback route, or initialize route-only state here.

## Related concepts

- [Mode](../layer-02-workflow-concepts/entry-and-context/mode.md)
