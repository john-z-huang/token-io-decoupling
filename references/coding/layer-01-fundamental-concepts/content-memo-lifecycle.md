# Worker Content Memo Lifecycle

This module defines creation, update, cleanup, and local-index discoverability for a Worker's file-backed execution memo. It does not define memo content, the dispatch switch, handoff or replacement strategy, or task acceptance.

## Creation and update

Create or update `content-memo.md`, or an existing equivalent document identified as the memo, when reusable execution state first appears and at material milestones, a blocking boundary, handoff, replacement, or normal exit.

## Cleanup and discoverability

Cleanup and compaction must preserve the `content-memo.md` content contract rather than turn the memo into a command journal. The memo must remain discoverable from the Worker's local index.
