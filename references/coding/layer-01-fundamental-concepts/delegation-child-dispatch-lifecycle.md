# Coding Child Dispatch and Lifecycle

This module owns Multi-Agent child creation, role allocation, Dispatch Preview, Worker boundaries, reuse, replacement, and lifecycle. It consumes a released Multi-Agent state with a locked count; it does not reopen mode or count confirmation.

## Creation capability

Creating a child means using a real MultiAgentV1 or MultiAgentV2 spawn operation, not a peer chat or generic task. The runtime must expose a child identity, parent-controlled send/return path, bounded waiting, and lifecycle status. The child receives a role, Interaction Slice, authorized scope/mutations, return conditions, and required context. If any capability is missing or unverifiable, stop and report the block.

## Allocation and auxiliary roles

Allocate only within the locked count. Primary Output, Change Verification, Documentation/Comments & Git Operations, Context Bootstrap/Refresh, and other independent responsibilities each consume a slot. If no independent verifier or auxiliary role was allocated, use the current or already allocated Agent when safe, or report it unavailable; never simulate independence by relabeling same-Session work.

Context Bootstrap/Refresh is assigned only when reuse is likely to outweigh setup: at least two independent downstream Workers, broad discovery plus three or more routed policy modules, or a source set roughly above 20k characters / 5k token-equivalents. Skip it for one small Worker or documentation-only fast paths. These are routing heuristics, not measured runtime or quality claims.

## Dispatch and Worker boundary

Before each material Dispatch, issue a concise preview of the already authorized slice. A Worker returns only to its direct parent; it must not create, fork, hand off to, message, replace, or coordinate another Agent or Session, or contact arbitrary threads. Worker findings cannot change the root mode or count.

Keep each Worker's context-exchange directory separate and grant only named paths. Release one Interaction Slice at a time unless independent, non-conflicting parallel work is explicitly allowed. Reuse the same child for authorized follow-ups and repaired epochs.

## Lifecycle

Keep created children visible and persistent. Do not close, shut down, archive, delete, or remove them from the task panel. A child may become completed only after returning its final result and evidence. While pending or running, wait or send only authorized input. On error or interruption, reuse the same child for an authorized repair or report the blocker; do not close it as cleanup.
