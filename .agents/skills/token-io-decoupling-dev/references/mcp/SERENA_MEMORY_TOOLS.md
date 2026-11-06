# Local Project Memory Tail Reads and Write Checks

[English](SERENA_MEMORY_TOOLS.md) | [简体中文](SERENA_MEMORY_TOOLS_zh_cn.md)

This guide owns the two read-only Memory tools' inputs, local path rules, results and limits. They use Python's standard library to read files in the current project; they do not use Serena-Agent, MemoryManager, a separate Serena Python environment, shell commands or helper processes.

## Tools

Both tools are exposed by the `token-io-decoupling-workflow` executable and take direct arguments.

| Tool | Arguments | Result |
| --- | --- | --- |
| `serena_memory_tail_read` | `memory_path`, `tail_lines` | Bounded file tail and line-count/range information. |
| `serena_memory_write_check` | `memory_path`, `changed_content`, `tail_lines` | Whether the expected text appears in that tail, with a reason when it does not. |

Start Codex from the target project's root. At startup, the MCP process captures its working directory as the project root and reads only from `.serena/memories/` below that directory. It does not search parent or sibling directories. The directory and requested file must already exist; missing paths return a non-success result without creating anything.

`tail_lines` must be an integer from 0 through 10000. A value of 0 returns empty content and may still report line counts. The selected tail and `changed_content` are each limited to 64000 characters; `changed_content` must be nonempty.

## Memory names

`memory_path` may start with the optional `mem:` prefix. The remainder is a relative name inside `.serena/memories/`; subdirectories are supported. If the name has no `.md` suffix, the tool adds it.

Examples:

```text
plans/PLAN-example
mem:plans/PLAN-example.md
```

Absolute paths, drive paths, backslashes, traversal, all symlinks, and global or external Memory references are rejected. Use `/` between subdirectory names. The `mem:` prefix does not select another project or storage area.

## Reading and checking

The tools use Python's standard library for local file and path handling. UTF-8 text iteration preserves LF, CRLF, or CR line endings and the final line terminator. Line counts follow Python text-stream iteration and do not add a phantom final line after a trailing terminator. Results include `total_lines`, `returned_lines`, and the returned range. Missing directories/files, invalid or out-of-scope paths, and unreadable content return a non-success result. The tools do not create Memory directories or files and do not invoke shell commands or subprocesses.

`serena_memory_write_check` performs the same tail read once and checks whether `changed_content` is a case-sensitive literal substring of the returned text. It returns compact match metadata without echoing the full tail or expected text. It does not write the file. A match means the text appears in the observed tail; it does not prove that a new write occurred or that the file has not changed since.

Windows execution has not yet been independently verified.

## Related documents

- [MCP development guide](DEVELOPMENT.md) — installation and workspace tooling.
- [MCP executable and registration guide](TOOLS_REGISTRATION.md) — current executable inventory and Codex registration.
- [Task Plan Memory Lifecycle](../../../../../instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md) — preservation and archive requirements.
