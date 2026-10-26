# MCP workspace development guide

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

This guide owns development, artifact checks, uv tool installation, and Codex setup for the Python workspace. The [architecture contract](../ENHANCED_ARCHITECTURE.md#implementation-packages) owns package responsibilities and dependency direction; the [Skill entry](../SKILL.md) and its linked owners remain the workflow authority.

## Environment and checks

The workspace contains eight independently buildable distributions, each with its own `pyproject.toml`, and one shared `uv.lock`. Only the root distribution, `token-io-decoupling`, exports a console script. Run these commands from `mcp/` using managed Python and locked dependencies:

```sh
uv sync --managed-python --locked --all-packages --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

`ty` covers root sources, tests, library packages, and the core build hook. Set `UV_PROJECT_ENVIRONMENT` to an absolute temporary directory to keep the environment outside the checkout. Tests use temporary databases, mocked bindings and API transport; they need no real API request. Run the documentation checks required by [repository instructions](../AGENTS.md) from the repository root.

## Unified launcher and profile tools

The installed command is `token-io-decoupling`. Select a profile at startup:

```sh
token-io-decoupling start-mcp-server --profile workflow
```

`--profile` accepts `workflow`, `root`, `worker`, or `share`. Omitting the subcommand starts stdio with the workflow profile; `--version` prints the launcher version. Each profile has a fixed, disjoint inventory:

| Profile / Codex server registration | Tools |
| --- | --- |
| `workflow` / `token-io-decoupling-workflow` | `workflow_capabilities`, `rules_get_context`, `workflow_evaluate`, `evaluate_control_checkpoint` |
| `root` / `token-io-decoupling-root-agent-tools` | `workflow_open`, `delegation_reserve`, `delegation_bind`, `slice_check`, `slice_release`, `workflow_transition`, `parent_get_worker_summary`, `workflow_reconcile` |
| `worker` / `token-io-decoupling-worker-agent-tools` | `worker_get_assignment`, `worker_record_progress`, `worker_get_evidence`, `worker_report_blocker`, `worker_get_recovery_context` |
| `share` / `token-io-decoupling-share-tools` | `database_schema_status`, `state_get`, `record_evidence` |

A profile controls discovery, not authority. Without a trusted host channel, public capability/rule reads succeed, schema status reports unavailable without inspecting state paths, and protected calls reject the missing binding. Workflow/Control evaluation requires a verified Root. Shared reads and evidence writes resolve the verified role on every invocation; Worker reads reject a non-null Root `index_page` cursor.

Canonical Python implementations use the independent package names shown in the architecture contract. The renamed `token_io_decoupling_mcp` adapter namespace carries the former facade modules and default factory's public-only behavior; `python -m token_io_decoupling_mcp.cli` remains available. The old `token_io_mcp` import namespace is not exposed as a general API. The two immutable v1 migration sources retain `token_io_mcp.models` in their historical bytes; the state migration loader provides a temporary alias for `DatabaseKind` only while importing those modules, then removes it. Use the renamed adapter paths for direct migration imports; importing frozen state migration modules directly bypasses the scoped loader and is unsupported. Compatibility files are owned by core, state, or launcher without duplicate wheel paths. The old four console scripts and the former `token-io-mcp` console script are not exported by this workspace.

## uv tool installation and Codex setup

Install the workspace root from its source path; uv resolves its declared local workspace dependencies. The directory reported by `uv tool dir --bin` must be on `PATH`, or invoke the installed command by its absolute path. Real setup also requires the Codex CLI on `PATH`:

```sh
uv tool install --managed-python --python 3.14 /absolute/path/to/skill/mcp
token-io-decoupling setup codex --dry-run
token-io-decoupling setup codex
```

Setup registers all four server names above using one verified absolute executable path and profile-specific arguments. To configure one, use `setup codex --profile root`. `--all` is an optional explicit alias for the default all-profile selection and cannot be combined with `--profile`. To migrate existing registrations after reviewing the dry-run output:

```sh
token-io-decoupling setup codex --replace
```

The setup separation follows [Serena's client setup implementation](https://github.com/oraios/serena/blob/main/src/serena/config/client_setup.py). Our launcher resolves its executable from the running installation's scripts directory and exact distribution entry-point metadata. It does not infer a project or identity from the startup directory.

Dry-run prints the selected JSON argument vectors and runs no subprocess or Codex preflight. Real setup probes the CLI and reads its listing and nested `transport` data before writes. Enabled registrations with the same resolved command and `start-mcp-server --profile <profile>` arguments are skipped, preserving additional settings. Conflicting or disabled entries require `--replace`. Replacement uses the official same-name upsert, without deleting first. Preflight failures cause no writes; partial apply failures report applied and pending names. Captured configuration and subprocess output are not printed. For a manual equivalent:

```sh
codex mcp add token-io-decoupling-root-agent-tools -- /absolute/installed/token-io-decoupling start-mcp-server --profile root
```

After the new launcher and registrations are verified, a migration from this repository's old four-command tool can remove that old distribution with `uv tool uninstall token-io-mcp`. Preserve unrelated tools, servers and settings, and reconnect the MCP client to load the new launch command. Setup does not establish a trusted host binding.

The protocol target remains `2026-07-28`. SDK subprocess tests verify negotiation and calls; actual trusted host integration remains separate evidence.

## Authenticated host channel

`HostChannelBindingProvider` and `serve_host_binding_channel` in `token_io_decoupling_core.host_binding` connect the CLI to a trusted host's existing `BindingProvider`. The host attaches one real Session to one connected Unix stream socket outside MCP request arguments. It passes the connected descriptor to an unprivileged CLI process and serves the other end. The supervisor must retain its serving endpoint within the trusted boundary and must not reassign a channel to another Session. The host launches the selected executable, for example `token-io-decoupling start-mcp-server --profile root --host-fd N`, where `N` is an inherited descriptor numbered at least 3; this argument locates a transport and supplies no identity or permission.

The CLI authenticates the peer through operating-system credentials: `SO_PEERCRED` on Linux and the native `getpeereid` call on macOS. This implementation pins the trusted peer to UID 0 and rejects a CLI process running as UID 0. A socket created by the Agent's own user cannot establish trust. Unsupported credential facilities, invalid descriptors, and failed startup binding terminate the requested bound launch. See the [Linux Unix-socket manual](https://man7.org/linux/man-pages/man7/unix.7.html) and [Apple peer-credential manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html) for the kernel mechanisms.

For a bound CLI launch, the state root is `.local/state/token-io-decoupling` beneath the current effective user's home from the operating-system account database. Caller-controlled `HOME` values cannot redirect it; an unavailable or invalid account mapping rejects startup. Trusted Python embeddings retain their explicit `state_root` factory argument.

The bridge pins project, Root, current Session, parent, and role at startup. Every protected call rereads current capability and guard evidence from the host; revocation or an identity change rejects the call. Child verification uses the host's current parent identity. The wire format accepts only the two binding operations, uses bounded frames and a finite timeout, and rejects malformed or mismatched responses without retry. A failed channel cannot regain trust through later responses.

The host must enforce the actual sandbox, path, and Worker-store boundaries before reporting the corresponding guards. Kernel authentication identifies the trusted supervisor; it does not create those guards or prove that a runtime's Session mapping is correct. This package supplies the bridge and host-side serving API, not a privileged service installer or a verified Codex/Claude Code runtime integration. A normal MCP client configuration cannot manufacture the inherited privileged channel. Existing test providers and tests that mock peer credentials remain synthetic evidence; the unmodified same-user channel rejection test exercises the real local credential boundary.

Before claiming an actual runtime integration, verify Root initialization, evidence insertion, transition and readback through that runtime's MCP connection; verify a real released and bound Worker can read its assignment and write only its own progress/evidence; and test revocation and cross-Worker rejection with the actual host guards. Restart or reconnect an existing client to load changed startup arguments and tool inventory; editing this checkout does not change an already running MCP process.

[Codex caller matching](CODEX_CALLER_CONTEXT.md) describes the optional `--codex-context` request-matching gate for an already verified host binding. It consumes SDK request metadata and does not add an authentication source.

## Required configuration for real API requests

Root and every delegated Agent must follow this constraint in both project functionality and test/smoke code: immediately before any real API request, read both `OPENAI_API_KEY` and `OPENAI_BASE_URL` from the local process environment. Both values must be present and nonempty; whitespace-only values are invalid too. If either is missing or invalid, do not create the SDK client or send a real request; return to the documented fallback instead.

Do not substitute a hardcoded key or endpoint, caller-supplied replacement, or the SDK's default endpoint. Read the two local values at invocation time and pass them explicitly to the SDK. Never print or persist their values. Synthetic configuration is permitted only for mocks that send no network requests.

The API remains disabled by default. Real requests additionally require explicit enablement and authorization for outbound data; this document alone grants neither. The ordinary test suite uses mocks, while a real smoke test requires a separate explicit opt-in and must obey the same two-variable requirement.

An authorized embedding enables advice with `DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True)` through the factory's `decisions_config` argument. Optional `semantic_input` on the two evaluation tools is limited to task intent, output class, Contract change, verification impact, and Control. The response keeps the Core result separate from advice. With no semantic input, the original Core response is retained. Advice never selects or confirms a Gate branch; stale, invalid, refused, unavailable, or replayed advice returns to document judgment.

After explicit authorization for a real synthetic request, run this separately from ordinary tests, from `mcp/`, with both local environment variables already configured:

```sh
TOKEN_IO_RUN_REAL_DECISIONS=1 uv run --managed-python --locked -- python tests/decisions_real_smoke.py
```

Without the opt-in, the script makes no request. It uses a temporary Root database and a synthetic trusted provider, calls `DecisionsAdvisor` directly, and reports only safe status, reason, classification metadata, choice, and usage. It does not prove a real host binding or a real API call through the MCP handler. MCP handler/protocol tests instead use mocked API transport. The advisor reads both required local variables at invocation time; neither the script nor the project supplies replacement credentials or a default endpoint.

## Build, rule resources, and installed checks

Build all eight wheels and source distributions from `mcp/`:

```sh
uv build --all-packages --managed-python --python 3.14 --out-dir /tmp/token-io-dist
```

The core package owns rule resources and its custom build hook. The canonical registry remains `mcp/rule-registry.json`; build output contains bounded excerpts from its English/Chinese owner headings. Core sdists carry their own `rule_sources`, so a detached build does not borrow a neighboring checkout. The default `token_io_decoupling_core.rules.RuleLoader` reads packaged snapshots; source development must explicitly supply the repository root. Editing Markdown does not update an installed wheel: rebuild and reinstall it.

Released migration files belong to the state package and remain byte-for-byte unchanged because database history records source checksums. The state loader temporarily supplies the historical `token_io_mcp.models.DatabaseKind` import required by the two v1 files; it removes the alias after importing them. Directly importing frozen state migration modules bypasses this scoped loader and is unsupported; use the renamed adapter migration path for direct imports. Namespace relocation does not authorize rewriting history, checksum verification, or schema versions. Tests cover legacy history and upgrades as well as fresh databases.

The [MCP CI workflow](../.github/workflows/mcp.yml) runs locked checks on managed Python 3.11 and 3.14 and a separate installed-wheel job. Export third-party build/runtime constraints with `uv export --no-emit-workspace` (plus `--all-groups` for builds or `--no-dev` for runtime). Workspace members are supplied by the local artifacts, not editable requirements. To install from the detached wheel set, use its directory as `--find-links` and install the root `token_io_decoupling-0.1.0-py3-none-any.whl`; retain the configured index for locked third-party dependencies. See CI for the complete commands.

For temporary installation, set command-local `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` to absolute temporary directories. Run `tests/installed_stdio_smoke.py --cli /absolute/temporary/bin/token-io-decoupling` with the locked workspace interpreter. It starts four profile subprocesses outside the checkout with an empty `PYTHONPATH`, verifies exact inventories and binding rejection, checks both rule languages, and runs setup dry-run with an empty `PATH`. Source-root tool installation is checked separately. These results prove packaging and stdio behavior, not actual host binding or a GitHub Actions run.

The [documentation workflow](../.github/workflows/multilingual-docs.yml) retains multilingual/link/route validators and scanner regressions; it prunes generated resources and environments while checking authored workspace documentation.

## Native recovery development checks

The [Native Authority Transfer](../references/coding/layer-01-fundamental-concepts/native-authority-transfer.md) and [Native Reconciliation](../references/coding/layer-01-fundamental-concepts/native-reconciliation.md) owners define the workflow boundaries. The checks below verify the implemented service cases; they do not establish a full export or host-stop capability.

Use temporary databases and synthetic bindings for recovery development. The focused state-service cases exercise explicit full-set adjudication, preserved comparison history, recovery Revision/Epoch freshness, outstanding evidence requests, and blocked dispatch side effects. They also cover exact confirmation without hiding older conflicts, fresh Control before the first post-recovery Slice, effect-free confirmed dispatch replay, and bounded readback of oversized legacy snapshots. Migration tests distinguish proven legacy confirmation pairs from malformed or nonadjacent records. Run them from `mcp/` before the complete suite:

```sh
uv run --managed-python --locked -- pytest tests/test_state_service.py -k native
uv run --managed-python --locked -- pytest tests/test_migrations.py
```

These checks do not prove a host can stop a Worker. The supported material-recovery path has existing Root control state and no bound Worker, active Worker Slice, or pending dispatch. It adjudicates the Contract source and semantic-reference pair; it does not reconstruct missing identity, dispatch, lifecycle, or acceptance history. Keep unsupported states blocked and preserve their records. Evidence references and request hashes provide review pointers and integrity binding; neither authenticates a caller or independently establishes freshness or quiescence.
