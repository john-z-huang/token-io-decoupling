# Enhanced Schema Migrations

[English](enhanced-schema-migrations.md) | [简体中文](enhanced-schema-migrations_zh_cn.md)

This owner defines schema compatibility diagnostics and the independent migration, backup, and restore boundaries for Enhanced Root and Worker stores. It does not own business-state fields, authorization policy, or semantic recovery decisions.

## General rules

### Independent histories and compatibility

Root and Worker stores use separate fixed, package-supported migration histories. Each applied version has an immutable name and checksum; published migration code is never edited or renumbered. Validate database identity, kind, contiguous history, checksums, supported current version, structure, and integrity before allowing a protected write. A missing history in a nonempty database, unknown kind, checksum conflict, future version, or incompatible structure fails closed; never silently initialize or recreate an unknown store.

Schema version is distinct from State Revision, Rule Hash, and Verification Epoch. Migrations preserve existing control state, references, receipts, and indexes; they do not reset Mode/Count, Run, Allocation, lifecycle, Revision, or Epoch.

### Read-only status, migration, and backup

Schema-status inspection is read-only: report whether the role-bound store exists, its kind, current and target versions, pending versions, compatibility, and a safe reason. It must not create a database or parent directory, migrate, or change any state. When the trusted role/path boundary is absent, return unavailable before state-path I/O. Root and Worker status is limited to their own store.

An authorized write open validates the trusted identity, permissions, derived path, and database kind before attempting migration. Under a bounded exclusive migration lock, verify compatibility and history; if an existing supported database has pending migrations, create a SQLite backup before applying them. Apply each migration and its history row in one transaction, then validate required structure, integrity, and foreign keys before enabling writes. Migration code is package-controlled, fixed, and may not commit its own transaction or call external services. A failure rolls back the current migration, preserving prior successful versions and the backup. Opening Root does not scan or upgrade every Worker store.

Restore is a separate explicitly authorized recovery action after an upper layer has stopped all business writers. The migration lock alone does not prove write quiescence. Validate the backup’s complete supported history and compatibility before replacing the target. Do not expose arbitrary database/backup paths or restore as an MCP operation; do not implement automatic downgrade or last-write-wins recovery.

## Codex CLI / ChatGPT Desktop optimizations

The current local implementation uses the fixed migration runner and a read-only schema-status operation. Use only status for diagnostics; protected migration requires the same verified host binding and write guard as other Root/Worker state writes. Protocol tests do not establish a real host’s stop-writes or filesystem boundary.

## Claude Code CLI / Claude Desktop optimizations

There is currently no Claude-specific migration optimization. Follow the general rules and do not infer a host guard or stopped-writer condition.

## Related concepts

- [Enhanced State Store](enhanced-state-store.md) — owns state authority, Root/Worker scope, CAS, and recovery indexes.
- [Coding Delegation State Record](../delegation/delegation-state-record.md) — owns protected task-record values that must survive migration.
- [Coding Delegation Worker Boundary](../delegation/delegation-worker-boundary.md) — owns Worker data isolation.
