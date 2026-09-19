# Worker Content Memo

This module defines the reusable content contract for a Worker's file-backed execution memo: its purpose, language and format rules, recordable state, and prohibited material. It does not define the dispatch switch or memo lifecycle.

## Purpose and language

The memo is a compact execution-state document for stable, reusable facts. Worker-authored context prose uses **Chinese**. Preserve paths, filenames, commands, symbols, keys, hashes, exact errors, and log fragments in their original form. Mechanically copied source documents retain their source language and content. This rule does not change the language of code comments, commits, Issues/PRs, READMEs, product documentation, or user messages.

## Recordable state

Use `content-memo.md`, or an existing equivalent document identified as the memo. Record only stable, reusable state:

- completed result and relevant findings;
- changed paths or symbols;
- verification state and exact evidence pointers;
- failed approaches that prevent repetition;
- remaining work, blockers, or handoff needs.

## Prohibited material

Do not write a per-command journal or record complete logs, complete diffs, large source copies, secrets, private reasoning, or unrelated history.
