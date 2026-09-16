# Worker Content Memo

This module owns the default write policy, working language, and parent-dispatch configuration for Worker execution-content summary documents in multi-Agent Coding. It is self-contained: it defines memo behavior only and does not define directory layout, cross-Worker transport, read/write isolation, or handoff mechanics.

This module applies only to execution-context summaries maintained by Workers under `<primary-worktree>/.token-io-decoupling/context/<worker-context-id>/`. It does not change the language or behavior rules for the Semantic Contract, Progress Signals, Control Checkpoints, Change Verification, Git delivery, or formal project documentation.

## Working language

Worker-authored context documents in the Worker's dedicated Context Exchange subdirectory use **Chinese** as their working language.

- `INDEX.md`, the execution content memo, `findings.md`, `changes.md`, `verification.md`, `handoff.md`, and other Worker-authored Context Exchange prose default to Chinese.
- Paths, filenames, commands, code symbols, type/function/API names, configuration keys, hashes, error text, log fragments, and other technical material that requires exact preservation remain in their original form and are not forcibly translated.
- Original documents mechanically copied from another Worker into `imports/` retain their source content; do not translate or rewrite them through the LLM.
- This rule does not require code comments, Git commit messages, Issues/PRs, READMEs, user-facing documentation, or other product artifacts to use Chinese. Those outputs continue to follow their own project and task rules.

## `write_content_memo` dispatch configuration

The parent Input-side Reasoning Agent uses the following boolean configuration when dispatching a task / Interaction Slice to an independent Worker:

```text
write_content_memo: true
```

Semantics:

- `true`: the default. The Worker must maintain a concise **execution content memo** in its own Context Exchange subdirectory, covering completed work for the slice, stable findings, key paths/symbols, actual changes, verification state, reusable conclusions from failed attempts, remaining work, and necessary evidence pointers.
- `false`: the slice does not require creation or maintenance of an execution content memo. The parent may disable it only when the work is sufficiently trivial that memo-writing cost clearly exceeds likely recovery, handoff, or reuse value.

If the parent dispatch omits `write_content_memo`, interpret it as `true`. To reduce ambiguity and make dispatch behavior visible, the parent **should carry this field explicitly in every independent-Worker Dispatch**.

A Worker must not change `true` to `false` based on its own estimate of task complexity, and must not skip the memo merely because it expects no handoff. Only the parent owns the decision to disable the switch; the parent may set a new value for a later slice.

## Default memo behavior

When `write_content_memo: true`:

1. Before dispatch, the parent provisions the Worker's dedicated Context Exchange subdirectory and sends the exact path together with this configuration.
2. The Worker creates or updates the memo once reusable execution state begins to exist; it need not create an empty file before the first command.
3. The Worker refreshes the memo at material milestones, blocking Control Checkpoints, handoff, normal exit, or replacement. Do not turn it into a per-command execution journal.
4. The Worker-local `INDEX.md` records the memo filename, purpose, and latest material update so the parent or an authorized successor can locate it on demand.
5. Keep the memo compressed and limited to stable, reusable, verifiable execution state. Complete logs, complete diffs, large source copies, private chain-of-thought, secrets, and unrelated conversation history remain prohibited.

The recommended default filename is `content-memo.md`. If an existing Worker directory already contains a document that clearly serves the same responsibility, the Worker may continue updating it rather than mechanically creating a duplicate, but the Worker-local `INDEX.md` must identify that document as the content memo.

## Boundary of `write_content_memo: false`

Disabling the content memo removes only the requirement for a **file-backed execution-content summary** for that slice. It does not disable other protocols:

- the Worker still follows `Objective`, `Authorized scope/mutations`, `Return conditions`, and `Unreleased boundary`;
- Progress Signals and Control Checkpoints still trigger under execution-control rules;
- the Worker still returns the compressed result and evidence needed to complete the current slice to the parent;
- Change Verification independence and evidence requirements are unchanged;
- the Semantic Contract, Decision Checkpoints, Context Firewall, permission boundaries, and user authorization remain in force;
- if Worker replacement actually occurs and the absence of a memo blocks continuation, the parent uses the minimum currently available facts for the necessary handoff and must not fabricate history.

Accordingly, `write_content_memo: false` is an output/file-write optimization for trivial work, not a master switch that disables Context Exchange or the parent-led control loop.

## Dispatch examples

```text
Objective: Fix the token-refresh boundary in authentication middleware
Authorized scope/mutations: src/auth/**, tests/auth/**
Return conditions: implementation complete with focused-check results
Unreleased boundary: documentation, final Change Verification, Git operations
Own Context RW: <primary-worktree>/.token-io-decoupling/context/worker-auth/
write_content_memo: true
```

For a slice the parent explicitly classifies as trivial:

```text
Objective: Correct one confirmed configuration-key typo
Authorized scope/mutations: config/example.yaml
Return conditions: one-line correction complete with diff summary
Unreleased boundary: all other files and Git operations
Own Context RW: <primary-worktree>/.token-io-decoupling/context/worker-config/
write_content_memo: false
```
