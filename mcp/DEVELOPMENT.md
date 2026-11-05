# MCP workspace development guide

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

This guide owns development, artifact checks, uv tool installation, and Codex setup for the Python workspace. The [architecture contract](../docs/skill/WORKFLOW_ARCHITECTURE.md#implementation-packages) owns package responsibilities and dependency direction; the [Skill entry](../docs/skill/SKILL.md) and its linked owners remain the workflow authority.

The MCP Server targets a locally available Codex CLI, including the local Codex CLI/app-server path used by local Work. Cloud ChatGPT conversations, remote Work, and other Code Agents are not direct clients. If another Agent runs in its own environment with Codex CLI installed and configures the server by following this repository's instructions, only that environment's local Codex CLI path is supported; no other Agent or cloud-surface adapter is maintained. The server does not add a runtime-environment selection step. Follow the [directory instructions](AGENTS.md). This fixed client scope does not establish a verified host integration; actual capabilities, trusted identity, guards, and permissions remain checked by the existing operations.

## Environment and checks

The workspace contains the root distribution and three independently buildable member distributions (`core`, `transport`, and `workflow`), plus one shared `uv.lock`. The root distribution, `token-io-decoupling`, exports the administrative `token-io-decoupling` command and the two MCP executables `token-io-decoupling-workflow` and `token-io-decoupling-tools`. Run these commands from `mcp/` using managed Python and locked dependencies:

```sh
uv sync --managed-python --locked --all-packages --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

`ty` covers root sources, tests, library packages, and the core build hook. Set `UV_PROJECT_ENVIRONMENT` to an absolute temporary directory to keep the environment outside the checkout. The default suite is local and offline; live API tests require explicit opt-in. Run the documentation checks required by [repository instructions](../AGENTS.md) from the repository root.

### Test organization

Classify every new or changed test by its actual dependencies and behavior:

| Directory | Responsibility |
| --- | --- |
| `tests/mock_api_tests/` | Tests that replace collaborators, host bindings, API clients or HTTP transport with mocks, fakes or stubs. |
| `tests/unit_tests/` | Deterministic local unit tests that exercise the real tested code without mocked collaborators or live API calls. |
| `tests/real_api_tests/` | Explicitly opted-in tests and smoke scripts that send real Decisions or Responses requests. |

Split mixed modules by test case; a marker or filename does not replace correct placement. Shared fixtures and subprocess helpers may live outside these three case directories, but must not become an unclassified home for test cases. Preserve assertions, parametrization and collection coverage when moving tests, and update imports, repository-root discovery and CI/script references together. Ordinary pytest must collect and skip live cases without reading credentials or sending requests. The same placement rules apply to future tests.

## Separate MCP executables

The MCP runtime consists of two installed executables. Each starts its own stdio server without startup arguments. The `token-io-decoupling` executable is an administrative CLI for setup, Skill installation, and environment-forwarding repair. It is not an MCP runtime and has no bare-server default.

| MCP executable / Codex registration | Tools |
| --- | --- |
| `token-io-decoupling-workflow` | 17 stateless workflow capability, rule, planning, routing, and evaluation tools. |
| `token-io-decoupling-tools` | 34 tools: 33 development workflow tools and `materialize_decoupled_output`; see [Two MCP executables and Codex registration](TOOLS_REGISTRATION.md). |

The one-call registration command adds both executables:

```sh
token-io-decoupling setup codex
```

To register them separately, use the executable paths from the installed tool bin directory:

```sh
codex mcp add token-io-decoupling-workflow -- /absolute/path/to/token-io-decoupling-workflow
codex mcp add token-io-decoupling-tools -- /absolute/path/to/token-io-decoupling-tools
```

The bounded request, route selection, hash, and result contract for `decide_decoupling_workflow` is documented in [Decoupling workflow routing](WORKFLOW_ROUTING.md).

The read-only `validate_decoupling_compliance` tool checks a bounded candidate overlay against an operator-configured checkout. Its request, result, startup factory, and explicit limits are documented in [Candidate compliance preflight](CANDIDATE_COMPLIANCE.md). It does not authorize or apply writes and does not replace repository checks or final acceptance.

The Worker-only `materialize_decoupled_output` tool prepares and inspects bounded output artifacts, then applies them through an independently granted operator service. Its request, templates, grant and preflight requirements, startup option `--output-materializer-factory MODULE:CALLABLE`, result, and recovery boundaries are documented in [Worker output materialization](OUTPUT_MATERIALIZATION.md). The trusted factory returns `OutputMaterializerConfig`; absent configuration leaves the tool unavailable without probing default paths.

Each executable has a fixed discovery inventory; discovery does not grant authority. The rule/workflow path is stateless and does not require a database or host binding. `workflow_evaluate` and `evaluate_control_checkpoint` check only the supplied typed facts and declared input structure; their results do not authenticate, authorize, pass a checkpoint, persist state, or sequence later calls. Output materialization remains unavailable without its trusted startup-injected authorization provider and separate grant.

The three task-plan tools use a separately configured, checkout-bound Serena MemoryManager backend. Its capability result reports `project_root`, `storage_scope`, `repository_id`, `namespace`, and `archive_namespace`; the default project scope can be configured as global storage so linked worktrees share plans while independent repositories remain separate. The tools remain `unavailable` unless a trusted startup factory explicitly injects the service. Their payloads, configuration, identity/path mapping, deterministic checks, tests, and protection limits are owned by [Task plan lifecycle tools](TASK_PLAN_TOOLS.md). No automatic Serena configuration loading or model request is involved.

Canonical Python implementations use the independent package names shown in the architecture contract. The two MCP executables remain separately installed and expose their fixed manifests.

The [Memory tools guide](SERENA_MEMORY_TOOLS.md) owns direct tail-read/write-check arguments, local path resolution, bounded-read results and matching limits. These tools read the current project's `.serena/memories/` files with Python's standard library; they do not use the separately configured task-plan backend.

## Capability report diagnostics

`workflow_capabilities({})` is public and takes no arguments. `capability_details.schema_version=3` reports static support and configured dependencies without probing API readiness. The top-level `trusted_binding` is `unverified` for the standard executable and reflects the injected provider for embedded use. `capability_details.runtime.server_mode` reports `public_only` or `embedded`; `binding_transport` is `unavailable` without an injected provider and `unverified` when embedded. These diagnostics do not authenticate callers or authorize operations. Configuration details separately report plan backend, Memory paths, compliance reader, API and materialization conditions; unprobed dependencies are not readiness evidence.

### Installed client runtime checks

The `real_client` cases in `tests/unit_tests/test_real_clients.py` run the actual installed Codex CLI and the Codex executable shipped inside ChatGPT Desktop. They exercise each executable's app-server MCP interface without mocked client transport or host identity. This covers the MCP host-runtime boundary, not Desktop GUI interaction, an already-running daemon, or independent host authentication.

After authorization for temporary test threads and processes, run from `mcp/`:

```sh
TOKEN_IO_RUN_REAL_CLIENTS=1 uv run --managed-python --locked -- pytest -q -s tests/unit_tests/test_real_clients.py
```

The CLI defaults to `codex` on `PATH`; Desktop defaults to `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`. `TOKEN_IO_CODEX_CLI_PATH` and `TOKEN_IO_DESKTOP_CODEX_PATH` may point to other actual installations. Overrides are caller-supplied paths, not proof of client identity. Evidence includes the resolved executable path, actual version, executable SHA-256, tested source fingerprints, and successful checks; changing the JSON-RPC client name does not establish client coverage.

Each case starts a separate real app-server with a process-local `mcp_servers` override that disables inherited configured servers using safe placeholders and enables the current workspace's workflow server. Only configured server names and transport types are read; URLs, arguments, environment values, and credentials are not copied. It asserts that inherited configured servers expose no tools; clients may retain built-in platform services, which the test never invokes. It verifies the target's no-argument schema and new description, calls `workflow_capabilities` and checks structured diagnostics, and confirms that `workflow_evaluate` rejects the missing trusted binding. It uses one ephemeral thread, starts no model turn, and terminates its owned process group to release the memory-only thread and MCP subprocess. No user configuration or installed MCP package is changed, and no model API request is needed for this capability check. The operating environment must permit launching and cleaning up these processes.

Ordinary pytest skips both cases without probing installed clients. Explicit opt-in makes missing clients, permission failures, protocol errors, or old capability responses fail rather than skip or fall back to a fake. Existing SDK, Mock, and installed-stdio checks retain their narrower scope. A passing runtime check does not prove an existing client session has reloaded an updated MCP installation; that session still needs its own installation/reload verification.

### Codex SDK final inspection

The official Python Codex SDK (`openai-codex`) is pinned in the separate `codex-test` dependency group and excluded from production dependencies and wheels. Follow the repository's [final-test boundary](../AGENTS.md#codex-sdk-final-test-boundary). From `mcp/`, install the test environment and run the ordered final check:

```sh
uv sync --locked --managed-python --group dev --group codex-test
uv run --no-sync python tests/support/final_codex_check.py
```

The coordinator first runs the complete default MCP test suite, lint, formatting, type checks, documentation regressions, all documentation validators, and whitespace checks. Any failure stops the sequence. It then builds the current wheels and installs them with `uv tool` in temporary tool/bin directories before launching a new Codex CLI via SDK. This tests the current installed build without replacing the user's installation. Ordinary pytest runs only fake-based SDK policy tests; it cannot start the final inspection. Optional real-API/client tests retain their explicit opt-ins; enable any applicable opt-ins before running the coordinator, and report remaining skips.

Every SDK launch requires and explicitly reuses nonblank process `OPENAI_API_KEY` and `OPENAI_BASE_URL`, fixes model `gpt-6-luna` and reasoning effort `medium`, and verifies effective configuration and thread settings. Missing or conflicting settings fail, with no saved-login, credential, endpoint, model, or effort fallback. The key travels only through the child environment; credential values and raw SDK diagnostics are never printed or persisted in auth files.

The adapter selects the installed `codex` on `PATH`, or the absolute executable specified by `TOKEN_IO_CODEX_CLI_PATH`, instead of the SDK's bundled CLI. Temporary `HOME`/`CODEX_HOME` isolates configuration. The fresh instance loads the two separately installed MCP executables with no startup arguments, checks each executable's version through read-only `command/exec`, discovers both inventories, and calls `workflow_capabilities` plus bilingual `rules_get_context`. It performs no model turn, mutation, arbitrary shell command, or complex task. This compensates for the current session's inability to dynamically reload the updated MCP Server; it does not prove that an existing session has reloaded it. CI installs the test dependency group for policy, static, and type checks without launching this final SDK inspection.


## API and tool recovery guidance

The child-effort, decision-context, and delegation selectors make one API request per invocation; the SDK has automatic retries disabled. Their result models add nullable `recovery` guidance, serialized as `null` when no guidance is present. `retry_eligible` is only a candidate signal; for explicit transient transport, 5xx, or confirmed rate-limit failures, `total_attempt_limit` is 3 calls per caller-tracked recovery process, including the first call. The server does not track attempts or retry automatically. Callers recheck task authorization, request hashes, current policy, and any result/effect before optionally invoking again.

Authentication, authorization, configuration, quota, unknown errors, refusal, malformed/incomplete responses, and insufficient evidence are not retry candidates. Resolve the cause, refresh and re-hash stale facts/policy, or stop. Recovery guidance never changes the existing result status, reason, hash, fallback, or authority. Only a successful `available` selector result can be considered for later work after the usual gates pass.

Optional advice is a separate stateless API operation; structural checkpoint evaluations neither call Decisions nor persist an advice result. Recovery metadata applies to the API operation that returned it and never changes that operation's result status, reason, hash, fallback, or authority. Retry only a qualifying transient failure within the caller-tracked attempt limit, after rechecking current authorization and input. No state-changing replay or stored-result behavior is part of checkpoint evaluation.

## uv tool installation and Codex setup

### Install the executable with uv tool

Keep the source checkout in a normal development directory, outside `~/.agents/skills/`. With `uv` available, install the root package from its `mcp/` workspace directory; the absolute source path allows this command to run from any working directory:

```sh
uv tool install --force --reinstall --managed-python --python 3.14 /absolute/path/to/token-io-decoupling/mcp
```

uv builds and installs the executable and its declared local workspace dependencies in an isolated tool environment. `--reinstall` refreshes dependencies and bundled document snapshots as well as the launcher. This step installs the program; it does not register MCP servers or install Skill instructions. To install a built wheel instead, supply the root wheel and the directory containing the other workspace wheels (see [artifact checks](#build-rule-resources-and-installed-checks)):

```sh
uv tool install --force --reinstall --managed-python --python 3.14 --find-links /absolute/path/to/wheels /absolute/path/to/wheels/token_io_decoupling-0.1.0-py3-none-any.whl
```

Use the actual artifact version in the filename. Subsequent examples assume uv's tool bin directory is on `PATH`. If it is not, locate it with `uv tool dir --bin` and invoke the executable by its absolute path; no virtual-environment activation is needed. For example:

```sh
"$(uv tool dir --bin)/token-io-decoupling" --version
```

### Standard installation availability

Standard installation exposes bounded, stateless rule navigation and supplied-fact structural checks over local stdio, alongside the separately configured task-plan service and other tools with their documented dependencies. These public rule/navigation operations do not require thread metadata, Root/Worker registration, or persisted workflow state. Read-only Memory helpers are scoped to the startup project's existing `.serena/memories/` files. The output materializer remains unavailable unless its trusted provider and independent per-call authorization are configured. API tools require both nonblank API environment variables and per-call outbound authorization. Discovery is neither configuration nor permission.

With the Codex CLI available on `PATH`, register both MCP executables in one operation:

```sh
token-io-decoupling setup codex
```

Setup resolves and verifies the current workflow and tools executables, then registers those two targets with empty argument lists. It preserves other settings in either target table and leaves unrelated configuration untouched. It does not inspect, classify, remove, or migrate other registrations. `--dry-run` reads the configuration and preflights only the two current target sections, but starts no MCP subprocess and writes nothing. Reload the affected MCP servers after registration or tool updates. Forwarding declarations contain variable names only; they do not supply values or establish a local session context.

The Memory tools need no additional installation options or Serena packages. Start Codex from the target project root; the MCP uses its startup working directory as the project root and reads only files under `.serena/memories/`. It does not search parent or sibling projects. The Memory directory and requested file must already exist; missing paths return a non-success result without creating anything. The local file operations use Python's standard library. See [Memory tools](SERENA_MEMORY_TOOLS.md).

### Install and update local Skill instructions

After the `uv tool` installation succeeds, run the installed program from any directory:

```sh
token-io-decoupling skills install
```

This installs the packaged bilingual Skill snapshot to `~/.agents/skills/token-io-decoupling-skill`, including `SKILL.md`, workflows, references, and supporting resources. It reads the installed package, without reading or cloning the source checkout. The Skill's name is `token-io-decoupling-skill`; use that name when requesting it. If the command is not on `PATH`, use the absolute executable path here too:

```sh
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

For another name, use `skills install --name my-coding-skill`, then use the same `--name my-coding-skill` with updates. Names must use lower-case letters/numbers separated by hyphens. The old name and directory `~/.agents/skills/token-io-decoupling` are protected: installation refuses that name, symlink installation paths, and existing unknown destinations. It never overwrites or deletes the old project. `skills install` also refuses an existing managed installation; update it explicitly instead.

After changing source instructions, repeat the `uv tool install --force --reinstall ...` command above (or install the rebuilt wheel set), then update the installed Skill snapshot:

```sh
token-io-decoupling skills update
```

Updating only the executable leaves the previously installed Skill unchanged. `skills update` requires an existing managed installation and refuses locally modified files; preserve your edits separately before updating. If no Skill is installed yet, use `skills install`. Tool installation, MCP registration, and Skill installation are separate operations; neither `setup codex` nor the helper script below installs the Skill automatically. Start a fresh Agent session after installing or updating Skill instructions. If an old checkout is still discovered as a Skill, preserve it and manually disable its old discovery entry as described in the [legacy coexistence guidance](../README.md#install-the-skill-separately); the installer does not automatically resolve duplicate discovery.

### Optional combined installation and registration script

As an alternative to the separate tool-install and `setup codex` commands, use the [installation script](../scripts/install-codex-mcp.sh) to install or update the package and configure Codex in one invocation. From this repository's root, run:

```sh
bash scripts/install-codex-mcp.sh
```

Installation does not select or save a Memory project. Start Codex from the target project root; the MCP uses its startup working directory as the project root and reads only `.serena/memories/`. It does not search parent or sibling projects, and does not create missing directories or files. To run this installer outside the repository root, use its absolute script path, replacing the placeholder with the actual location:

```sh
bash /absolute/path/to/token-io-decoupling/scripts/install-codex-mcp.sh
```

Run `skills install` or `skills update` afterward as described above.

Prerequisites are Bash 3.2 or later (including macOS `/bin/bash`), `uv`, and the Codex CLI; `uv` and `codex` must be on `PATH`. The script locates `mcp/` relative to itself, runs `uv tool install --force --reinstall --managed-python --python 3.14` against that source, obtains the bin directory with `uv tool dir --bin`, then calls the absolute installed administrative executable's `setup codex`. uv resolves the declared dependencies; `--reinstall` refreshes them even when only their source or packaged rules changed. The tool bin directory need not be on `PATH`, and virtual-environment activation or a separate setup command is not required. Repeating the command refreshes this tool from the current checkout.

Each operation is a single script call. The installer runs `setup codex` to register both MCP executables. Append the relevant options to the command above:

| Option | Operation |
| --- | --- |
| `--dry-run` | Print the installer plan without installing or invoking setup. The future tool bin path is symbolic until a real run. Direct `setup codex --dry-run` reads configuration and preflights only the two target sections; it starts no MCP subprocess and writes nothing. |
| `--python VERSION` | Choose the uv-managed Python version instead of the default `3.14`. |
| `--help` | Show usage without installing or configuring anything. |

The script validates arguments and required commands before installation. A failed stage stops subsequent stages and returns a nonzero status. Installation and registration are separate effects: if setup fails after installation, the refreshed tool remains installed; inspect setup's partial-state report before rerunning. Existing registration-preservation and forwarding checks remain in the setup helper. Reload the affected servers after success; the script does not restart the client or supply credential values.

Setup registers both executable names above with verified absolute executable paths and empty argument lists. It merges the required API and optional proxy environment-variable names; the tools executable also forwards `OPENAI_TIMEOUT_MAX_RETRIES`. It updates only these two target tables, preserving their other settings and unrelated configuration. It does not inspect or migrate other registrations. See [Two MCP executables and Codex registration](TOOLS_REGISTRATION.md). Users who prefer separate registration can use the two direct commands above.

The administrative command resolves its own path from the running installation's scripts directory and exact distribution entry-point metadata. Each MCP executable uses its startup working directory as the project root; this does not establish host identity.

The installed command's `setup codex --dry-run` reports the planned paths and empty argument lists for the two target registrations without writing configuration. Real setup resolves the current installed executables, verifies their `tools/list` inventories, and atomically upserts only their two target tables. It preserves other settings in those tables and unrelated configuration. The update preserves file mode, rejects unsupported TOML layouts, and checks that the input file has not changed before replacement. Avoid concurrent configuration writers; this check is not a global lock. Captured configuration and subprocess output are not printed.

If both target tables already match, setup is a no-op. It does not rewrite unrelated entries or manage other server registrations. It never prints configuration values or subprocess output.

The protocol target remains `2026-07-28`. SDK subprocess tests verify negotiation and calls; actual trusted host integration remains separate evidence.

### Codex stdio environment forwarding

The installer already handles forwarding through setup. For a forwarding-only repair of the two executable registrations, run the [standalone repair script](../scripts/configure-codex-mcp-env.py) once from any working directory:

```sh
uv run --managed-python -- /absolute/path/to/skill/scripts/configure-codex-mcp-env.py --server token-io-decoupling-tools
```

Repeat `--server token-io-decoupling-workflow` to update the workflow registration in the same file operation.

Add `--dry-run` to preview instead of writing. Alternatively, an existing installation offers the same operation as `token-io-decoupling setup codex-env --server NAME`; these are alternatives, not sequential steps. Repeat `--server NAME` to update multiple existing stdio registrations in one file operation. The default names to merge are `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and the four lowercase proxy forms; repeat `--env-var NAME` to supply a custom name list instead. `--config /absolute/path/config.toml` selects a file explicitly; otherwise the target is `$CODEX_HOME/config.toml`, or `~/.codex/config.toml` when `CODEX_HOME` is unset. The script uses PEP 723 metadata to obtain TOML Kit through uv and imports the helper from this checkout, so it does not require an installed MCP package or Codex CLI. The installed command uses the same helper.

The helper merges only selected `env_vars`, preserving other names, comments, settings, and file mode. Repeated successful runs with no missing names leave file bytes and modification time unchanged. It writes through a temporary file in the same directory and detects changes to its input before replacement; avoid concurrent configuration writers, since this is not a cross-client transaction. Missing files or server entries, non-stdio servers, invalid TOML/field types, symlink targets, conflicting remote sources for requested variables, and write failures return safe errors. It creates no server entries, prints no configuration values, and makes no API request. `--dry-run` for this repair reads and validates the selected file but writes nothing; the setup dry-run above reads configuration and preflights only the two target sections, without starting an MCP subprocess or writing.

TOML Kit documents a formatting exception for out-of-order subtables that extend an array of tables. The locked version also normalizes that layout. Before a planned repair write, the helper checks that the unmodified document round-trips byte-for-byte; unsupported layouts are rejected without writing, rather than silently moving unrelated content. Registration setup applies the same check before its atomic configuration update. An already-complete standalone repair remains a no-op even on such a layout.

The following partial example illustrates the two default registrations. Preserve existing `command`, `args`, approvals and additional forwarded names when editing manually; the `tools` entry also needs its `OPENAI_TIMEOUT_MAX_RETRIES` forwarding declaration:

```toml
[mcp_servers.token-io-decoupling-workflow]
env_vars = [
  "OPENAI_API_KEY", "OPENAI_BASE_URL",
  "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
  "http_proxy", "https_proxy", "all_proxy", "no_proxy",
]

[mcp_servers.token-io-decoupling-tools]
env_vars = [
  "OPENAI_API_KEY", "OPENAI_BASE_URL",
  "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
  "http_proxy", "https_proxy", "all_proxy", "no_proxy",
  "OPENAI_TIMEOUT_MAX_RETRIES",
]
```

Codex must itself have both nonblank API variables and any desired proxy variables in its environment. `env_vars` allows and forwards the corresponding values to each separately launched MCP process; it neither loads Shell configuration or `.env` files nor copies another terminal's environment. Store no actual values in repository files, setup arguments, logs, or examples. See the [Codex MCP configuration reference](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Both MCP registrations receive the forwarding merge during setup. The installation script includes setup automatically; a bare `uv tool install` still does not register servers or supply credentials. Reload the affected MCP servers after configuration changes; if the client has no reload mechanism, quit and reopen it so new service processes are created. Running processes do not automatically receive changed configuration.

When a terminal invocation works but an MCP request reports missing configuration, check the client process environment, each registration's forwarding names, and whether the service was recreated. Record only variable presence/nonblank status. The current Decisions advisor returns `fallback` with reason `missing_credentials` before creating the SDK client when either required value is absent or blank; do not assume another service's `missing_api_key` error name applies here. Forwarding does not enable API requests, grant outbound-data authorization, or establish a local session context; the separate requirements below still apply.



## Local stdio workflow navigation

The standard local stdio tools provide bounded, stateless workflow-rule navigation and structural checks over caller-supplied facts. They do not maintain thread, project, Root, Worker, allocation, or checkpoint state between calls. The startup working directory scopes project-local read-only Memory helpers; it does not establish caller identity or authorization.

The separate output materializer is unavailable by default and requires trusted startup context, an independent operator grant, and matching per-call binding. See [Output materialization](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/output-materialization.md) and [caller context](CODEX_CALLER_CONTEXT.md) for the actual guard boundaries. Installed-package checks verify stdio discovery and bounded behavior; the final SDK inspection remains limited to version, discovery, capabilities, and rules, with no model turns or mutations.

## Required configuration for real API requests

All six OpenAI client construction paths use the shared HTTPX2 client builder with explicit `trust_env=True`, preserving the SDK's connection limits and redirect defaults, each operation's timeout, and `max_retries=0`. It reads `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and `NO_PROXY`, including their lowercase forms, from the MCP process environment when creating a client. [HTTPX2 environment rules](https://pydantic.dev/docs/httpx2/api/environment_variables/) determine proxy selection and bypasses. `NO_PROXY` can allow a direct route; without proxy configuration, normal direct routing remains available. Invalid or unreachable proxies follow the existing safe API failure results; the server does not retry them through a direct route. Closing the SDK client also closes its HTTPX2 client, and an SDK construction failure closes the newly created HTTP client.

For an existing installation, update the tool, run `token-io-decoupling setup codex` to register/update both MCP executables and merge their forwarding names, then reload the MCP servers. Proxy variables must be present in the launching Codex process, not just an unrelated terminal. Setup persists names only and requires no proxy values as arguments. No system proxy or user configuration is changed merely by calling an API tool.

Root and every delegated Agent must follow this constraint in both project functionality and test/smoke code: immediately before any real API request, read both `OPENAI_API_KEY` and `OPENAI_BASE_URL` from the local process environment. Both values must be present and nonempty; whitespace-only values are invalid too. If either is missing or invalid, do not create the SDK client or send a real request; return to the documented fallback instead.

Do not substitute a hardcoded key or endpoint, caller-supplied replacement, or the SDK's default endpoint. Read the two local values at invocation time and pass them explicitly to the SDK. Never print or persist their values. Synthetic configuration is permitted only for mocks that send no network requests.

Optional checkpoint advice remains disabled by default. Its real requests additionally require explicit enablement and authorization for outbound data; this document alone grants neither. The ordinary test suite uses mocks, while a real smoke test requires a separate explicit opt-in and must obey the same two-variable requirement.

The checkpoint tools perform deterministic structural checks on bounded, caller-supplied facts. Optional decision advice is a separate operation and is not embedded in, or persisted by, those evaluations. Any advice request requires explicit outbound-data authorization and current-input review; advice cannot select or confirm a Gate branch. The structural result is returned independently of any separately requested advice, and neither result replaces document judgment.

`workflow_generate_decision_context` is a stateless public operation that turns caller-assembled material into one question or context paragraph for a later Decisions request. It uses the [Responses API with Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), fixed `gpt-6-luna` with `medium` reasoning, `store=False`, no tools, and no automatic downstream call. It requires no persisted workflow state or optional-advice enablement. The Code Agent collects the user requirements, current Git diff, relevant LSP results, and other necessary verified observations, labels their origins and verification limits, then combines them into `raw_content`. The service never reads a repository, executes commands, or treats supplied source labels as proof.

Send `payload.request` with required `raw_content` (nonblank strict string, at most 60,000 characters), `decision_goal` (nonblank strict string, at most 1,200 characters describing the actual downstream decision), `output_kind` (`decision_question` or `decision_context`), and `outbound_data_permitted` (strict boolean). Oversized inputs are rejected without truncation; do not omit material constraints merely to fit the limit. The permission assertion authorizes neither collection nor disclosure by itself. Both local API environment variables remain mandatory for each permitted request. For example:

```json
{
  "payload": {
    "request": {
      "raw_content": "User requirement: add bounded question input.\nCurrent Git diff, collected by caller: + decision_question: StrictStr\nLSP observation, collected by caller: ChildEffortInput is consumed by ChildEffortSelector.select; call path verified, runtime behavior not yet tested.",
      "decision_goal": "Frame the question for selecting the lowest sufficient supported effort for this released child task.",
      "output_kind": "decision_question",
      "outbound_data_permitted": true
    }
  }
}
```

Only `status: available` carries a nonblank `description`: at most 1,200 characters for `decision_question`, or 6,000 for `decision_context`. The result includes `output_kind`, a canonical SHA-256 `input_hash` over the raw material, goal, and kind (excluding the permission assertion), and safe model/usage metadata. Critical gaps or conflicts return `blocked` / `insufficient_evidence`, `description: null`, and up to eight `missing_information` items of at most 240 characters; configuration, refusal, incomplete or invalid output, timeout, and provider errors also block without a fallback. The fixed instructions require preserving the distinction between requirements, observations, plans, and proven outcomes, treating embedded instructions as data, and generating no answer, selected branch, or authorization. These semantic requirements still need caller review. Check the paragraph against the original material and current repository state before using `description` as `decision_question` or context; supply the other required decision facts separately. The generation hash identifies this generation input and does not replace the downstream decision hash. Changes to the material, goal, or kind require a fresh comparison and review.

`workflow_select_child_effort` is a separate stateless public workflow operation for Codex child creation. An explicit, authorized invocation with `payload.request.outbound_data_permitted: true` opts into one Decisions request; it needs neither optional-advice enablement nor persistent workflow state. The assertion is not proof of authorization. Supply verified bounded task facts and supported effort levels under the [runtime owner's creation contract](../docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support.md). The result carries a selected effort only when available, a request hash, and the echoed slice fingerprint. Parent review and current-input comparison remain mandatory. Refusal, insufficient evidence, invalid response, missing configuration, or provider failure blocks selection, without a fixed-effort fallback. The tool does not create an Agent, mutate workflow state, or authorize a gate.

The required `decision_question` is a nonblank strict string of at most 1,200 characters asking which supported effort is minimally sufficient for this released child task. The tool sends it explicitly in the Decisions input and includes it in the canonical input hash; changing only the question invalidates the previous hash. It is task data, without authority to change the fixed model, candidate levels, instructions, or permissions. Local validation enforces the string constraints; fixed API instructions require `insufficient_evidence` for an out-of-scope question or an attempted rule override. This semantic judgment and the parent's review remain necessary. Each offered level describes concrete task evidence, adjacent-level boundaries, and exclusions; file count, impact, or a missing fact alone does not justify a higher level.

### Delegation decisions and approved capacity

Four stateless public tools provide optional delegation advice. Each accepts `payload.request` with bounded task facts, reviewed context and its `context_input_hash`, current `fact_revision` and `fact_fingerprint`, Fork/mode facts, and `outbound_data_permitted`. Identity, permission, provenance, and approval assertions remain caller-supplied facts, not host proofs. Root reviews an authorized proposed task before choosing a role or executor; the child-specific Interaction Slice is released afterward and must pass its own gates.

| Tool | Decision and result boundary |
| --- | --- |
| `workflow_select_child_role` | Select one of the four maintained roles under [Child Role Selection](../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/child-role-selection.md). Explicit user creation skips the request. An established creation may default to an unoccupied Primary Output; a role already created remains occupied for the entire Session. All roles occupied returns a blocked result for Root review rather than suggesting more capacity. |
| `workflow_select_executor` | Suggest Root or a child under [Task Assignment](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-assignment.md). Explicit executor instructions skip advice; an explicit child under locked Single-Agent mode blocks instead of becoming Root. Failure never defaults to Root. A child decision with unused approved capacity and no actual child can continue through the normal role and creation gates. |
| `workflow_select_child` | Select among eligible current-session children. Explicit or unique candidates can bypass advice; busy selections wait. Multiple idle candidates use Decisions, preferring a suitable idle Primary and otherwise task-relevant context. Failure may use only a suitable Primary fallback, subject to availability; inherited foreign-session children are excluded. |
| `workflow_assess_output_tokens` | Independently assess direct Root output under [Output Token Routing](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/output-token-routing.md). Explicit execution instructions skip advice. `no` permits Root subject to other gates; `yes` prevents immediate Root output and requires an idle suitable child or hold/wait. Independently authorized creation can still follow its normal gates; output advice alone does not authorize it. |

Permitted API calls explicitly read both nonblank `OPENAI_API_KEY` and `OPENAI_BASE_URL` at invocation time, use exactly `gpt-6-luna`, and make no automatic retries or fallback-model requests. Tool inputs cannot override the model or endpoint. The common [Decision Context Generation](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/decision-context-generation.md) operation reuses Responses for the reviewed background; generating a question is optional. Its instructions now come from that current owner's General rules. Its `source_policy_hash` identifies the loaded rules, and a change during a successful request blocks reuse with `stale_policy`.

The selectors load their current owner instructions and concrete choice descriptions through `RuleLoader`. Results distinguish `available`, `skipped`, `fallback`, `blocked`, and `stale`, with request/context/fact and source-policy hashes. Root must recheck them against current evidence before any effect. Missing configuration or required policy blocks before a request; stale rules require refresh rather than fallback. No selector creates a child, dispatches work, changes a budget, or establishes trusted binding. These tools accept one already bounded task; they do not decompose an instruction into multiple tasks.

### Component optimization measurement

The [optimization benchmark](OPTIMIZATION_BENCHMARK.md) owns the fixed-case measurement protocol, raw-result links, provenance, and observed token/call/latency/repair/failure results. It compares direct service components through real reference-caller API requests, separately from MCP transport, the current Agent's usage, and fresh-CLI inspection. Its archived first protocol and single corrected run remain available; consult that guide for the measured limits and reproduction authorization.

### Real API integration tests

The `real_api` cases under `tests/real_api_tests/` exercise real Responses context generation, child-effort Decisions, the negotiated in-process MCP generation-to-effort chain, and the four delegation decisions: new-child role, Root/child executor, existing-child selection, and output-token routing. They use synthetic requirements, diff text, Session facts and LSP observations rather than collecting repository or host data. Delegation cases generate and review context before requesting a decision, then check the expected result, input hash and current policy hashes. These checks establish live API and MCP-handler behavior; they do not prove a trusted desktop-host binding or stable semantic rankings.

Ordinary pytest runs collect and skip these cases before credentials or clients are accessed, even when credentials exist. Only the exact opt-in `TOKEN_IO_RUN_REAL_API=1` enables them. Once enabled, a missing or blank `OPENAI_API_KEY` or `OPENAI_BASE_URL` fails the tests instead of skipping them or using mocks. Requests use the configured endpoint and fixed `gpt-6-luna`; there is no endpoint/model fallback or automatic retry. The test scope suppresses SDK/HTTP logging and reports safe status/reason data without credentials, endpoint values, or raw provider errors. After explicit authorization, run from `mcp/`:

```sh
TOKEN_IO_RUN_REAL_API=1 uv run --managed-python --locked -- pytest -m real_api tests/real_api_tests/ -q
```

The separate [official HTTPX2 smoke test](tests/real_api_tests/test_official_httpx2.py) uses `OPENAI_API_KEY_OFFICAL` and `OPENAI_BASE_URL_OFFICAL` (the `OFFICAL` spelling is intentional) under its own `TOKEN_IO_RUN_OFFICIAL_API=1` opt-in. This test-only configuration choice does not change the production tools' required variable names. It calls the shared HTTPX2 builder and sends one short Responses request to fixed `gpt-6-luna`, with a 60-second timeout, no retries and `store=False`. It validates completed nonempty text and reports only safe status and whether the configured transport selected a proxy; it prints no credentials, URLs, response body or raw provider error. A false proxy flag means the configured route was direct, including a possible `NO_PROXY` bypass. Without its opt-in it skips before reading the two variables. After authorizing this real request, load the variables and run from `mcp/` in Zsh:

```sh
source ~/.zshrc
TOKEN_IO_RUN_OFFICIAL_API=1 uv run --managed-python --locked -- pytest tests/real_api_tests/test_official_httpx2.py -q -s --tb=no
```

## Build, rule resources, and installed checks

Build all eight wheels and source distributions from `mcp/`:

```sh
uv build --all-packages --managed-python --python 3.14 --out-dir /tmp/token-io-dist
```

The core package owns rule resources and its custom build hook. The canonical registry remains `mcp/rule-registry.json`; build output contains bounded excerpts from its English/Chinese owner headings. The independent version 1 fragment index and its fragment resources are built from authoritative owner sections with a shared fence-aware parser and normalization. Source and packaged resources therefore produce the same fragment text and hashes; the build does not hard-code a Skill installation path or borrow a neighboring checkout. Core sdists carry their own `rule_sources`. The default `token_io_decoupling_core.rules.RuleLoader` reads packaged snapshots; source development must explicitly supply the repository root. Editing Markdown does not update an installed wheel: rebuild and reinstall it.

Rule loading trims leading/trailing whitespace before returning text and calculating context or policy hashes; internal whitespace is preserved. Source and packaged loaders therefore agree for the same registry and rule content even when a text resource has a final newline. This corrects older package hashes that included packaging whitespace. The existing `rules_get_context` call and output/hash remain unchanged when `context_version` is omitted. Any fragment-bundle extension such as `fragment_ids` or `max_chars` requires explicit `context_version=1`; unversioned extensions are rejected. Version 1 `max_chars` counts Unicode characters in fragment text (not tokens), defaults to 12,000, and is limited to 256–60,000; fragments are not truncated, and missing required content or insufficient budget is returned as incomplete. Bundle completion covers only the requested index dependency closure, not all task rules or linked owners. After upgrading, read current rule contexts and policy hashes again and re-evaluate affected stale results; do not rewrite historical records or reuse cached pre-upgrade hashes.

The local Skill directory and the MCP tool environment are separate snapshots. `skills install/update` writes only the selected `~/.agents/skills/` installation; it does not change the MCP executable, packaged rules, or Codex registrations. The MCP does not import the installed Skill or its `_project/` supporting attachments. `rules_get_context.owner_path` identifies the canonical repository source under `docs/skill/`, not a path to resolve against the local Skill directory. `_project/` manifests and CI files are reference copies, not live server configuration. To keep instructions and server rules aligned, reinstall the same tool build, run `skills update`, reload the MCP servers, and start a fresh Agent session; separate updates can otherwise leave different snapshots active.

The build also packages General rules in both languages for eight allowlisted owners: `child-role-selection`, `task-assignment`, `output-token-routing`, `session-role-ownership`, `decision-context-generation`, `workflow-routing-advice`, `candidate-compliance`, and `output-materialization`. The original five remain the delegation-policy allowlist. The three new owners supply optional version 1 fragments: `decision.workflow_routing_advice`, `implementation.candidate_compliance`, and `implementation.output_materialization`; the last depends on candidate compliance. The 17 Core checkpoint IDs and their default fragment roots remain unchanged. `tests/unit_tests/test_build_artifacts.py` verifies detached sdist-to-wheel builds and bilingual source/packaged text and hash parity.

The launcher build regenerates its Skill snapshot zip when the Skill source markers and canonical compliance helper are present, so a matching old helper cannot hide changed documentation. A detached build without those sources requires a bundled snapshot with unique safe entry paths, valid CRCs, and all six required Skill/metadata/helper/loader/checker text entries containing non-whitespace UTF-8. It also checks helper parity when the canonical helper is available. This validates those required entries, not every document's semantics or completeness. Missing or invalid snapshots fail the build. Regression tests exercise fresh-source rebuilding, valid detached fallback, and CRC-valid snapshots with empty required entries.

The [MCP CI workflow](../.github/workflows/mcp.yml) runs locked checks on managed Python 3.11 and 3.14 and a separate installed-wheel job. Export third-party build/runtime constraints with `uv export --no-emit-workspace` (plus `--all-groups` for builds or `--no-dev` for runtime). Workspace members are supplied by the local artifacts, not editable requirements. To install from the detached wheel set, use its directory as `--find-links` and install the root `token_io_decoupling-0.1.0-py3-none-any.whl`; retain the configured index for locked third-party dependencies. See CI for the complete commands.

For temporary installation, set command-local `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` to absolute temporary directories. Run `tests/support/installed_stdio_smoke.py --cli /absolute/temporary/bin/token-io-decoupling` with the locked workspace interpreter. It starts the two separate MCP executables outside the checkout with an empty `PYTHONPATH`, verifies their exact inventories and binding rejection, checks both rule languages, and runs setup dry-run with an empty `PATH`. Source-root tool installation is checked separately. These results prove packaging and stdio behavior, not actual host binding or a GitHub Actions run.

The [documentation workflow](../.github/workflows/multilingual-docs.yml) retains multilingual/link/route validators and scanner regressions; it prunes generated resources and environments while checking authored workspace documentation.
