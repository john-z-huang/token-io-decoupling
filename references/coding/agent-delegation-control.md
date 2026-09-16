sed: --: No such file or directory
# Coding Agent Delegation Control

This document alone defines Coding decisions about root-directive mode confirmation, child-Agent and Session creation, role allocation, count locking, reuse, replacement, exceptions, and delegation limits. No other module contains an independent decision rule for these matters.

## Authority and scope

The **root parent Agent** is the Agent that owns Input-side Reasoning for the current root user directive. Only the root parent can apply this policy, record its state, release a Dispatch, and create or manage a child Agent or Session. A Worker never becomes an orchestration parent and never gains authority from its own task, thread, role, progress, or findings.

This policy is subordinate to higher-priority user, permission, security, product, runtime-environment, capability, repository, and safety constraints. A required capability or authorization that is unavailable blocks the requested route; it never permits silently changing the mode or child count.

## Root-directive mode-confirmation gate

For every new root user directive, before substantive task work, the root parent must:

1. Analyze the task at the level needed to make a useful recommendation.
2. Recommend **Single-Agent Coding** or **Multi-Agent Coding**, with a concise reason.
3. Ask the user to choose one of those modes and wait for an unambiguous confirmation.

A mode stated in the root directive is input to the recommendation, not a substitute for the confirmation question. Until the user confirms the mode, the root parent must not create, fork, hand off to, message, or otherwise manage an Agent or Session; release a Dispatch; or begin substantive reconnaissance, implementation, verification, documentation, or Git work. Mandatory instruction loading and capability checks needed to formulate the question are allowed. Worker feedback and ordinary continuation requests are not new root directives and do not reopen the gate.

The root parent records the confirmed mode as state scoped to that root directive. A new root user directive starts a new mode gate, even when it continues the same project or task. Ambiguous, conditional, or non-responsive mode input does not release execution; ask again concisely.

## Single-Agent Coding

After the user explicitly confirms Single-Agent Coding:

- Keep all task work in the current Session, including Input-side Reasoning, Primary Output, documentation, Git work, and allowed verification.
- Do not create, fork, hand off to, message, replace, or otherwise manage a child Agent or additional Session. Do not use structural benefit, material-change status, verification needs, documentation/Git needs, bootstrap, context recovery, or runtime convenience as an exception.
- For a material change, preserve any independent-verification requirement as a semantic requirement, but do not create a verifier automatically. The current Session performs the allowed checks and reports independent verification as unavailable when it cannot be provided.

A later explicit root user directive requesting a child-Agent or additional-Session exception starts a new mode gate. The exception is actionable only after the user explicitly confirms the resulting mode and, if Multi-Agent Coding is selected, a positive child-Agent count. A Worker or the current Agent must not infer this exception from a request for “more review,” “parallelism,” or “help.”

## Multi-Agent Coding and count confirmation

After the user explicitly confirms Multi-Agent Coding, the root parent must analyze the task, recommend the exact positive integer number of child Agents, ask the user to confirm that number, and wait. No child Agent or Session may be created during this second gate. The number must describe the total child-Agent budget for the current root directive, not a per-stage or per-role number.

After the user confirms the positive integer:

- Record and lock the count before the first Dispatch.
- Create exactly that number of child Agents, subject to higher-priority capability, authorization, permission, security, product, runtime, repository, and safety limits. If the environment cannot safely create the requested number, stop and report the block; do not silently create fewer or more.
- Allocate roles only within that locked count. Primary Output, Change Verification, Documentation/Comments & Git Operations, Context Bootstrap/Refresh, and any other auxiliary responsibility consume a child-Agent slot when assigned to an independent child.
- Never append a child Agent or additional Session because a change is material, verification is desirable or required, documentation or Git work appears, bootstrap or context recovery would help, a structural benefit is discovered, or an existing Worker requests it.
- Reuse only the already created and assigned child Agents or Sessions for later slices when the active workflow authorizes the work. Reuse does not create a new slot and must not expand the assigned scope.
- A replacement, fork, handoff to a new child, or additional verifier is a new child creation for this policy. It is not an automatic reuse or exception. Once the locked count has been created, it is forbidden for the current root directive; a later root directive must pass a new mode and count gate.

If the locked allocation does not include an independent verifier, documentation/Git Worker, bootstrap Worker, recovery Worker, or another required role, the root parent uses the current or already allocated Agent within its authorized scope when that is safe, or reports the role/capability as unavailable. Independent verification remains independent when assigned; it must not be simulated by relabeling a same-Session check. If the missing role makes acceptance impossible, report a blocking limitation rather than bypassing the count.

### Auxiliary-role assignment

Context Bootstrap/Refresh may be assigned only when reuse is likely to outweigh setup: at least two independent downstream Workers are expected, a fresh Worker would otherwise need broad discovery plus three or more routed policy modules, or the relevant source set is roughly above 20k raw characters / 5k token-equivalents. Skip it for Single-Agent work, one small Worker, local or documentation-only fast paths, known one- or two-file tasks, and cases where expected reuse does not exceed setup cost. These are routing heuristics for this policy, not claims of billed, cached, quota, latency, or quality savings. Once assigned, the Bootstrap responsibility may be reused or refreshed only within the locked allocation; it never creates another slot.

## Dispatch and lifecycle boundaries

Only after the mode is confirmed and, for Multi-Agent Coding, the count is confirmed and locked, may the root parent issue a Dispatch Preview and create the approved child Agents. The Dispatch Preview is a concise summary of the already authorized slice; it is not a substitute for either user confirmation.

Every child receives only the role and slice authorized by the root parent. A child Agent must remain non-recursive: it may not create, fork, hand off to, message, replace, or coordinate another Agent or Session. Worker findings, checkpoints, and requests return only through the parent-controlled path and never change the mode or count.

The root parent records at least: gate status, confirmed mode, confirmed and locked count when applicable, child-to-role allocation, and any unavailable capability or blocked requirement. This record is control state, not permission to exceed the count.

## Re-entry and higher-priority limits

When a new root directive materially changes the requested delegation, reopen the mode gate and, for Multi-Agent Coding, obtain a new count confirmation before changing the child topology. Do not carry a prior mode or count across root directives without asking again.

Nothing in this policy authorizes external effects, repository mutations, Git operations, credentials, network access, or bypasses of runtime restrictions. The active Coding workflow and repository instructions still govern those boundaries.
