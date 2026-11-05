# Serena Memory tail reads and write checks

[English](SERENA_MEMORY_TOOLS.md) | [简体中文](SERENA_MEMORY_TOOLS_zh_cn.md)

This document owns the two read-only Memory tools' inputs, backend binding, results and limits. It does not replace Serena access policy or the Skill's complete-content preservation and archive requirements.

## Tools

Both tools belong to the `workflow` profile and use direct arguments, without a `payload` envelope. They perform local file reads and string matching; they make no model/API requests and do not write Memories, directories or workflow state.

| Tool | Required arguments | Result |
| --- | --- | --- |
| `serena_memory_tail_read` | `memory_path`, `tail_lines` | Bounded tail text, canonical identity and line-count/range evidence. |
| `serena_memory_write_check` | `memory_path`, `changed_content`, `tail_lines` | Compact `success`/reason and window evidence; no expected-text or tail echo. |

`memory_path` is a nonblank string of at most 4096 characters. `tail_lines` is a strict integer from 0 through 10000; booleans, negative values and numeric strings are invalid. Zero requests line-count metadata with empty content. The selected tail and `changed_content` are each limited to 64000 characters. An oversized tail fails explicitly instead of silently truncating. `changed_content` must be nonempty.

For example, after an authorized Memory append:

```json
{"memory_path":"mem:plans/PLAN-example","tail_lines":12}
```

For a quick literal check of that append:

```json
{"memory_path":"mem:plans/PLAN-example","changed_content":"Validation passed.\nNext: review.","tail_lines":12}
```

The second operation invokes the same tail-read implementation once, then tests whether `changed_content` is a literal substring of the returned text. Matching is case-sensitive, without regex or additional normalization.

## Default installation with uv tool Serena

With Serena already installed by `uv tool` and an existing configured Serena project, run the repository's normal installer:

```sh
bash /absolute/path/to/token-io-decoupling/scripts/install-codex-mcp.sh \
  --serena-project-root /absolute/path/to/your-project
```

This installs/updates this MCP and runs `setup codex`. Setup discovers `<uv tool dir>/serena-agent/bin/python`, probes the read backend, and saves the following suffix only in the workflow profile's `start-mcp-server --profile workflow` arguments:

```text
--serena-project-root /absolute/path/to/your-project --serena-python /resolved/Serena-env/bin/python
```

The actual virtual-environment interpreter path is saved; its final symlink is not resolved to the base Python. Override discovery with `--serena-python /absolute/Serena-env/bin/python`. An existing installation can run `token-io-decoupling setup codex --serena-project-root /absolute/path/to/your-project` directly. No user-authored factory or manual configuration edit is required. Setup preserves a recognized existing binding when invoked without new binding options; changing the bound project/interpreter requires `--replace`. Dry-run defers discovery/probes and shows an interpreter placeholder.

Reload the workflow MCP server after setup. `SERENA_HOME` is forwarded by name, without saving its value; supply the same environment value to Codex when Serena uses a custom home. The project is explicit, never inferred from the installation checkout or current directory. Omitting all binding options retains the legacy unconfigured mode for a new registration.

Serena and this MCP have different pinned dependencies. The backend therefore invokes a fixed local helper in the existing Serena Python environment, exchanging bounded JSON for only capability/tail-read/write-check operations. The MCP environment does not import or install Serena. The helper safely reads existing `serena_config.yml`, `project.yml` and optional `project.local.yml`, honoring the configured data directory and combined regex policies; it does not invoke Serena's migrating/saving configuration loaders, activation commands, Agent, LSP, model or API. Required YAML files must be regular non-symlink files, and configuration/Memory directories must already exist. Missing or unsupported configuration is unavailable, without initialization or migration.

### Advanced embedding and factory

A compatible trusted embedding can still supply `create_server(serena_memory_service=SerenaMemoryReadService(manager, project_root))` with an existing real Manager. Alternatively, the launcher can import an operator-maintained no-argument factory:

```sh
token-io-decoupling start-mcp-server --profile workflow \
  --serena-memory-factory operator_memory:build_reader
```

That callable must return a `token_io_decoupling_workflow.serena_memory.SerenaMemoryReadService` bound to the intended Manager/project. The operator owns compatibility and initialization for that advanced embedding. The factory option loads trusted code and is mutually exclusive with the isolated project/Python pair; it is not accepted in tool arguments, `setup`, or `skills` commands. Neither mode discovers another process's active project or initializes Memory roots.

Without either backend configuration, both tools remain discoverable and return `unavailable`, without importing Serena or probing Memory paths. Inspect `workflow_capabilities` fields `serena_memory_reads`, `serena_memory_binding`, and `capability_details.configuration.serena_memory_reads` before relying on them. This is separate from `--task-plan-factory`: configuring either service does not configure the other.

## Names, paths and access policy

Accepted inputs include Serena logical names such as `notes/design`, `notes/design.md`, `mem:notes/design`, and `mem:global/notes/design`; corresponding existing file paths may be absolute or relative to the explicitly bound project root. File paths must map back into the Manager's actual configured project/global Memory roots. Custom data directories are taken from that Manager, not a hardcoded `.serena/memories` assumption.

After path mapping, the reader applies Serena name normalization and ignored-memory policy, including Serena's regex `fullmatch` semantics. Ignored Memories cannot be read. Read-only Memories can be read because these tools do not perform writes. An arbitrary project file is not made readable by supplying its path. The reader rejects traversal, out-of-root paths, symlinks and non-regular files; its symlink restriction is stricter than Serena's general path behavior. Resolution never calls a helper that creates missing directories.

The reader uses the Manager's encoding, bounded streaming and guarded file descriptors. Missing files, inaccessible or changed bindings, unsupported secure-open facilities, decoding failures, excessive output and observed changes during a read produce explicit non-success results without partial content. These checks do not provide a global lock or atomic compare-and-swap against other writers.

## Interpreting results

Successful tail reads report `content`, `total_lines`, `returned_lines`, `start_line`, `end_line`, `ends_with_newline`, and canonical Memory/path identity. Lines are delimited by LF, including CRLF; the returned text preserves its decoded separators and final newline. Nonempty line ranges use one-based numbering. A final unterminated line counts as one line, without a phantom line after a final newline; empty files and zero-line requests have zero returned lines and `null` start/end bounds. Inspect `status` and `reason` before using these fields.

For Write Check, `success: true` means only that the expected text is present in the currently observed tail. Text already present before a write can match. A correct update outside the requested tail, or a window shorter than the expected text, can fail to match. An unavailable reader is unverified, not proof that the earlier write failed. The result does not prove a new write occurred, semantic correctness, unchanged earlier content, history preservation, or concurrency safety.

Use these tools for bounded recall and supplementary checks when the applicable owner permits them. They cannot replace a required complete stored-content comparison, revision conflict resolution, or archive equality check.

## Tracking appended lines

Record `total_lines` and the line-boundary state after a read. If independent evidence establishes that the prior prefix is unchanged and only complete new lines were appended, the difference in total line counts can select the appended tail. A same-line append to an unterminated last line may add no line; middle edits, deletions or rewrites can also leave counts unchanged or misleading. Counts alone never establish the append-only premise or reconstruct a general diff.

## Local integration check

The regular MCP suite covers the service, flat wire schemas, backend/factory and profile inventories. From the `mcp/` development environment, an offline smoke can reuse the existing uv tool Serena without updating it:

```sh
uv run --no-sync python tests/support/serena_installer_smoke.py \
  --serena-python "$(uv tool dir)/serena-agent/bin/python"
```

The smoke selects a temporary `SERENA_HOME` and creates only temporary project/Memory fixtures. It exercises the fixed helper and real Manager, then verifies the configuration/data snapshot is unchanged. It does not start a model, change user configuration, access user Memories or install Serena. It is not collected by ordinary pytest. The [ordered final check](DEVELOPMENT.md#codex-sdk-final-inspection) additionally offers an explicit real-installer check after all ordinary checks and temporary installation, before the final zero-turn SDK inspection.

## Related documents

- [MCP development guide](DEVELOPMENT.md) — installation, profiles and required final checks.
- [Task Plan Memory Lifecycle](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.md) — authoritative preservation and archive requirements.
