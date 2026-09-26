# Worker Content Memo

[English](content-memo.md) | [简体中文](content-memo_zh_cn.md)

This module defines the reusable content contract for a Worker's file-backed execution memo: its purpose, language and format rules, recordable state, and prohibited material. It does not define the dispatch switch or memo lifecycle.

## General rules

### Purpose and language

The memo is a compact execution-state document for stable, reusable facts. Worker-authored context prose uses **Chinese**. Preserve paths, filenames, commands, symbols, keys, hashes, exact errors, and log fragments in their original form. Mechanically copied source documents retain their source language and content. This rule does not change the language of code comments, commits, Issues/PRs, READMEs, product documentation, or user messages.

### Recordable state

Use `content-memo.md`, or an existing equivalent document identified as the memo. Record only stable, reusable state:

- completed result and relevant findings;
- changed paths or symbols;
- verification state and exact evidence pointers;
- failed approaches that prevent repetition;
- remaining work, blockers, or handoff needs.

### Prohibited material

Do not write a per-command journal or record complete logs, complete diffs, large source copies, secrets, private reasoning, or unrelated history.

## Codex CLI / ChatGPT Desktop optimizations

Codex local memories (when enabled) summarize reusable cross-chat experience, while `/compact` reduces one chat's context. Neither guarantees an up-to-date Worker-owned memo for the current authorized slice, and neither carries the required source hashes, changed paths or next-action contract by itself. Keep stable execution state in the explicit `content-memo.md`, with only bounded evidence pointers; do not copy local memory files or entire CLI transcripts. [OpenAI: local memories](https://learn.chatgpt.com/docs/customization/memories), [OpenAI: compact command](https://learn.chatgpt.com/docs/developer-commands).

## Claude Code CLI / Claude Desktop optimizations

Claude Code's `CLAUDE.md` and auto memory capture standing instructions or reusable learned preferences; `/compact` condenses a **conversation**, and `PreCompact`/`PostCompact` observe that operation. None is a substitute for this Worker-owned, path-scoped, evidence-linked `content-memo.md`. When a memo is enabled, write only stable decisions, source references, changed paths, blockers and next actions into the authorized file; do not dump a full transcript or copy auto memory into it. [Anthropic: memory](https://code.claude.com/docs/en/memory), [Anthropic: compaction hooks](https://code.claude.com/docs/en/hooks).

## Related concepts

- [Worker Content Memo Dispatch](content-memo-dispatch.md) — locate the memo dispatch switch.
- [Worker Content Memo Lifecycle](content-memo-lifecycle.md) — locate memo lifecycle rules.
