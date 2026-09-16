# Worker Content Memo

This module defines the language, switch, content boundary, and lifecycle of a Worker's file-backed execution memo. It does not define Agent topology, context transport, permissions, or task acceptance.

## Scope and language

The memo is a compact execution-state document kept in the Worker's assigned context directory. Worker-authored context prose uses **Chinese**. Preserve paths, filenames, commands, symbols, keys, hashes, exact errors, and log fragments in their original form. Mechanically copied source documents retain their source language and content. This rule does not change the language of code comments, commits, Issues/PRs, READMEs, product documentation, or user messages.

## Dispatch switch

The parent sets:

```text
write_content_memo: true
```

`true` is the default, including when the field is omitted. The Worker maintains a concise memo once reusable execution state exists. `false` suppresses only the file-backed memo and is appropriate only when memo cost clearly exceeds likely reuse, recovery, or handoff value. The Worker cannot change the switch; only the parent may choose a later value for a later slice.

## Memo content and lifecycle

Use `content-memo.md`, or an existing equivalent document identified as the memo. Record only stable, reusable state:

- completed result and relevant findings;
- changed paths or symbols;
- verification state and exact evidence pointers;
- failed approaches that prevent repetition;
- remaining work, blockers, or handoff needs.

Create or update it when reusable state first appears and at material milestones, a blocking boundary, handoff, replacement, or normal exit. Do not write a per-command journal. Keep it free of complete logs, complete diffs, large source copies, secrets, private reasoning, and unrelated history. The parent or an authorized successor must be able to locate it from the Worker's local index.

With `write_content_memo: false`, the Worker still observes its released scope, return conditions, authorization, and required checks, and still returns the compressed result and evidence needed by the parent. If a later handoff lacks sufficient facts, the parent records only what is actually known; it must not reconstruct a fictitious history.

Minimal dispatch form:

```text
Objective: fix the confirmed token-refresh boundary
Own Context RW: <context-directory>
write_content_memo: true
```
sed: --: No such file or directory
