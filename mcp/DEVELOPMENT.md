# MCP workspace development guide

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

This guide owns development, artifact checks, uv tool installation, and Codex setup for the Python workspace. The [architecture contract](../ENHANCED_ARCHITECTURE.md#implementation-packages) owns package responsibilities and dependency direction; the [Skill entry](../SKILL.md) and its linked owners remain the workflow authority.

The MCP Server supports only Codex and ChatGPT Desktop. Follow the [directory instructions](AGENTS.md); development under `mcp/` does not maintain compatibility with other Code Agents. Supported scope does not establish a verified host adapter.

## Environment and checks

The workspace contains eight independently buildable distributions, each with its own `pyproject.toml`, and one shared `uv.lock`. Only the root distribution, `token-io-decoupling`, exports a console script. Run these commands from `mcp/` using managed Python and locked dependencies:

```sh
uv sync --managed-python --locked --all-packages --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

`ty` covers root sources, tests, library packages, and the core build hook. Set `UV_PROJECT_ENVIRONMENT` to an absolute temporary directory to keep the environment outside the checkout. The default suite uses temporary databases and offline transport; live API tests require explicit opt-in. Run the documentation checks required by [repository instructions](../AGENTS.md) from the repository root.

### Test organization

Classify every new or changed test by its actual dependencies and behavior:

| Directory | Responsibility |
| --- | --- |
| `tests/mock_api_tests/` | Tests that replace collaborators, host bindings, API clients or HTTP transport with mocks, fakes or stubs. |
| `tests/unit_tests/` | Deterministic local unit tests that exercise the real tested code without mocked collaborators or live API calls. |
| `tests/real_api_tests/` | Explicitly opted-in tests and smoke scripts that send real Decisions or Responses requests. |

Split mixed modules by test case; a marker or filename does not replace correct placement. Shared fixtures and subprocess helpers may live outside these three case directories, but must not become an unclassified home for test cases. Preserve assertions, parametrization and collection coverage when moving tests, and update imports, repository-root discovery and CI/script references together. Ordinary pytest must collect and skip live cases without reading credentials or sending requests. The same placement rules apply to future tests.

## Unified launcher and profile tools

The installed command is `token-io-decoupling`. Select a profile at startup:

```sh
token-io-decoupling start-mcp-server --profile workflow
```

`--profile` accepts `workflow`, `root`, `worker`, or `share`. Omitting the subcommand starts stdio with the workflow profile; `--version` prints the launcher version. Each profile has a fixed, disjoint inventory:

| Profile / Codex server registration | Tools |
| --- | --- |
| `workflow` / `token-io-decoupling-workflow` | `workflow_capabilities`, `rules_get_context`, `workflow_generate_decision_context`, `workflow_select_child_effort`, `workflow_select_child_role`, `workflow_select_executor`, `workflow_select_child`, `workflow_assess_output_tokens`, `workflow_evaluate`, `evaluate_control_checkpoint` |
| `root` / `token-io-decoupling-root-agent-tools` | `workflow_open`, `delegation_reserve`, `delegation_unreserve`, `delegation_bind`, `slice_check`, `slice_release`, `workflow_transition`, `parent_get_worker_summary`, `workflow_reconcile` |
| `worker` / `token-io-decoupling-worker-agent-tools` | `worker_get_assignment`, `worker_record_progress`, `worker_get_evidence`, `worker_report_blocker`, `worker_get_recovery_context` |
| `share` / `token-io-decoupling-share-tools` | `database_schema_status`, `state_get`, `record_evidence` |

A profile controls discovery, not authority. Without a trusted host channel, public capability/rule reads succeed, schema status reports unavailable without inspecting state paths, and protected calls reject the missing binding. Workflow/Control evaluation requires a verified Root. Shared reads and evidence writes resolve the verified role on every invocation; Worker reads reject a non-null Root `index_page` cursor.

Canonical Python implementations use the independent package names shown in the architecture contract. The renamed `token_io_decoupling_mcp` adapter namespace carries the former facade modules and default factory's public-only behavior; `python -m token_io_decoupling_mcp.cli` remains available. The old `token_io_mcp` import namespace is not exposed as a general API. The two immutable v1 migration sources retain `token_io_mcp.models` in their historical bytes; the state migration loader provides a temporary alias for `DatabaseKind` only while importing those modules, then removes it. Use the renamed adapter paths for direct migration imports; importing frozen state migration modules directly bypasses the scoped loader and is unsupported. Compatibility files are owned by core, state, or launcher without duplicate wheel paths. The old four console scripts and the former `token-io-mcp` console script are not exported by this workspace.

## Capability report diagnostics

`workflow_capabilities({})` is public and takes no arguments. It preserves top-level summaries and adds `capability_details` with `schema_version: 1`. Each detail contains `status`, `reason_code`, a safe `message`, diagnostic `source`, and `next_step`.

| Detail group | Meaning and boundary |
| --- | --- |
| `support.host_adapters` | Static built-in Desktop identity/guard support: `unavailable/adapter_not_implemented`. This is not a provider probe; an injected trusted provider may still verify. |
| `configuration.caller_match` | Startup `required/configured_required` or `disabled/configured_disabled`. Public discovery does not verify request caller metadata. |
| `configuration.api_decisions` | Persisted advice `enabled/configured_enabled` or `disabled/configured_disabled`. Disabled is normal configuration. Per-invocation tools remain separate; no API readiness is tested. |
| `runtime.binding` | Current session relationship and baseline guards. Success includes only role (`parent` or `worker`), never identity values; operation-specific authorization remains separate. |
| `runtime.binding_transport` | Type classification: known inherited host channel `available/known_transport`; custom provider `unverified/transport_not_reported`. Recognizing a type does not prove current channel health. |
| `runtime.server_mode` | Startup admission (`embedded` or `public_only`). Later diagnostics never expand registered scope or bypass checks. |

Binding diagnostic outcomes:

| Status / reason code | Evidence and next action |
| --- | --- |
| `unverified/provider_not_configured` | Default denying provider; no probe attempted. Use Native or configure a trusted host integration. |
| `available/baseline_verified` | Session relationship and baseline guards passed. Check intended-operation guards and caller context separately. |
| `unavailable/required_guards_missing` | Baseline guards are absent. Correct the host binding without bypassing checks. |
| `unavailable/session_identity_mismatch` | Role/session relationship is invalid. Correct host-supplied identity. |
| `unavailable/permission_denied` | Provider raised `PermissionError` other than `BindingError`. Have the host owner check permissions. |
| `unknown/binding_unavailable` | `BindingError` cannot distinguish denial, timeout, or protocol failure. Consult trusted host diagnostics rather than guessing. |
| `unknown/probe_failed` or `unknown/invalid_binding_response` | Unexpected exception or invalid typed result. Repair the provider before protected use. |

`BindingError` inherits `PermissionError`, so it is classified first. A report reads the binding at most once, may contact the configured host channel, and makes no API request or state/path inspection. Fixed explanations never echo exceptions, credentials, identity values, paths, or arbitrary provider attributes.

Legacy non-embedded summaries remain `enhanced_binding: unverified` and `binding_transport: unavailable`, even if a later probe succeeds; details separate current validation from startup admission. Embedded binding summaries remain `available`/`unavailable`. Transport summaries use only `authenticated_inherited_unix_socket` or `embedded_provider`, never custom labels. No result automatically enables Enhanced or grants authority.

### Installed client runtime checks

The `real_client` cases in `tests/unit_tests/test_real_clients.py` run the actual installed Codex CLI and the Codex executable shipped inside ChatGPT Desktop. They exercise each executable's app-server MCP interface without mocked client transport or host identity. This covers the MCP host-runtime boundary, not Desktop GUI interaction, an already-running daemon, or authenticated Enhanced host binding.

After authorization for temporary test threads and processes, run from `mcp/`:

```sh
TOKEN_IO_RUN_REAL_CLIENTS=1 uv run --managed-python --locked -- pytest -q -s tests/unit_tests/test_real_clients.py
```

The CLI defaults to `codex` on `PATH`; Desktop defaults to `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`. `TOKEN_IO_CODEX_CLI_PATH` and `TOKEN_IO_DESKTOP_CODEX_PATH` may point to other actual installations. Overrides are caller-supplied paths, not proof of client identity. Evidence includes the resolved executable path, actual version, executable SHA-256, tested source fingerprints, and successful checks; changing the JSON-RPC client name does not establish client coverage.

Each case starts a separate real app-server with a process-local `mcp_servers` override that disables inherited configured servers using safe placeholders and enables the current workspace's workflow server. Only configured server names and transport types are read; URLs, arguments, environment values, and credentials are not copied. It asserts that inherited configured servers expose no tools; clients may retain built-in platform services, which the test never invokes. It verifies the target's no-argument schema and new description, calls `workflow_capabilities` and checks structured diagnostics, and confirms that `workflow_evaluate` rejects the missing trusted binding. It uses one ephemeral thread, starts no model turn, and terminates its owned process group to release the memory-only thread and MCP subprocess. No user configuration or installed MCP package is changed, and no model API request is needed for this capability check. The operating environment must permit launching and cleaning up these processes.

Ordinary pytest skips both cases without probing installed clients. Explicit opt-in makes missing clients, permission failures, protocol errors, or old capability responses fail rather than skip or fall back to a fake. Existing SDK, Mock, and installed-stdio checks retain their narrower scope. A passing runtime check does not prove an existing client session has reloaded an updated MCP installation; that session still needs its own installation/reload verification.

## uv tool installation and Codex setup

Use the [installation script](../scripts/install-codex-mcp.sh) to install or update the package and configure Codex in one invocation, from any working directory:

```sh
bash /absolute/path/to/skill/scripts/install-codex-mcp.sh
```

Prerequisites are Bash 3.2 or later (including macOS `/bin/bash`), `uv`, and the Codex CLI; `uv` and `codex` must be on `PATH`. The script locates `mcp/` relative to itself, runs `uv tool install --force --reinstall --managed-python --python 3.14` against that source, obtains the bin directory with `uv tool dir --bin`, then calls the absolute installed executable's `setup codex`. uv resolves the declared local workspace dependencies; `--reinstall` refreshes them even when only their source or packaged rules changed. The tool bin directory need not be on `PATH`, and no manual directory change, virtual-environment activation, or separate setup command is required. Repeating the command refreshes this tool from the current checkout; it does not uninstall the legacy `token-io-mcp` tool.

Each operation is a single script call. Append the relevant options to the command above:

| Option | Operation |
| --- | --- |
| `--dry-run` | Print the install and setup plan without running installation/setup commands or reading/writing configuration. The future tool bin path is symbolic until a real run. |
| `--profile root` | Register only the selected `workflow`, `root`, `worker`, or `share` profile; the installed package still contains all profiles. |
| `--all` | Explicitly select the default four profiles; cannot be combined with `--profile`. |
| `--replace` | Permit setup to replace conflicting or disabled registrations. Omit it to retain conflict rejection. |
| `--python VERSION` | Choose the uv-managed Python version instead of the default `3.14`. |
| `--help` | Show usage without installing or configuring anything. |

The script validates arguments and required commands before installation. A failed stage stops subsequent stages and returns a nonzero status. Installation and registration are separate effects: if setup fails after installation, the refreshed tool remains installed; inspect setup's partial-state report before rerunning. Existing registration-preservation and forwarding checks remain in the setup helper. Reload the affected servers after success; the script does not restart the client or supply credential values.

Setup registers all four server names above using one verified absolute executable path and profile-specific arguments, and automatically merges the two required environment-variable names into their `env_vars`. Users who already manage tool installation separately can still invoke `token-io-decoupling setup codex` directly. For example, register and repair forwarding for only the root profile with one installed-command call:

```sh
token-io-decoupling setup codex --profile root
```

The setup separation follows [Serena's client setup implementation](https://github.com/oraios/serena/blob/main/src/serena/config/client_setup.py). Our launcher resolves its executable from the running installation's scripts directory and exact distribution entry-point metadata. It does not infer a project or identity from the startup directory.

The installed command's `setup codex --dry-run` prints the selected JSON argument vectors and a variable-name forwarding plan, without subprocesses or configuration reads/writes. Real setup validates the local configuration and probes the CLI before registration writes. It reads the listing and nested `transport` data. Enabled registrations with the same resolved command and `start-mcp-server --profile <profile>` arguments skip re-registration but still receive missing forwarding names. Conflicting or disabled entries require `--replace`. Replacement uses the official same-name upsert, without deleting first. A later forwarding failure is reported separately from registrations already applied; inspect the named partial state before retrying. Captured configuration and subprocess output are not printed.

Because the Codex upsert replaces a registration, setup keeps the previous settings in memory and restores them with forwarding after each successful upsert, before processing the next profile. Stdio replacement preserves additional settings and forwarded names while changing the launcher, profile arguments and intended enabled state. HTTP-to-stdio replacement preserves common tool policies and timeouts, but removes the old transport and authentication fields. If a later profile fails, the report distinguishes completed registrations/forwarding from pending work. Use setup for replacements that must preserve these settings.

After the new launcher and registrations are verified, a migration from this repository's old four-command tool can remove that old distribution with `uv tool uninstall token-io-mcp`. Preserve unrelated tools, servers and settings, and reconnect the MCP client to load the new launch command. Setup does not establish a trusted host binding.

The protocol target remains `2026-07-28`. SDK subprocess tests verify negotiation and calls; actual trusted host integration remains separate evidence.

### Codex stdio environment forwarding

The installer already handles forwarding through setup. For a forwarding-only repair of existing registrations, run the [standalone repair script](../scripts/configure-codex-mcp-env.py) once from any working directory:

```sh
uv run --managed-python -- /absolute/path/to/skill/scripts/configure-codex-mcp-env.py --server dev-workflow-standards-tools
```

Add `--dry-run` to preview instead of writing. Alternatively, an existing installation offers the same operation as `token-io-decoupling setup codex-env --server NAME`; these are alternatives, not sequential steps. Repeat `--server NAME` to update multiple existing stdio registrations in one file operation. The default names to merge are `OPENAI_API_KEY` and `OPENAI_BASE_URL`; repeat `--env-var NAME` to supply a custom name list instead. `--config /absolute/path/config.toml` selects a file explicitly; otherwise the target is `$CODEX_HOME/config.toml`, or `~/.codex/config.toml` when `CODEX_HOME` is unset. The script uses PEP 723 metadata to obtain TOML Kit through uv and imports the helper from this checkout, so it does not require an installed MCP package or Codex CLI. The installed command uses the same helper.

The helper merges only selected `env_vars`, preserving other names, comments, settings, and file mode. Repeated successful runs with no missing names leave file bytes and modification time unchanged. It writes through a temporary file in the same directory and detects changes to its input before replacement; avoid concurrent configuration writers, since this is not a cross-client transaction. Missing files or server entries, non-stdio servers, invalid TOML/field types, symlink targets, conflicting remote sources for requested variables, and write failures return safe errors. It creates no server entries, prints no configuration values, and makes no API request. `--dry-run` for this repair reads and validates the selected file but writes nothing; the registration dry-run above deliberately does not inspect configuration.

TOML Kit documents a formatting exception for out-of-order subtables that extend an array of tables. The locked version also normalizes that layout. Before a planned repair write, the helper checks that the unmodified document round-trips byte-for-byte; unsupported layouts are rejected without writing, rather than silently moving unrelated content. Registration setup applies the same check during preflight, before upserts. An already-complete standalone repair remains a no-op even on such a layout.

The following partial example illustrates the resulting settings. Preserve existing `command`, `args`, approvals and additional forwarded names when editing manually:

```toml
[mcp_servers.token-io-decoupling-workflow]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]

[mcp_servers.token-io-decoupling-root-agent-tools]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]

[mcp_servers.token-io-decoupling-worker-agent-tools]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]

[mcp_servers.token-io-decoupling-share-tools]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
```

Codex must itself have both nonblank variables in its environment. `env_vars` allows and forwards their names to each separately launched MCP process; it neither loads Shell configuration or `.env` files nor copies another terminal's environment. Store no actual values in repository files, setup arguments, logs, or examples. See the [Codex MCP configuration reference](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Both new and matching registrations receive the forwarding merge during setup; `--replace` is followed by the same merge. The installation script includes setup automatically; a bare `uv tool install` still does not register servers or supply credentials. Reload the affected MCP servers after configuration changes; if the client has no reload mechanism, quit and reopen it so new service processes are created. Running processes do not automatically receive changed configuration.

When a terminal invocation works but an MCP request reports missing configuration, check the client process environment, each registration's forwarding names, and whether the service was recreated. Record only variable presence/nonblank status. The current Decisions advisor returns `fallback` with reason `missing_credentials` before creating the SDK client when either required value is absent or blank; do not assume another service's `missing_api_key` error name applies here. Forwarding does not enable API requests, grant outbound-data authorization, or establish a trusted host binding; the separate requirements below still apply.



## Authenticated host channel

`HostChannelBindingProvider` and `serve_host_binding_channel` in `token_io_decoupling_core.host_binding` connect the CLI to a trusted host's existing `BindingProvider`. The host attaches one real Session to one connected Unix stream socket outside MCP request arguments. It passes the connected descriptor to an unprivileged CLI process and serves the other end. The supervisor must retain its serving endpoint within the trusted boundary and must not reassign a channel to another Session. The host launches the selected executable, for example `token-io-decoupling start-mcp-server --profile root --host-fd N`, where `N` is an inherited descriptor numbered at least 3; this argument locates a transport and supplies no identity or permission.

The CLI authenticates the peer through operating-system credentials: `SO_PEERCRED` on Linux and the native `getpeereid` call on macOS. This implementation pins the trusted peer to UID 0 and rejects a CLI process running as UID 0. A socket created by the Agent's own user cannot establish trust. Unsupported credential facilities, invalid descriptors, and failed startup binding terminate the requested bound launch. See the [Linux Unix-socket manual](https://man7.org/linux/man-pages/man7/unix.7.html) and [Apple peer-credential manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html) for the kernel mechanisms.

For a bound CLI launch, the state root is `.local/state/token-io-decoupling` beneath the current effective user's home from the operating-system account database. Caller-controlled `HOME` values cannot redirect it; an unavailable or invalid account mapping rejects startup. Trusted Python embeddings retain their explicit `state_root` factory argument.

The bridge pins project, Root, current Session, parent, and role at startup. Every protected call rereads current capability and guard evidence from the host; revocation or an identity change rejects the call. Child verification uses the host's current parent identity. The wire format accepts only the two binding operations, uses bounded frames and a finite timeout, and rejects malformed or mismatched responses without retry. A failed channel cannot regain trust through later responses.

The host must enforce the actual sandbox, path, and Worker-store boundaries before reporting the corresponding guards. Kernel authentication identifies the trusted supervisor; it does not create those guards or prove that a runtime's Session mapping is correct. This package supplies the bridge and host-side serving API, not a privileged service installer or a verified Codex/ChatGPT Desktop runtime integration. A normal MCP client configuration cannot manufacture the inherited privileged channel. Existing test providers and tests that mock peer credentials remain synthetic evidence; the unmodified same-user channel rejection test exercises the real local credential boundary.

Before claiming an actual runtime integration, verify Root initialization, evidence insertion, transition and readback through that runtime's MCP connection; verify a real released and bound Worker can read its assignment and write only its own progress/evidence; and test revocation and cross-Worker rejection with the actual host guards. Restart or reconnect an existing client to load changed startup arguments and tool inventory; editing this checkout does not change an already running MCP process.

[Codex caller matching](CODEX_CALLER_CONTEXT.md) describes the optional `--codex-context` request-matching gate for an already verified host binding. It consumes SDK request metadata and does not add an authentication source.

## Required configuration for real API requests

Root and every delegated Agent must follow this constraint in both project functionality and test/smoke code: immediately before any real API request, read both `OPENAI_API_KEY` and `OPENAI_BASE_URL` from the local process environment. Both values must be present and nonempty; whitespace-only values are invalid too. If either is missing or invalid, do not create the SDK client or send a real request; return to the documented fallback instead.

Do not substitute a hardcoded key or endpoint, caller-supplied replacement, or the SDK's default endpoint. Read the two local values at invocation time and pass them explicitly to the SDK. Never print or persist their values. Synthetic configuration is permitted only for mocks that send no network requests.

Optional checkpoint advice remains disabled by default. Its real requests additionally require explicit enablement and authorization for outbound data; this document alone grants neither. The ordinary test suite uses mocks, while a real smoke test requires a separate explicit opt-in and must obey the same two-variable requirement.

An authorized embedding enables advice with `DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True)` through the factory's `decisions_config` argument. Optional `semantic_input` on the two evaluation tools is limited to task intent, output class, Contract change, verification impact, and Control. The response keeps the Core result separate from advice. With no semantic input, the original Core response is retained. Advice never selects or confirms a Gate branch; stale, invalid, refused, unavailable, or replayed advice returns to document judgment.

`workflow_generate_decision_context` is a stateless public operation that turns caller-assembled material into one question or context paragraph for a later Decisions request. It uses the [Responses API with Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), fixed `gpt-6-luna` with `medium` reasoning, `store=False`, no tools, and no automatic downstream call. It requires no Enhanced binding or optional-advice enablement. The Code Agent collects the user requirements, current Git diff, relevant LSP results, and other necessary verified observations, labels their origins and verification limits, then combines them into `raw_content`. The service never reads a repository, executes commands, or treats supplied source labels as proof.

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

`workflow_select_child_effort` is a separate stateless public workflow operation for Codex child creation. An explicit, authorized invocation with `payload.request.outbound_data_permitted: true` opts into one Decisions request; it needs neither optional-advice enablement nor an Enhanced Root store. The assertion is not proof of authorization. Supply verified bounded task facts and supported effort levels under the [runtime owner's creation contract](../references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support.md). The result carries a selected effort only when available, a request hash, and the echoed slice fingerprint. Parent review and current-input comparison remain mandatory. Refusal, insufficient evidence, invalid response, missing configuration, or provider failure blocks selection, without a fixed-effort fallback. The tool does not create an Agent, mutate workflow state, or authorize a gate.

The required `decision_question` is a nonblank strict string of at most 1,200 characters asking which supported effort is minimally sufficient for this released child task. The tool sends it explicitly in the Decisions input and includes it in the canonical input hash; changing only the question invalidates the previous hash. It is task data, without authority to change the fixed model, candidate levels, instructions, or permissions. Local validation enforces the string constraints; fixed API instructions require `insufficient_evidence` for an out-of-scope question or an attempted rule override. This semantic judgment and the parent's review remain necessary. Each offered level describes concrete task evidence, adjacent-level boundaries, and exclusions; file count, impact, or a missing fact alone does not justify a higher level.

### Delegation decisions and approved capacity

Four stateless public tools provide delegation advice independently of the optional five-checkpoint advisor and Enhanced state. Each accepts `payload.request` with bounded task facts, reviewed context and its `context_input_hash`, current `fact_revision` and `fact_fingerprint`, Fork/mode facts, and `outbound_data_permitted`. Identity, permission, provenance, and approval assertions remain caller-supplied facts, not host proofs. Root reviews an authorized proposed task before choosing a role or executor; the child-specific Interaction Slice is released afterward and must pass its own gates.

| Tool | Decision and result boundary |
| --- | --- |
| `workflow_select_child_role` | Select one of the four maintained roles under [Child Role Selection](../references/coding/layer-01-fundamental-concepts/delegation/child-role-selection.md). Explicit user creation skips the request. An established creation may default to an unoccupied Primary Output; a role already created remains occupied for the entire Session. All roles occupied returns a blocked result for Root review rather than suggesting more capacity. |
| `workflow_select_executor` | Suggest Root or a child under [Task Assignment](../references/coding/layer-01-fundamental-concepts/execution-planning/task-assignment.md). Explicit executor instructions skip advice; an explicit child under locked Single-Agent mode blocks instead of becoming Root. Failure never defaults to Root. A child decision with unused approved capacity and no actual child can continue through the normal role and creation gates. |
| `workflow_select_child` | Select among eligible current-session children. Explicit or unique candidates can bypass advice; busy selections wait. Multiple idle candidates use Decisions, preferring a suitable idle Primary and otherwise task-relevant context. Failure may use only a suitable Primary fallback, subject to availability; inherited foreign-session children are excluded. |
| `workflow_assess_output_tokens` | Independently assess direct Root output under [Output Token Routing](../references/coding/layer-01-fundamental-concepts/execution-planning/output-token-routing.md). Explicit execution instructions skip advice. `no` permits Root subject to other gates; `yes` prevents immediate Root output and requires an idle suitable child or hold/wait. Independently authorized creation can still follow its normal gates; output advice alone does not authorize it. |

Permitted API calls explicitly read both nonblank `OPENAI_API_KEY` and `OPENAI_BASE_URL` at invocation time, use exactly `gpt-6-luna`, and make no automatic retries or fallback-model requests. Tool inputs cannot override the model or endpoint. The common [Decision Context Generation](../references/coding/layer-01-fundamental-concepts/execution-planning/decision-context-generation.md) operation reuses Responses for the reviewed background; generating a question is optional. Its instructions now come from that current owner's General rules. Its `source_policy_hash` identifies the loaded rules, and a change during a successful request blocks reuse with `stale_policy`.

The selectors load their current owner instructions and concrete choice descriptions through `RuleLoader`. Results distinguish `available`, `skipped`, `fallback`, `blocked`, and `stale`, with request/context/fact and source-policy hashes. Root must recheck them against current evidence before any effect. Missing configuration or required policy blocks before a request; stale rules require refresh rather than fallback. No selector creates a child, dispatches work, changes a budget, or establishes trusted binding. These tools accept one already bounded task; they do not decompose an instruction into multiple tasks.

The protected Root `delegation_reserve` accepts optional `budget_approval` only after current unassigned capacity is exhausted. Root must reference actual explicit user approval through `user_approval` and request exactly the current count plus one for a different unoccupied role. Existing binding, guards, revision, and idempotency requirements still apply. The transaction retains the prior source, records the approval, adds one slot, and reserves that role atomically; replay cannot add it twice. Existing unassigned capacity needs no increase. Approval never permits a repeated role or replacement child; see [Delegation Count Gate](../references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md).

Before creation begins, protected Root `delegation_unreserve` can cancel a role reservation so that the same unused slot can be planned again. It requires explicit evidence that creation has not started, current revision and idempotency, and the existing Root binding/guards. It rejects bound or ambiguous identities and any allocation with Slice, dispatch or Worker history. The evidence is a Root attestation, not independent host proof. Cancellation clears only the unused reservation: it neither reduces the locked count nor releases a role or identity after child creation. Refresh allocation facts before selecting or reserving a new role.

### Real API integration tests

The `real_api` cases under `tests/real_api_tests/` exercise real Responses context generation, child-effort Decisions, the negotiated in-process MCP generation-to-effort chain, and the four delegation decisions: new-child role, Root/child executor, existing-child selection, and output-token routing. They use synthetic requirements, diff text, Session facts and LSP observations rather than collecting repository or host data. Delegation cases generate and review context before requesting a decision, then check the expected result, input hash and current policy hashes. These checks establish live API and MCP-handler behavior; they do not prove a trusted desktop-host binding or stable semantic rankings.

Ordinary pytest runs collect and skip these cases before credentials or clients are accessed, even when credentials exist. Only the exact opt-in `TOKEN_IO_RUN_REAL_API=1` enables them. Once enabled, a missing or blank `OPENAI_API_KEY` or `OPENAI_BASE_URL` fails the tests instead of skipping them or using mocks. Requests use the configured endpoint and fixed `gpt-6-luna`; there is no endpoint/model fallback or automatic retry. The test scope suppresses SDK/HTTP logging and reports safe status/reason data without credentials, endpoint values, or raw provider errors. After explicit authorization, run from `mcp/`:

```sh
TOKEN_IO_RUN_REAL_API=1 uv run --managed-python --locked -- pytest -m real_api tests/real_api_tests/ -q
```

The older task-intent advisor smoke remains separate and uses its own opt-in. After explicit authorization for that real synthetic request, run from `mcp/` with both local environment variables configured:

```sh
TOKEN_IO_RUN_REAL_DECISIONS=1 uv run --managed-python --locked -- python tests/real_api_tests/decisions_real_smoke.py
```

Without the opt-in, the script makes no request. It uses a temporary Root database and a synthetic trusted provider, calls `DecisionsAdvisor` directly, and reports only safe status, reason, classification metadata, choice, and usage. It does not prove a real host binding or a real API call through the MCP handler. MCP handler/protocol tests instead use mocked API transport. The advisor reads both required local variables at invocation time; neither the script nor the project supplies replacement credentials or a default endpoint.

## Build, rule resources, and installed checks

Build all eight wheels and source distributions from `mcp/`:

```sh
uv build --all-packages --managed-python --python 3.14 --out-dir /tmp/token-io-dist
```

The core package owns rule resources and its custom build hook. The canonical registry remains `mcp/rule-registry.json`; build output contains bounded excerpts from its English/Chinese owner headings. Core sdists carry their own `rule_sources`, so a detached build does not borrow a neighboring checkout. The default `token_io_decoupling_core.rules.RuleLoader` reads packaged snapshots; source development must explicitly supply the repository root. Editing Markdown does not update an installed wheel: rebuild and reinstall it.

The build also packages General rules in both languages for `child-role-selection`, `task-assignment`, `output-token-routing`, `session-role-ownership`, and `decision-context-generation`. These are fixed allowlisted policy resources, not additional Core checkpoint IDs. `tests/unit_tests/test_build_artifacts.py` verifies a detached sdist-to-wheel build and loads these policies through the packaged `RuleLoader`, including their content hashes.

Released migration files belong to the state package and remain byte-for-byte unchanged because database history records source checksums. The state loader temporarily supplies the historical `token_io_mcp.models.DatabaseKind` import required by the two v1 files; it removes the alias after importing them. Directly importing frozen state migration modules bypasses this scoped loader and is unsupported; use the renamed adapter migration path for direct imports. Namespace relocation does not authorize rewriting history, checksum verification, or schema versions. Tests cover legacy history and upgrades as well as fresh databases.

The [MCP CI workflow](../.github/workflows/mcp.yml) runs locked checks on managed Python 3.11 and 3.14 and a separate installed-wheel job. Export third-party build/runtime constraints with `uv export --no-emit-workspace` (plus `--all-groups` for builds or `--no-dev` for runtime). Workspace members are supplied by the local artifacts, not editable requirements. To install from the detached wheel set, use its directory as `--find-links` and install the root `token_io_decoupling-0.1.0-py3-none-any.whl`; retain the configured index for locked third-party dependencies. See CI for the complete commands.

For temporary installation, set command-local `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` to absolute temporary directories. Run `tests/support/installed_stdio_smoke.py --cli /absolute/temporary/bin/token-io-decoupling` with the locked workspace interpreter. It starts four profile subprocesses outside the checkout with an empty `PYTHONPATH`, verifies exact inventories and binding rejection, checks both rule languages, and runs setup dry-run with an empty `PATH`. Source-root tool installation is checked separately. These results prove packaging and stdio behavior, not actual host binding or a GitHub Actions run.

The [documentation workflow](../.github/workflows/multilingual-docs.yml) retains multilingual/link/route validators and scanner regressions; it prunes generated resources and environments while checking authored workspace documentation.

## Native recovery development checks

The [Native Authority Transfer](../references/coding/layer-01-fundamental-concepts/enhanced-native-state/native-authority-transfer.md) and [Native Reconciliation](../references/coding/layer-01-fundamental-concepts/enhanced-native-state/native-reconciliation.md) owners define the workflow boundaries. The checks below verify the implemented service cases; they do not establish a full export or host-stop capability.

Use temporary databases and synthetic bindings for recovery development. The focused state-service cases exercise explicit full-set adjudication, preserved comparison history, recovery Revision/Epoch freshness, outstanding evidence requests, and blocked dispatch side effects. They also cover exact confirmation without hiding older conflicts, fresh Control before the first post-recovery Slice, effect-free confirmed dispatch replay, and bounded readback of oversized legacy snapshots. Migration tests distinguish proven legacy confirmation pairs from malformed or nonadjacent records. Run them from `mcp/` before the complete suite:

```sh
uv run --managed-python --locked -- pytest tests/mock_api_tests/test_state_service.py -k native
uv run --managed-python --locked -- pytest tests/unit_tests/test_migrations.py
```

These checks do not prove a host can stop a Worker. The supported material-recovery path has existing Root control state and no bound Worker, active Worker Slice, or pending dispatch. It adjudicates the Contract source and semantic-reference pair; it does not reconstruct missing identity, dispatch, lifecycle, or acceptance history. Keep unsupported states blocked and preserve their records. Evidence references and request hashes provide review pointers and integrity binding; neither authenticates a caller or independently establishes freshness or quiescence.
