# Coding Delegation Mode and Count Gate

This module owns root-directive mode confirmation, Single-Agent restrictions, Multi-Agent count confirmation/locking, and re-entry. It consumes and updates the state record; it does not create children or define their lifecycle.

## Root-directive gate

For every new root user directive, the root parent must:

1. Analyze the task enough to make a useful recommendation.
2. Recommend Single-Agent Coding or Multi-Agent Coding with a concise reason.
3. Ask the user to choose and wait for an unambiguous confirmation.

A mode stated in the directive is input to the recommendation, not a substitute for confirmation. Until confirmation, do not create/manage Agents or Sessions, release Dispatch, or begin substantive reconnaissance, implementation, verification, documentation, or Git work. Mandatory instruction loading and capability checks needed to form the question are allowed.

Record the confirmed mode in the task-control record. A new root directive reopens this gate, even for the same project. Ambiguous or non-responsive input does not release it.

## Single-Agent Coding

After confirmation, keep all work in the current Session. Do not create, fork, hand off to, message, replace, or otherwise manage a child Agent or additional Session. Structural benefit, verification, documentation/Git needs, bootstrap, recovery, or runtime convenience are not exceptions. Independent verification remains a semantic requirement, but is unavailable on this route.

## Multi-Agent Coding and count

After Multi-Agent confirmation, recommend the exact positive integer child count, ask the user to confirm it, and wait. The count is the total budget for the root directive, not a per-stage or per-role number.

After count confirmation, lock it before the first Dispatch. Create exactly that many children if the runtime can safely do so; otherwise block rather than silently changing the count. Every independently assigned role consumes a slot. Reuse does not create a slot. Replacement, fork, handoff to a new child, or an additional verifier is a new creation and is forbidden after the lock for this directive.

## Higher-priority limits and re-entry

Higher-priority user, permission, security, product, runtime, capability, repository, and safety constraints always apply. An unavailable capability blocks the route; it never authorizes silently changing mode or count. A later directive that materially changes delegation must reopen mode and count gates before changing topology.
